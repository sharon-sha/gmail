#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from config import get_settings
from gmail_client import GmailClient
from summarizer import EmailSummarizer
from telegram_client import TelegramClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent / "processed_messages.json"


def load_processed_ids() -> set[str]:
    if not STATE_FILE.exists():
        return set()

    try:
        data = json.loads(STATE_FILE.read_text())
        return set(data.get("processed_ids", []))
    except json.JSONDecodeError:
        return set()


def save_processed_ids(processed_ids: set[str]) -> None:
    STATE_FILE.write_text(
        json.dumps({"processed_ids": sorted(processed_ids)}, indent=2)
    )


def process_new_emails() -> int:
    settings = get_settings()
    gmail = GmailClient(settings.credentials_file, settings.token_file)
    summarizer = EmailSummarizer(settings)
    telegram = TelegramClient(settings)

    processed_ids = load_processed_ids()
    emails = gmail.list_new_messages(query=settings.gmail_query)
    new_emails = [email for email in emails if email.id not in processed_ids]

    if not new_emails:
        logger.info("No new emails")
        return 0

    for email in reversed(new_emails):
        logger.info("Summarizing: %s", email.subject)
        summary = summarizer.summarize(email)
        telegram.send_message(summary)
        processed_ids.add(email.id)
        logger.info("Sent summary to Telegram for message %s", email.id)

    save_processed_ids(processed_ids)
    return len(new_emails)


def main() -> None:
    settings = get_settings()
    logger.info(
        "Gmail trigger started (poll every %ss, model=%s)",
        settings.poll_interval_seconds,
        settings.groq_model,
    )

    while True:
        try:
            count = process_new_emails()
            if count:
                logger.info("Processed %s new email(s)", count)
        except Exception:
            logger.exception("Error while processing emails")

        time.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    main()
