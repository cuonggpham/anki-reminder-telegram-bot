from __future__ import annotations

import httpx

from anki_reminder_bot.adapters.persistence.control_api_repository import ControlApiRepository
from anki_reminder_bot.domain.models import ReminderConfig, RuntimeState


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_control_api_repository_maps_runtime_payload(monkeypatch):
    def request(method, url, **kwargs):
        assert method == "GET"
        assert url == "https://control.example/internal/runtime"
        assert kwargs["headers"]["Authorization"] == "Bearer secret"
        return FakeResponse(
            {
                "config": {
                    "enabled": True,
                    "selectedDecks": ["English"],
                    "reminderTimes": ["08:15"],
                    "timezone": "Asia/Ho_Chi_Minh",
                    "language": "vi-en",
                },
                "state": {
                    "sentSlots": {"2026-09-08:08:15": "done"},
                    "completionSentDates": [],
                    "lastSyncAt": "2026-09-08T08:15:00+07:00",
                },
            }
        )

    monkeypatch.setattr(httpx, "request", request)
    repository = ControlApiRepository("https://control.example/", "secret")

    assert repository.load_config() == ReminderConfig(
        selected_decks=["English"],
        reminder_times=["08:15"],
        timezone="Asia/Ho_Chi_Minh",
        language="vi-en",
    )
    assert repository.load_state() == RuntimeState(
        sent_slots={"2026-09-08:08:15": "done"},
        last_sync_at="2026-09-08T08:15:00+07:00",
    )
