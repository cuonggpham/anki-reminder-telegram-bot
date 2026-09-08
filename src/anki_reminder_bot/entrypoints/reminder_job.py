from __future__ import annotations

from anki_reminder_bot.application.services import ReminderService
from anki_reminder_bot.entrypoints.common import app_now, build_components


def main() -> None:
    _, repository, anki, telegram = build_components()
    try:
        config = repository.load_config()
        service = ReminderService(anki, telegram, repository)
        sent = service.run(app_now(config.timezone))
        print(f"reminder_job completed; notification_sent={sent}")
    except Exception as exc:
        # Do not hide the original failure: the workflow must be non-zero.
        # The alert itself is best-effort and contains no exception details
        # that could accidentally expose credentials.
        try:
            telegram.send_message(
                "❌ Anki sync failed / Đồng bộ Anki thất bại.\n"
                "Please check GitHub Actions logs / Vui lòng kiểm tra log GitHub Actions."
            )
        finally:
            raise RuntimeError(f"reminder job failed: {type(exc).__name__}") from exc


if __name__ == "__main__":
    main()
