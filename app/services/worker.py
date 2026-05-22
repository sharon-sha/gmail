from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import get_app_settings
from app.database import SessionLocal
from app.models import ActivityLog, Integration, ProcessedEmail, User
from app.services.gmail_service import list_inbox_messages
from app.services.summarizer import summarize_email
from app.services.telegram import send_telegram_message

logger = logging.getLogger(__name__)
settings = get_app_settings()


def _monthly_usage(db: Session, user_id: int) -> int:
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(
        select(func.count())
        .select_from(ProcessedEmail)
        .where(
            ProcessedEmail.user_id == user_id,
            ProcessedEmail.created_at >= start_of_month,
        )
    ) or 0


def _log_activity(db: Session, user_id: int, message: str, level: str = "info") -> None:
    db.add(ActivityLog(user_id=user_id, message=message, level=level))


def process_user_emails(db: Session, user: User) -> int:
    if user.integration:
        db.refresh(user.integration)
    integration = user.integration
    if not integration or not integration.automation_enabled:
        return 0
    if not integration.gmail_token_json:
        integration.last_error = "Connect Gmail first"
        db.commit()
        return 0
    if not integration.telegram_bot_token:
        integration.last_error = "Add your Telegram bot token"
        db.commit()
        return 0
    if not integration.telegram_chat_id:
        integration.last_error = "Add your Telegram chat ID"
        db.commit()
        return 0

    usage = _monthly_usage(db, user.id)
    if user.plan == "free" and usage >= settings.free_plan_monthly_limit:
        integration.last_error = "Monthly free plan limit reached"
        db.commit()
        return 0

    processed_ids = {
        row[0]
        for row in db.execute(
            select(ProcessedEmail.message_id).where(ProcessedEmail.user_id == user.id)
        ).all()
    }

    emails = list_inbox_messages(
        integration.gmail_token_json,
        query=integration.gmail_query,
        max_results=10,
    )
    new_emails = [email for email in emails if email.id not in processed_ids]
    processed_count = 0

    for email in reversed(new_emails):
        if user.plan == "free" and _monthly_usage(db, user.id) >= settings.free_plan_monthly_limit:
            break

        summary = summarize_email(email)
        send_telegram_message(
            integration.telegram_bot_token,
            integration.telegram_chat_id,
            summary,
        )
        db.add(
            ProcessedEmail(
                user_id=user.id,
                message_id=email.id,
                subject=email.subject,
                summary=summary,
            )
        )
        _log_activity(db, user.id, f"Sent summary for: {email.subject}")
        processed_count += 1

    integration.last_checked_at = datetime.utcnow()
    integration.last_error = None if processed_count or not new_emails else integration.last_error
    db.commit()
    return processed_count


def run_worker_cycle() -> None:
    db = SessionLocal()
    try:
        users = db.scalars(
            select(User)
            .join(Integration)
            .where(Integration.automation_enabled.is_(True))
            .options(joinedload(User.integration))
        ).all()

        for user in users:
            try:
                count = process_user_emails(db, user)
                if count:
                    logger.info("Processed %s emails for user %s", count, user.email)
            except Exception as exc:
                logger.exception("Worker failed for user %s", user.email)
                if user.integration:
                    user.integration.last_error = str(exc)
                    _log_activity(db, user.id, str(exc), level="error")
                    db.commit()
    finally:
        db.close()
