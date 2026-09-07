from __future__ import annotations

from datetime import datetime, time as datetime_time
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from anki_reminder_bot.domain.models import ALL_DECKS, AnkiStats


class AnkiSyncError(RuntimeError):
    pass


class OfficialAnkiAdapter:
    """Adapter around Anki's Python library.

    The import and sync call are intentionally isolated here because Anki's
    Python internals are not a stable public API. The rest of the application
    only depends on this adapter's small contract.
    """

    def __init__(self, email: str, password: str, timezone: str):
        self.email = email
        self.password = password
        self.timezone = ZoneInfo(timezone)

    def sync_and_get_stats(
        self, selected_decks: list[str], now: datetime
    ) -> tuple[AnkiStats, list[str]]:
        try:
            from anki.collection import Collection
        except ImportError as exc:
            raise AnkiSyncError("The official Anki Python package is unavailable") from exc

        with TemporaryDirectory(prefix="anki-reminder-") as directory:
            collection_path = Path(directory) / "collection.anki2"
            collection = None
            try:
                collection = Collection(str(collection_path))
                self._sync_collection(collection)
                all_decks = self._deck_names(collection)
                stats = self._read_stats(collection, selected_decks, all_decks, now)
                return stats, all_decks
            except Exception as exc:
                raise AnkiSyncError(f"Anki sync/query failed: {type(exc).__name__}") from exc
            finally:
                if collection is not None:
                    close = getattr(collection, "close", None)
                    if close:
                        close()

    def _sync_collection(self, collection) -> None:
        """Download/sync without ever choosing the upload direction.

        Anki 26 exposes sync through Collection. A fresh temporary collection
        can require a full download; that path is handled explicitly. A full
        upload is treated as a hard safety error.
        """
        auth = collection.sync_login(self.email, self.password, None)
        status = collection.sync_status(auth)
        if getattr(status, "new_endpoint", ""):
            auth.endpoint = status.new_endpoint

        response = collection.sync_collection(auth, sync_media=False)
        if getattr(response, "new_endpoint", ""):
            auth.endpoint = response.new_endpoint

        required = int(response.required)
        full_download = int(getattr(response, "FULL_DOWNLOAD", 3))
        full_sync = int(getattr(response, "FULL_SYNC", 2))
        full_upload = int(getattr(response, "FULL_UPLOAD", 4))
        if required == full_upload:
            raise AnkiSyncError("Anki requested a full upload; refusing for safety")
        if required in {full_download, full_sync}:
            collection.close_for_full_sync()
            collection.full_upload_or_download(
                auth=auth,
                server_usn=None,
                upload=False,
            )
            collection.reopen(after_full_sync=True)

    @staticmethod
    def _deck_names(collection) -> list[str]:
        names_and_ids = collection.decks.all_names_and_ids()
        if isinstance(names_and_ids, dict):
            return sorted(str(name) for name in names_and_ids)
        return sorted(
            str(item.name if hasattr(item, "name") else item[0])
            for item in names_and_ids
        )

    def _read_stats(
        self, collection, selected_decks: list[str], all_decks: list[str], now: datetime
    ) -> AnkiStats:
        missing = [name for name in selected_decks if name != ALL_DECKS and name not in all_decks]
        if missing:
            raise AnkiSyncError(f"Configured deck not found: {', '.join(missing)}")
        expanded = self._expand_selected_decks(selected_decks, all_decks)
        card_ids: set[int] = set()
        due_ids: set[int] = set()
        new_ids: set[int] = set()
        for deck_name in expanded:
            query_prefix = f'deck:"{deck_name.replace(chr(34), chr(92) + chr(34))}"'
            card_ids.update(collection.find_cards(query_prefix))
            due_ids.update(collection.find_cards(f"{query_prefix} is:due"))
            new_ids.update(collection.find_cards(f"{query_prefix} is:new"))

        reviewed_today = self._reviewed_today(collection, card_ids, now)
        return AnkiStats(
            due_count=len(due_ids),
            new_count=len(new_ids),
            reviewed_today=reviewed_today,
            remaining_today=len(due_ids),
            deck_names=tuple(expanded),
            synced_at=now,
        )

    @staticmethod
    def _expand_selected_decks(selected: list[str], all_decks: list[str]) -> list[str]:
        if ALL_DECKS in selected:
            return all_decks
        expanded: set[str] = set()
        for selected_name in selected:
            expanded.update(
                name
                for name in all_decks
                if name == selected_name or name.startswith(f"{selected_name}::")
            )
        return sorted(expanded)

    def _reviewed_today(self, collection, card_ids: set[int], now: datetime) -> int:
        if not card_ids:
            return 0
        local_today = now.astimezone(self.timezone).date()
        start = datetime.combine(local_today, datetime_time.min, tzinfo=self.timezone)
        start_ms = int(start.timestamp() * 1000)
        placeholders = ",".join("?" for _ in card_ids)
        params = [start_ms, *card_ids]
        query = (
            f"select count() from revlog where id >= ? and cid in ({placeholders})"
        )
        return int(collection.db.scalar(query, *params) or 0)
