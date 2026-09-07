from __future__ import annotations

from anki_reminder_bot.domain.models import ALL_DECKS, ReminderConfig


def settings_keyboard(config: ReminderConfig) -> dict:
    decks = ", ".join(config.selected_decks) if config.selected_decks != [ALL_DECKS] else "All decks"
    times = ", ".join(config.reminder_times) or "None"
    return {
        "inline_keyboard": [
            [{"text": f"📚 Decks: {decks[:32]}", "callback_data": "menu:decks"}],
            [{"text": f"⏰ Times: {times[:32]}", "callback_data": "menu:times"}],
            [{"text": "🔔 Enable / Bật" if not config.enabled else "🔕 Disable / Tắt", "callback_data": "cfg:toggle"}],
            [{"text": "⬅️ Menu", "callback_data": "menu:main"}],
        ]
    }


def deck_keyboard(decks: list[str], config: ReminderConfig) -> dict:
    rows = []
    all_selected = config.selected_decks == [ALL_DECKS]
    rows.append([{"text": f"{'✅ ' if all_selected else ''}All decks", "callback_data": "deck:all"}])
    for index, deck in enumerate(decks[:80]):
        selected = deck in config.selected_decks
        rows.append([{"text": f"{'✅ ' if selected else '⬜ '}{deck[:50]}", "callback_data": f"deck:toggle:{index}"}])
    rows.append([{"text": "✅ Save / Lưu", "callback_data": "menu:settings"}])
    return {"inline_keyboard": rows}


def time_keyboard(config: ReminderConfig) -> dict:
    quick_times = ["07:00", "08:00", "12:00", "13:00", "18:00", "20:00", "22:00"]
    rows = []
    for start in range(0, len(quick_times), 3):
        rows.append(
            [
                {
                    "text": f"{'✅ ' if value in config.reminder_times else ''}{value}",
                    "callback_data": f"time:toggle:{value}",
                }
                for value in quick_times[start : start + 3]
            ]
        )
    rows.extend(
        [
            [{"text": "✍️ Custom time / Giờ tùy ý", "callback_data": "time:custom"}],
            [
                {"text": "🔄 Refresh / Làm mới", "callback_data": "decks:refresh"},
                {"text": "✅ Save / Lưu", "callback_data": "menu:settings"},
            ],
        ]
    )
    return {"inline_keyboard": rows}
