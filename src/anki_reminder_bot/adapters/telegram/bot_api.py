from __future__ import annotations

import time
from typing import Any

import httpx


class TelegramApiError(RuntimeError):
    pass


class TelegramBotApi:
    def __init__(self, token: str, chat_id: int, miniapp_url: str):
        self.chat_id = chat_id
        self.miniapp_url = miniapp_url
        self.base_url = f"https://api.telegram.org/bot{token}"

    def call(self, method: str, payload: dict[str, Any], retries: int = 3) -> dict:
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                response = httpx.post(
                    f"{self.base_url}/{method}", json=payload, timeout=35
                )
                response.raise_for_status()
                data = response.json()
                if not data.get("ok"):
                    raise TelegramApiError(data.get("description", "Telegram API error"))
                return data["result"]
            except (httpx.HTTPError, ValueError, TelegramApiError) as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(2**attempt)
        raise TelegramApiError(f"Telegram {method} failed: {last_error}") from last_error

    def send_message(self, text: str, reply_markup: dict | None = None) -> dict:
        payload: dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.call("sendMessage", payload)

    def study_keyboard(self) -> dict:
        return {
            "inline_keyboard": [
                [{"text": "📖 Học ngay / Study now", "web_app": {"url": self.miniapp_url}}]
            ]
        }
