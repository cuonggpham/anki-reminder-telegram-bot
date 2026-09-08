from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    ankiweb_email: str
    ankiweb_password: str
    telegram_bot_token: str
    telegram_chat_id: int
    miniapp_url: str
    runtime_dir: Path
    runtime_backend: str
    control_api_url: str | None
    control_api_token: str | None

    @classmethod
    def from_env(cls) -> "AppSettings":
        required = {
            "ANKIWEB_EMAIL": os.getenv("ANKIWEB_EMAIL"),
            "ANKIWEB_PASSWORD": os.getenv("ANKIWEB_PASSWORD"),
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
            "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID"),
            "MINIAPP_URL": os.getenv("MINIAPP_URL"),
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        try:
            chat_id = int(required["TELEGRAM_CHAT_ID"] or "")
        except ValueError as exc:
            raise ValueError("TELEGRAM_CHAT_ID must be an integer") from exc
        return cls(
            ankiweb_email=required["ANKIWEB_EMAIL"] or "",
            ankiweb_password=required["ANKIWEB_PASSWORD"] or "",
            telegram_bot_token=required["TELEGRAM_BOT_TOKEN"] or "",
            telegram_chat_id=chat_id,
            miniapp_url=required["MINIAPP_URL"] or "",
            runtime_dir=Path(os.getenv("RUNTIME_DIR", "runtime")),
            runtime_backend=os.getenv("RUNTIME_BACKEND", "json"),
            control_api_url=os.getenv("CONTROL_API_URL"),
            control_api_token=os.getenv("CONTROL_API_TOKEN"),
        )
