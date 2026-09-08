from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from anki_reminder_bot.domain.models import ReminderConfig, RuntimeState


class ControlApiError(RuntimeError):
    pass


class ControlApiRepository:
    """Runtime repository backed by the Telegram control service."""

    def __init__(self, base_url: str, token: str, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.token}"},
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ControlApiError(f"Control API {method} {path} failed") from exc
        if not isinstance(data, dict):
            raise ControlApiError(f"Control API {method} {path} returned invalid JSON")
        return data

    def _runtime(self) -> dict[str, Any]:
        return self._request("GET", "/internal/runtime")

    def load_config(self) -> ReminderConfig:
        raw = self._runtime().get("config")
        if not isinstance(raw, dict):
            raise ControlApiError("Control API response has no config")
        return ReminderConfig.from_dict(
            {
                "enabled": raw.get("enabled"),
                "selected_decks": raw.get("selectedDecks"),
                "reminder_times": raw.get("reminderTimes"),
                "timezone": raw.get("timezone"),
                "language": raw.get("language"),
            }
        )

    def save_config(self, config: ReminderConfig) -> None:
        self._request("PUT", "/internal/runtime/config", config.to_dict())

    def load_state(self) -> RuntimeState:
        raw = self._runtime().get("state")
        if not isinstance(raw, dict):
            raise ControlApiError("Control API response has no state")
        return RuntimeState.from_dict(
            {
                "sent_slots": raw.get("sentSlots"),
                "completion_sent_dates": raw.get("completionSentDates"),
                "last_sync_at": raw.get("lastSyncAt"),
            }
        )

    def save_state(self, state: RuntimeState) -> None:
        self._request(
            "PUT",
            "/internal/runtime/state",
            {
                "sentSlots": state.sent_slots,
                "completionSentDates": state.completion_sent_dates,
                "lastSyncAt": state.last_sync_at,
            },
        )

    def save_decks(self, decks: list[str]) -> None:
        self._request("POST", "/internal/decks", {"decks": sorted(set(decks))})

