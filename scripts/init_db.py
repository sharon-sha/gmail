#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from app.database import init_db

    init_db()
    print("Database schema initialized.")
except Exception as exc:
    print("Database initialization failed:", exc, file=sys.stderr)
    print(
        "Check Render env vars: POSTGRES_HOST, POSTGRES_USER, "
        "POSTGRES_PASSWORD, POSTGRES_DB",
        file=sys.stderr,
    )
    raise
