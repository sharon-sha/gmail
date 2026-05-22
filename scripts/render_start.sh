#!/usr/bin/env bash
set -euo pipefail

echo "Starting MailBrief..."
echo "PORT=${PORT:-8000}"
echo "WEB_CONCURRENCY=${WEB_CONCURRENCY:-1}"
echo "POSTGRES_HOST=${POSTGRES_HOST:-not set}"
echo "RENDER=${RENDER:-not set}"

python scripts/init_db.py

exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
