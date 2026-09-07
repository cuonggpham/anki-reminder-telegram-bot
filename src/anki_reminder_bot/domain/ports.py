from __future__ import annotations

from datetime import datetime
from typing import Protocol

from anki_reminder_bot.domain.models import AnkiStats, ReminderConfig


class AnkiPort(Protocol):
    def sync_and_get_stats(
        self, selected_decks: list[str], now: datetime
    ) -> tuple[AnkiStats, list[str]]: ...


class ConfigRepository(Protocol):
    def load_config(self) -> ReminderConfig: ...

    def save_config(self, config: ReminderConfig) -> None: ...

    def load_state(self): ...

    def save_state(self, state) -> None: ...

    def load_decks(self) -> list[str]: ...

    def save_decks(self, decks: list[str], updated_at: datetime) -> None: ...


class TelegramPort(Protocol):
    def send_message(self, text: str, reply_markup: dict | None = None) -> dict: ...
