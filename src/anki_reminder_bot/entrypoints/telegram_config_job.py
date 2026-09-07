from __future__ import annotations

from anki_reminder_bot.application.services import TelegramInteractionService
from anki_reminder_bot.entrypoints.common import build_components


def main() -> None:
    _, repository, anki, telegram = build_components()

    def status_loader(config):
        from anki_reminder_bot.entrypoints.common import app_now

        return anki.sync_and_get_stats(config.selected_decks, app_now(config.timezone))

    telegram.set_commands()
    service = TelegramInteractionService(telegram, repository, status_loader)
    processed = service.process_updates()
    print(f"telegram_config_job completed; updates_processed={processed}")


if __name__ == "__main__":
    main()
