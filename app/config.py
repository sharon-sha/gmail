import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    if "sslmode=" not in url and ("render.com" in url or "neon.tech" in url):
        url += "&sslmode=require" if "?" in url else "?sslmode=require"

    return url


def _resolve_app_url() -> str:
    for key in ("APP_URL", "RENDER_EXTERNAL_URL"):
        value = os.getenv(key, "").strip().rstrip("/")
        if value:
            return value
    return "http://localhost:8000"


@dataclass(frozen=True)
class AppSettings:
    app_name: str
    app_url: str
    secret_key: str
    database_url: str
    groq_api_key: str
    groq_model: str
    gmail_credentials_file: Path
    gmail_redirect_uri: str
    poll_interval_seconds: int
    free_plan_monthly_limit: int


def get_app_settings() -> AppSettings:
    app_url = _resolve_app_url()
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    secret_key = os.getenv("SECRET_KEY", "change-me-in-production").strip()

    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is required")

    credentials_file = BASE_DIR / "gmailautomation.json"
    if not credentials_file.exists():
        credentials_file = BASE_DIR / "credentials.json"

    return AppSettings(
        app_name=os.getenv("APP_NAME", "MailBrief"),
        app_url=app_url,
        secret_key=secret_key,
        database_url=_build_database_url(),
        groq_api_key=groq_api_key,
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
        gmail_credentials_file=credentials_file,
        gmail_redirect_uri=os.getenv(
            "GMAIL_REDIRECT_URI",
            f"{app_url}/auth/gmail/callback",
        ),
        poll_interval_seconds=max(15, int(os.getenv("POLL_INTERVAL_SECONDS", "60"))),
        free_plan_monthly_limit=int(os.getenv("FREE_PLAN_MONTHLY_LIMIT", "100")),
    )


def _build_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL", "").strip()
    if explicit_url:
        return _normalize_database_url(explicit_url)

    postgres_host = os.getenv("POSTGRES_HOST", "").strip()
    if not postgres_host:
        return f"sqlite:///{BASE_DIR / 'mailbrief.db'}"

    postgres_user = os.getenv("POSTGRES_USER", "mailbrief").strip()
    postgres_password = os.getenv("POSTGRES_PASSWORD", "").strip()
    postgres_host = os.getenv("POSTGRES_HOST", "localhost").strip()
    postgres_port = os.getenv("POSTGRES_PORT", "5432").strip()
    postgres_db = os.getenv("POSTGRES_DB", "mailbrief").strip()

    if not postgres_password:
        raise ValueError("POSTGRES_PASSWORD is required when using PostgreSQL")

    return (
        f"postgresql+psycopg2://{postgres_user}:{postgres_password}"
        f"@{postgres_host}:{postgres_port}/{postgres_db}"
    )
