import httpx

from config import Settings


class TelegramClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._api_base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    def send_message(self, text: str) -> None:
        response = httpx.post(
            f"{self._api_base}/sendMessage",
            json={
                "chat_id": self._settings.telegram_chat_id,
                "text": text,
            },
            timeout=30.0,
        )

        payload = response.json()
        if not response.is_success or not payload.get("ok"):
            description = payload.get("description", response.text)
            raise RuntimeError(
                f"Telegram send failed ({response.status_code}): {description}"
            )
