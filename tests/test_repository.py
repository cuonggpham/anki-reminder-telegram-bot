from pathlib import Path

from anki_reminder_bot.adapters.persistence.json_repository import JsonRuntimeRepository
from anki_reminder_bot.domain.models import ReminderConfig


def test_repository_persists_config(tmp_path: Path):
    repository = JsonRuntimeRepository(tmp_path)
    config = ReminderConfig(selected_decks=["English"], reminder_times=["09:15"])
    repository.save_config(config)
    loaded = repository.load_config()
    assert loaded.selected_decks == ["English"]
    assert loaded.reminder_times == ["09:15"]
