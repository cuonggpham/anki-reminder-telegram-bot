from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from anki_reminder_bot.application.presentation import (
    format_completed,
    format_reminder,
)
from anki_reminder_bot.domain.models import parse_clock_time


class ReminderService:
    def __init__(self, anki, telegram, repository):
        self.anki = anki
        self.telegram = telegram
        self.repository = repository

    def run(self, now: datetime) -> bool:
        config = self.repository.load_config()
        state = self.repository.load_state()
        if not config.enabled:
            return False
        local_now = now.astimezone(ZoneInfo(config.timezone))
        matching = [value for value in config.reminder_times if self._is_due(value, local_now)]
        if not matching:
            return False
        stats, _ = self.anki.sync_and_get_stats(config.selected_decks, local_now)
        state.last_sync_at = local_now.isoformat()
        sent = False
        for slot in matching:
            slot_key = f"{local_now.date().isoformat()}:{slot}"
            if slot_key in state.sent_slots:
                continue
            if stats.due_count == 0:
                date_key = local_now.date().isoformat()
                if date_key not in state.completion_sent_dates:
                    self.telegram.send_message(format_completed(config), self.telegram.study_keyboard())
                    state.completion_sent_dates.append(date_key)
            else:
                self.telegram.send_message(
                    format_reminder(stats, config, local_now.strftime("%Y-%m-%d %H:%M")),
                    self.telegram.study_keyboard(),
                )
            state.sent_slots[slot_key] = local_now.isoformat()
            sent = True
        self.repository.save_state(state)
        return sent

    @staticmethod
    def _is_due(value: str, now: datetime) -> bool:
        hour, minute = parse_clock_time(value)
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        delta = (now - target).total_seconds()
        return 0 <= delta < 5 * 60
