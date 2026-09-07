from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from anki_reminder_bot.application.keyboards import deck_keyboard, settings_keyboard, time_keyboard
from anki_reminder_bot.application.presentation import (
    format_completed,
    format_reminder,
    format_stats,
)
from anki_reminder_bot.domain.models import ReminderConfig, RuntimeState, parse_clock_time


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
        stats, decks = self.anki.sync_and_get_stats(config.selected_decks, local_now)
        self.repository.save_decks(decks, local_now)
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


class TelegramInteractionService:
    def __init__(self, telegram, repository, status_loader):
        self.telegram = telegram
        self.repository = repository
        self.status_loader = status_loader

    def process_updates(self) -> int:
        state = self.repository.load_state()
        config = self.repository.load_config()
        decks = self.repository.load_decks()
        updates = self.telegram.get_updates(state.telegram_update_offset)
        processed = 0
        for update in updates:
            state.telegram_update_offset = max(state.telegram_update_offset, int(update["update_id"]) + 1)
            try:
                self._process_update(update, config, state, decks)
            except Exception as exc:
                self.telegram.send_message(f"❌ Bot error / Lỗi bot: {type(exc).__name__}")
            processed += 1
        self.repository.save_config(config)
        self.repository.save_state(state)
        return processed

    def _process_update(self, update, config: ReminderConfig, state: RuntimeState, decks: list[str]) -> None:
        if "callback_query" in update:
            self._callback(update["callback_query"], config, state, decks)
            return
        message = update.get("message") or {}
        if message.get("chat", {}).get("id") != self.telegram.chat_id:
            return
        text = (message.get("text") or "").strip()
        if not text:
            return
        if text.startswith("/times") or state.awaiting_input == "times":
            self._set_times(text.removeprefix("/times").strip(), config, state)
        elif text in {"/start", "/settings"}:
            self.telegram.send_message(self._settings_text(config), settings_keyboard(config))
        elif text == "/study":
            self.telegram.send_message("📖 Study now / Học ngay", self.telegram.study_keyboard())
        elif text == "/status":
            stats, _ = self.status_loader(config)
            self.telegram.send_message(format_stats(stats, config), self.telegram.study_keyboard())

    def _callback(self, callback, config: ReminderConfig, state: RuntimeState, decks: list[str]) -> None:
        if callback.get("message", {}).get("chat", {}).get("id") != self.telegram.chat_id:
            return
        data = callback.get("data", "")
        self.telegram.answer_callback(callback["id"])
        if data == "menu:main":
            self.telegram.edit_message(callback["message"]["message_id"], "📚 Anki Reminder", self.telegram.main_keyboard())
        elif data in {"menu:settings", "cfg:toggle"}:
            if data == "cfg:toggle":
                config.enabled = not config.enabled
            self.telegram.edit_message(callback["message"]["message_id"], self._settings_text(config), settings_keyboard(config))
        elif data == "menu:decks":
            self.telegram.edit_message(callback["message"]["message_id"], "📚 Select decks / Chọn deck", deck_keyboard(decks, config))
        elif data == "decks:refresh":
            refreshed_stats, refreshed_decks = self.status_loader(config)
            self.repository.save_decks(
                refreshed_decks, refreshed_stats.synced_at or datetime.now()
            )
            self.telegram.edit_message(
                callback["message"]["message_id"],
                "📚 Select decks / Chọn deck",
                deck_keyboard(refreshed_decks, config),
            )
        elif data == "deck:all":
            config.toggle_deck("*")
            self.telegram.edit_message(callback["message"]["message_id"], "📚 Select decks / Chọn deck", deck_keyboard(decks, config))
        elif data.startswith("deck:toggle:"):
            index = int(data.rsplit(":", 1)[1])
            if index < len(decks):
                config.toggle_deck(decks[index])
            self.telegram.edit_message(callback["message"]["message_id"], "📚 Select decks / Chọn deck", deck_keyboard(decks, config))
        elif data == "menu:times":
            self.telegram.edit_message(callback["message"]["message_id"], "⏰ Select times / Chọn giờ", time_keyboard(config))
        elif data.startswith("time:toggle:"):
            config.toggle_time(data.rsplit(":", 1)[1])
            self.telegram.edit_message(callback["message"]["message_id"], "⏰ Select times / Chọn giờ", time_keyboard(config))
        elif data == "time:custom":
            state.awaiting_input = "times"
            self.telegram.send_message("✍️ Send up to 5 times as HH:MM, separated by commas.\nVí dụ: 08:15, 13:30, 21:45")
        elif data == "menu:status":
            stats, _ = self.status_loader(config)
            self.telegram.edit_message(callback["message"]["message_id"], format_stats(stats, config), self.telegram.study_keyboard())

    @staticmethod
    def _settings_text(config: ReminderConfig) -> str:
        decks = ", ".join(config.selected_decks)
        times = ", ".join(config.reminder_times) or "None"
        status = "Enabled / Đang bật" if config.enabled else "Disabled / Đang tắt"
        return f"⚙️ Settings / Cấu hình\n\nDecks: {decks}\nTimes: {times}\nStatus: {status}\nTimezone: {config.timezone}"

    @staticmethod
    def _set_times(value: str, config: ReminderConfig, state: RuntimeState) -> None:
        values = [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]
        if not values or len(values) > 5:
            raise ValueError("Please provide 1-5 times")
        for item in values:
            parse_clock_time(item)
        config.reminder_times = sorted(set(values))
        config.validate()
        state.awaiting_input = None
