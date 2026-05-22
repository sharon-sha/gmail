import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_app_url() -> str:
    for key in ("APP_URL", "RENDER_EXTERNAL_URL"):
        value = os.getenv(key, "").strip().rstrip("/")
        if value:
            return value
    return "http://localhost:8000"


def _add_sslmode(url: str) -> str:
    host = make_url(url).host or ""
    if "sslmode=" in url:
        return url
    if "render.com" in url or "dpg-" in host or "neon.tech" in url:
        return f"{url}&sslmode=require" if "?" in url else f"{url}?sslmode=require"
    return url


def _build_database_url_from_parts() -> str | None:
    host = (
        os.getenv("POSTGRES_HOST", "")
        or os.getenv("PGHOST", "")
        or os.getenv("DATABASE_HOST", "")
    ).strip()
    user = (
        os.getenv("POSTGRES_USER", "")
        or os.getenv("PGUSER", "")
        or os.getenv("DATABASE_USER", "")
    ).strip()
    password = (
        os.getenv("POSTGRES_PASSWORD", "")
        or os.getenv("PGPASSWORD", "")
        or os.getenv("DATABASE_PASSWORD", "")
    ).strip()
    database = (
        os.getenv("POSTGRES_DB", "")
        or os.getenv("PGDATABASE", "")
        or os.getenv("DATABASE_NAME", "")
        or "mailbrief"
    ).strip()
    port = (
        os.getenv("POSTGRES_PORT", "")
        or os.getenv("PGPORT", "")
        or os.getenv("DATABASE_PORT", "")
        or "5432"
    ).strip()

    if not host or not user or not password:
        return None

    return (
        f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{quote_plus(database)}?sslmode=require"
    )


def _normalize_database_url(url: str) -> str:
    cleaned = url.strip().strip('"').strip("'")
    if not cleaned:
        raise ValueError("DATABASE_URL is empty")

    if cleaned.startswith("postgres://"):
        cleaned = cleaned.replace("postgres://", "postgresql+psycopg2://", 1)
    elif cleaned.startswith("postgresql://") and "+psycopg2" not in cleaned:
        cleaned = cleaned.replace("postgresql://", "postgresql+psycopg2://", 1)

    make_url(cleaned)
    return _add_sslmode(cleaned)


def _build_database_url() -> str:
    parts_url = _build_database_url_from_parts()
    if parts_url:
        return parts_url

    explicit_url = os.getenv("DATABASE_URL", "").strip().strip('"').strip("'")
    if explicit_url:
        try:
            return _normalize_database_url(explicit_url)
        except Exception as exc:
            raise ValueError(
                "DATABASE_URL is invalid. Link PostgreSQL in Render or set "
                "POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB."
            ) from exc

    return f"sqlite:///{BASE_DIR / 'mailbrief.db'}"


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
