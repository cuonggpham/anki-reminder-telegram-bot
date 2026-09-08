from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from anki_reminder_bot.adapters.anki.official import OfficialAnkiAdapter
from anki_reminder_bot.adapters.persistence.control_api_repository import ControlApiRepository
from anki_reminder_bot.adapters.persistence.json_repository import JsonRuntimeRepository
from anki_reminder_bot.adapters.telegram.bot_api import TelegramBotApi
from anki_reminder_bot.config import AppSettings


def build_components():
    settings = AppSettings.from_env()
    if settings.runtime_backend == "control_api":
        if not settings.control_api_url or not settings.control_api_token:
            raise ValueError("CONTROL_API_URL and CONTROL_API_TOKEN are required for control_api backend")
        repository = ControlApiRepository(settings.control_api_url, settings.control_api_token)
    else:
        repository = JsonRuntimeRepository(settings.runtime_dir)
    config = repository.load_config()
    anki = OfficialAnkiAdapter(settings.ankiweb_email, settings.ankiweb_password, config.timezone)
    telegram = TelegramBotApi(settings.telegram_bot_token, settings.telegram_chat_id, settings.miniapp_url)
    return settings, repository, anki, telegram


def app_now(timezone: str) -> datetime:
    return datetime.now(ZoneInfo(timezone))
