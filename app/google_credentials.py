from __future__ import annotations

import json
import os
from pathlib import Path

from app.config import BASE_DIR


def load_google_client_config() -> dict:
    raw_json = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    if raw_json:
        return json.loads(raw_json)

    for name in ("gmailautomation.json", "credentials.json"):
        path = BASE_DIR / name
        if path.exists():
            with path.open(encoding="utf-8") as handle:
                return json.load(handle)

    raise FileNotFoundError(
        "Google OAuth credentials missing. Set GOOGLE_CREDENTIALS_JSON or add gmailautomation.json."
    )
