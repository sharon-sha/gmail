# MailBrief — Gmail to Telegram SaaS

Multi-user SaaS that connects Gmail, summarizes new emails with Groq AI, and sends summaries to Telegram.

## Features

- User signup / login
- Per-user Gmail OAuth
- Dashboard to manage Telegram bot token, chat ID, and automation
- Background worker polls all active users every 60 seconds
- Free plan with 100 summaries/month
- Activity log and recent summary history

## PostgreSQL setup (accounts)

MailBrief stores user accounts, integrations, and activity in PostgreSQL.

### 1. Create database and role

```bash
chmod +x scripts/postgres/setup.sh
./scripts/postgres/setup.sh
```

Or manually:

```bash
sudo -u postgres psql -f scripts/postgres/setup.sql
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
```

This creates:
- Database: `mailbrief`
- User: `mailbrief`
- Password: `mailbrief_dev_password` (change in production)

### 2. Configure `.env`

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mailbrief
POSTGRES_USER=mailbrief
POSTGRES_PASSWORD=mailbrief_dev_password
```

### Tables created

| Table | Purpose |
|---|---|
| `users` | Accounts (email, password, plan) |
| `integrations` | Gmail/Telegram settings per user |
| `processed_emails` | Summary history |
| `activity_logs` | Automation events |
| `oauth_states` | Gmail OAuth flow state |

If PostgreSQL vars are not set, the app falls back to SQLite (`mailbrief.db`).

## Quick start

```bash
cd /home/sha/Gmail
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # if needed
python run.py
```

Open **http://localhost:8000**

## Google OAuth setup

Add this redirect URI in [Google Cloud Console](https://console.cloud.google.com/) for your OAuth client:

```
http://localhost:8000/auth/gmail/callback
```

Keep `gmailautomation.json` in the project root.

## User flow

1. Register at `/register`
2. Connect Gmail from the dashboard
3. Create a bot with [@BotFather](https://t.me/BotFather) and paste your bot token
4. Message your bot on Telegram and paste your chat ID
5. Enable automation

## CLI mode (single user)

The original script still works:

```bash
python main.py
```

## Project layout

```
app/
  main.py              FastAPI app + background worker
  routers/             Pages and Gmail OAuth
  services/            Gmail, Groq, Telegram, worker
  templates/           SaaS UI
  static/              CSS
run.py                 Start the web app
main.py                Legacy single-user CLI
```

## Environment

| Variable | Description |
|---|---|
| `APP_URL` | Public app URL |
| `SECRET_KEY` | JWT signing secret |
| `POSTGRES_*` or `DATABASE_URL` | PostgreSQL connection |
| `GROQ_API_KEY` | Platform Groq API key |
| `GMAIL_REDIRECT_URI` | Google OAuth callback |
| `FREE_PLAN_MONTHLY_LIMIT` | Free tier limit (default 100) |

Each user adds their own **Telegram bot token** and **chat ID** in the dashboard.

Legacy CLI (`python main.py`) still uses `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`.

## n8n workflow

Original n8n export: `n8n/gmail-trigger-workflow.json`
