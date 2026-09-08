from datetime import datetime

import pytest

from anki_reminder_bot.application.services import ReminderService
from anki_reminder_bot.domain.models import ReminderConfig, RuntimeState


def test_config_rejects_more_than_five_reminder_times():
    with pytest.raises(ValueError):
        ReminderConfig(reminder_times=["00:00", "01:00", "02:00", "03:00", "04:00", "05:00"]).validate()


def test_due_window_is_five_minutes():
    now = datetime.fromisoformat("2026-09-08T08:04:00+07:00")
    assert ReminderService._is_due("08:00", now)
    assert not ReminderService._is_due("08:00", now.replace(minute=5))


def test_runtime_state_round_trip():
    state = RuntimeState(last_sync_at="2026-09-08T08:00:00+07:00")
    restored = RuntimeState.from_dict(state.to_dict())
    assert restored.last_sync_at == "2026-09-08T08:00:00+07:00"
