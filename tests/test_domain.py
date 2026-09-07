from datetime import datetime

import pytest

from anki_reminder_bot.application.services import ReminderService
from anki_reminder_bot.domain.models import ReminderConfig, RuntimeState


def test_config_rejects_more_than_five_reminder_times():
    with pytest.raises(ValueError):
        ReminderConfig(reminder_times=["00:00", "01:00", "02:00", "03:00", "04:00", "05:00"]).validate()


def test_config_toggling_all_decks_clears_named_decks():
    config = ReminderConfig(selected_decks=["English", "Japanese"])
    config.toggle_deck("*")
    assert config.selected_decks == ["*"]


def test_config_toggling_named_deck_replaces_all_selection():
    config = ReminderConfig()
    config.toggle_deck("English")
    assert config.selected_decks == ["English"]


def test_due_window_is_five_minutes():
    now = datetime.fromisoformat("2026-09-08T08:04:00+07:00")
    assert ReminderService._is_due("08:00", now)
    assert not ReminderService._is_due("08:00", now.replace(minute=5))


def test_runtime_state_round_trip():
    state = RuntimeState(telegram_update_offset=4, awaiting_input="times")
    restored = RuntimeState.from_dict(state.to_dict())
    assert restored.telegram_update_offset == 4
    assert restored.awaiting_input == "times"
