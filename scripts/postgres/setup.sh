#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SQL_FILE="$ROOT_DIR/scripts/postgres/setup.sql"

echo "Creating PostgreSQL role and database for MailBrief..."
sudo -u postgres psql -f "$SQL_FILE"

echo
echo "Initializing tables..."
cd "$ROOT_DIR"
source .venv/bin/activate
python scripts/init_db.py

echo
echo "PostgreSQL ready."
echo "DATABASE_URL=postgresql+psycopg2://mailbrief:mailbrief_dev_password@localhost:5432/mailbrief"
