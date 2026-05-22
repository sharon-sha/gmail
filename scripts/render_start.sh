#!/usr/bin/env bash
set -euo pipefail

python scripts/init_db.py
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b "0.0.0.0:${PORT:-8000}" \
  --workers 2 \
  --timeout 120
