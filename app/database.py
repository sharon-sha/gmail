from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_app_settings

settings = get_app_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine_kwargs = {"connect_args": connect_args}
if settings.database_url.startswith("postgresql"):
    engine_kwargs["pool_pre_ping"] = True
engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_oauth_state_columns()
    _ensure_integration_columns()


def _ensure_integration_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(integrations)").fetchall()
        }
        if "telegram_bot_token" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE integrations ADD COLUMN telegram_bot_token TEXT"
            )
        if "telegram_bot_username" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE integrations ADD COLUMN telegram_bot_username VARCHAR(64)"
            )


def _ensure_oauth_state_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(oauth_states)").fetchall()
        }
        if "code_verifier" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE oauth_states ADD COLUMN code_verifier VARCHAR(128)"
            )
