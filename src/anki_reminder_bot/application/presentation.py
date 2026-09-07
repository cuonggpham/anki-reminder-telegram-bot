from __future__ import annotations

from anki_reminder_bot.domain.models import AnkiStats, ReminderConfig


def format_stats(stats: AnkiStats, config: ReminderConfig, last_sync: str | None = None) -> str:
    decks = ", ".join(stats.deck_names) if stats.deck_names else "All decks"
    if config.language == "en-vi":
        return (
            "📚 Anki Status / Trạng thái Anki\n\n"
            f"Deck(s): {decks}\n"
            f"🔴 Due / Cần ôn: {stats.due_count}\n"
            f"🆕 New / Mới: {stats.new_count}\n"
            f"✅ Reviewed today / Đã ôn hôm nay: {stats.reviewed_today}\n"
            f"⏳ Remaining / Còn lại: {stats.remaining_today}\n"
            f"🕒 Last sync / Đồng bộ: {last_sync or 'now'}"
        )
    return (
        "📚 Trạng thái Anki / Anki Status\n\n"
        f"Deck: {decks}\n"
        f"🔴 Cần ôn / Due: {stats.due_count}\n"
        f"🆕 Mới / New: {stats.new_count}\n"
        f"✅ Đã ôn hôm nay / Reviewed today: {stats.reviewed_today}\n"
        f"⏳ Còn lại / Remaining: {stats.remaining_today}\n"
        f"🕒 Đồng bộ / Last sync: {last_sync or 'now'}"
    )


def format_reminder(stats: AnkiStats, config: ReminderConfig, last_sync: str) -> str:
    if config.language == "en-vi":
        return (
            "📚 Anki Reminder / Nhắc học Anki\n\n"
            f"🔴 Due / Cần ôn: {stats.due_count}\n"
            f"🆕 New / Mới: {stats.new_count}\n"
            f"✅ Reviewed today / Đã ôn hôm nay: {stats.reviewed_today}\n"
            f"🕒 {last_sync}"
        )
    return (
        "📚 Nhắc học Anki / Anki Reminder\n\n"
        f"🔴 Cần ôn / Due: {stats.due_count}\n"
        f"🆕 Mới / New: {stats.new_count}\n"
        f"✅ Đã ôn hôm nay / Reviewed today: {stats.reviewed_today}\n"
        f"🕒 {last_sync}"
    )


def format_completed(config: ReminderConfig) -> str:
    if config.language == "en-vi":
        return "✅ Completed today / Đã hoàn thành hôm nay!"
    return "✅ Đã hoàn thành hôm nay / Completed today!"
