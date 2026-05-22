import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    groq_model: str
    telegram_bot_token: str
    telegram_chat_id: str
    poll_interval_seconds: int
    gmail_query: str
    credentials_file: Path
    token_file: Path


def get_settings() -> Settings:
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is required")
    if not telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    return Settings(
        groq_api_key=groq_api_key,
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "6862705647").strip(),
        poll_interval_seconds=max(10, int(os.getenv("POLL_INTERVAL_SECONDS", "60"))),
        gmail_query=os.getenv("GMAIL_QUERY", "").strip(),
        credentials_file=_resolve_credentials_file(BASE_DIR),
        token_file=BASE_DIR / "token.json",
    )


def _resolve_credentials_file(base_dir: Path) -> Path:
    for name in ("gmailautomation.json", "credentials.json"):
        path = base_dir / name
        if path.exists():
            return path
    return base_dir / "credentials.json"
