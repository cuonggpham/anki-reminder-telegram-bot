from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


ALL_DECKS = "*"
SUPPORTED_LANGUAGES = {"vi-en", "en-vi"}


@dataclass(frozen=True)
class AnkiStats:
    due_count: int
    new_count: int
    reviewed_today: int
    remaining_today: int
    deck_names: tuple[str, ...] = ()
    synced_at: datetime | None = None


@dataclass
class ReminderConfig:
    enabled: bool = True
    selected_decks: list[str] = field(default_factory=lambda: [ALL_DECKS])
    reminder_times: list[str] = field(default_factory=lambda: ["08:00", "18:00"])
    timezone: str = "Asia/Ho_Chi_Minh"
    language: str = "vi-en"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ReminderConfig":
        defaults = cls()
        config = cls(
            enabled=bool(raw.get("enabled", defaults.enabled)),
            selected_decks=list(raw.get("selected_decks") or defaults.selected_decks),
            reminder_times=list(raw.get("reminder_times") or defaults.reminder_times),
            timezone=str(raw.get("timezone", defaults.timezone)),
            language=str(raw.get("language", defaults.language)),
        )
        config.validate()
        return config

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "selected_decks": self.selected_decks,
            "reminder_times": self.reminder_times,
            "timezone": self.timezone,
            "language": self.language,
        }

    def validate(self) -> None:
        if not self.selected_decks:
            raise ValueError("At least one deck selection is required")
        if ALL_DECKS in self.selected_decks and len(self.selected_decks) > 1:
            raise ValueError("All decks cannot be combined with named decks")
        if len(self.reminder_times) > 5:
            raise ValueError("At most five reminder times are supported")
        for value in self.reminder_times:
            parse_clock_time(value)
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {self.language}")

    def toggle_deck(self, deck: str) -> None:
        if deck == ALL_DECKS:
            self.selected_decks = [ALL_DECKS]
            return
        if ALL_DECKS in self.selected_decks:
            self.selected_decks = []
        if deck in self.selected_decks:
            self.selected_decks.remove(deck)
        else:
            self.selected_decks.append(deck)
        if not self.selected_decks:
            self.selected_decks = [ALL_DECKS]
        self.validate()

    def toggle_time(self, value: str) -> None:
        parse_clock_time(value)
        if value in self.reminder_times:
            self.reminder_times.remove(value)
        elif len(self.reminder_times) < 5:
            self.reminder_times.append(value)
            self.reminder_times.sort()
        else:
            raise ValueError("You can select at most five reminder times")
        self.validate()


@dataclass
class RuntimeState:
    telegram_update_offset: int = 0
    sent_slots: dict[str, str] = field(default_factory=dict)
    completion_sent_dates: list[str] = field(default_factory=list)
    awaiting_input: str | None = None
    last_sync_at: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RuntimeState":
        return cls(
            telegram_update_offset=int(raw.get("telegram_update_offset", 0)),
            sent_slots=dict(raw.get("sent_slots") or {}),
            completion_sent_dates=list(raw.get("completion_sent_dates") or []),
            awaiting_input=raw.get("awaiting_input"),
            last_sync_at=raw.get("last_sync_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "telegram_update_offset": self.telegram_update_offset,
            "sent_slots": self.sent_slots,
            "completion_sent_dates": self.completion_sent_dates,
            "awaiting_input": self.awaiting_input,
            "last_sync_at": self.last_sync_at,
        }


def parse_clock_time(value: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = value.split(":", 1)
        hour, minute = int(hour_text), int(minute_text)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid time: {value!r}; expected HH:MM") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time: {value!r}; expected HH:MM")
    return hour, minute
