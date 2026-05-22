from __future__ import annotations

import secrets

from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from app.config import get_app_settings
from app.google_credentials import load_google_client_config
from app.models import OAuthState
from gmail_client import SCOPES

settings = get_app_settings()


def _load_client_config() -> dict:
    return load_google_client_config()


def _create_flow() -> Flow:
    return Flow.from_client_config(
        _load_client_config(),
        scopes=SCOPES,
        redirect_uri=settings.gmail_redirect_uri,
    )


def create_gmail_auth_url(db: Session, user_id: int) -> str:
    flow = _create_flow()
    state = secrets.token_urlsafe(32)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )

    db.add(
        OAuthState(
            state=state,
            user_id=user_id,
            code_verifier=flow.code_verifier,
        )
    )
    db.commit()
    return auth_url


def exchange_gmail_code(db: Session, code: str, state: str, user_id: int) -> str:
    oauth_state = db.get(OAuthState, state)
    if not oauth_state:
        raise ValueError("Invalid or expired OAuth state")
    if oauth_state.user_id != user_id:
        raise ValueError("OAuth state does not match the current user")
    if not oauth_state.code_verifier:
        raise ValueError("Missing OAuth code verifier. Click Connect Gmail again.")

    flow = _create_flow()
    flow.code_verifier = oauth_state.code_verifier
    flow.fetch_token(code=code)
    token_json = flow.credentials.to_json()

    db.delete(oauth_state)
    db.commit()
    return token_json
