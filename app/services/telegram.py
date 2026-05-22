import httpx


def verify_telegram_bot_token(bot_token: str) -> str:
    response = httpx.get(
        f"https://api.telegram.org/bot{bot_token}/getMe",
        timeout=20.0,
    )
    payload = response.json()
    if not response.is_success or not payload.get("ok"):
        description = payload.get("description", response.text)
        raise RuntimeError(description)

    username = payload["result"].get("username")
    if not username:
        raise RuntimeError("Bot token is valid but has no username")
    return username


def verify_telegram_chat(chat_id: str, bot_token: str) -> None:
    response = httpx.get(
        f"https://api.telegram.org/bot{bot_token}/getChat",
        params={"chat_id": chat_id},
        timeout=20.0,
    )
    payload = response.json()
    if not response.is_success or not payload.get("ok"):
        description = payload.get("description", response.text)
        raise RuntimeError(description)


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    response = httpx.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=30.0,
    )
    payload = response.json()
    if not response.is_success or not payload.get("ok"):
        description = payload.get("description", response.text)
        raise RuntimeError(f"Telegram send failed ({response.status_code}): {description}")
