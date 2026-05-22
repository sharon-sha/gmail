#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database import init_db


def main() -> None:
    init_db()
    print("Database schema initialized.")


if __name__ == "__main__":
    main()
