from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from anki_reminder_bot.domain.models import ReminderConfig, RuntimeState


class JsonRuntimeRepository:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        return self.root / name

    def _read(self, name: str, default: dict) -> dict:
        path = self._path(name)
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, name: str, payload: dict) -> None:
        path = self._path(name)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def load_config(self) -> ReminderConfig:
        return ReminderConfig.from_dict(self._read("config.json", {}))

    def save_config(self, config: ReminderConfig) -> None:
        config.validate()
        self._write("config.json", config.to_dict())

    def load_state(self) -> RuntimeState:
        return RuntimeState.from_dict(self._read("state.json", {}))

    def save_state(self, state: RuntimeState) -> None:
        self._write("state.json", state.to_dict())

    def load_decks(self) -> list[str]:
        payload = self._read("decks.json", {"decks": []})
        return list(payload.get("decks") or [])

    def save_decks(self, decks: list[str], updated_at: datetime) -> None:
        self._write(
            "decks.json",
            {"decks": sorted(set(decks)), "updated_at": updated_at.isoformat()},
        )
