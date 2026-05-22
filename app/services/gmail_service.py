from __future__ import annotations

import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from gmail_client import SCOPES, EmailMessage


def credentials_from_token(token_json: str) -> Credentials:
    creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def get_gmail_profile(token_json: str) -> str:
    creds = credentials_from_token(token_json)
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "connected@gmail.com")


def list_inbox_messages(token_json: str, query: str = "", max_results: int = 10) -> list[EmailMessage]:
    creds = credentials_from_token(token_json)
    service = build("gmail", "v1", credentials=creds)

    list_kwargs: dict = {
        "userId": "me",
        "labelIds": ["INBOX"],
        "maxResults": max_results,
    }
    if query:
        list_kwargs["q"] = query

    response = service.users().messages().list(**list_kwargs).execute()
    messages = response.get("messages", [])
    return [_get_message(service, message["id"]) for message in messages]


def _get_message(service, message_id: str) -> EmailMessage:
    message = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="metadata")
        .execute()
    )
    headers = {
        header["name"].lower(): header["value"]
        for header in message.get("payload", {}).get("headers", [])
    }
    return EmailMessage(
        id=message["id"],
        thread_id=message.get("threadId", ""),
        subject=headers.get("subject", "(no subject)"),
        snippet=message.get("snippet", ""),
    )
