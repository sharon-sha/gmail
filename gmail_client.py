from __future__ import annotations

import base64
import json
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


@dataclass(frozen=True)
class EmailMessage:
    id: str
    thread_id: str
    subject: str
    snippet: str


class GmailClient:
    def __init__(self, credentials_file: Path, token_file: Path) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file
        self._service = build("gmail", "v1", credentials=self._get_credentials())

    def _get_credentials(self) -> Credentials:
        creds: Credentials | None = None

        if self._token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self._token_file), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self._credentials_file.exists():
                    raise FileNotFoundError(
                        f"Missing {self._credentials_file.name}. "
                        "Add gmailautomation.json or credentials.json from Google Cloud Console."
                    )
                creds = _authorize(self._credentials_file, SCOPES)

            self._token_file.write_text(creds.to_json())

        return creds

    def list_new_messages(self, query: str = "", max_results: int = 10) -> list[EmailMessage]:
        list_kwargs: dict = {
            "userId": "me",
            "labelIds": ["INBOX"],
            "maxResults": max_results,
        }
        if query:
            list_kwargs["q"] = query

        response = (
            self._service.users()
            .messages()
            .list(**list_kwargs)
            .execute()
        )

        messages = response.get("messages", [])
        return [self.get_message(message["id"]) for message in messages]

    def get_message(self, message_id: str) -> EmailMessage:
        message = (
            self._service.users()
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

    def get_message_body(self, message_id: str) -> str:
        message = (
            self._service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return self._extract_body(message.get("payload", {}))

    def _extract_body(self, payload: dict) -> str:
        if not payload:
            return ""

        body_data = payload.get("body", {}).get("data")
        if body_data:
            return self._decode_body(body_data)

        for part in payload.get("parts", []):
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain":
                part_data = part.get("body", {}).get("data")
                if part_data:
                    return self._decode_body(part_data)

        for part in payload.get("parts", []):
            text = self._extract_body(part)
            if text:
                return text

        return ""

    @staticmethod
    def _decode_body(data: str) -> str:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")


def _authorize(credentials_file: Path, scopes: list[str]) -> Credentials:
    with credentials_file.open(encoding="utf-8") as handle:
        client_config = json.load(handle)

    if "installed" in client_config:
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), scopes)
        return flow.run_local_server(port=0)

    if "web" not in client_config:
        raise ValueError(
            f"{credentials_file.name} must contain either 'installed' or 'web' OAuth credentials"
        )

    redirect_uri = client_config["web"]["redirect_uris"][0]
    flow = Flow.from_client_config(client_config, scopes, redirect_uri=redirect_uri)
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")

    print("Opening browser for Gmail authorization...")
    print(f"If it does not open, visit:\n{auth_url}\n")

    auth_code = _wait_for_oauth_callback(redirect_uri, auth_url)
    flow.fetch_token(code=auth_code)
    return flow.credentials


def _wait_for_oauth_callback(redirect_uri: str, auth_url: str) -> str:
    parsed = urlparse(redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    callback_path = parsed.path or "/"

    class OAuthCallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.split("?", 1)[0] != callback_path:
                self.send_error(404)
                return

            query = parse_qs(urlparse(self.path).query)
            if "code" in query:
                self.server.auth_code = query["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h1>Authorization successful</h1>"
                    b"<p>You can close this tab and return to the terminal.</p></body></html>"
                )
                return

            self.server.auth_error = query.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<html><body><h1>Authorization failed</h1>"
                f"<p>{self.server.auth_error}</p></body></html>".encode()
            )

        def log_message(self, format: str, *args) -> None:
            return

    server = HTTPServer((host, port), OAuthCallbackHandler)
    server.auth_code = None
    server.auth_error = None

    webbrowser.open(auth_url)

    print(f"Waiting for Google OAuth callback on {redirect_uri}")
    print("If port 5678 is in use, stop n8n first.")

    try:
        while server.auth_code is None and server.auth_error is None:
            server.handle_request()
    except OSError as exc:
        raise RuntimeError(
            f"Could not listen on {host}:{port}. "
            "Stop n8n or anything else using that port, then try again."
        ) from exc

    server.server_close()

    if server.auth_error:
        raise RuntimeError(f"OAuth authorization failed: {server.auth_error}")

    return server.auth_code
