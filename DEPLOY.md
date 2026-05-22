# Publish MailBrief as a SaaS

## Before you go live — checklist

### 1. Domain + HTTPS
- Buy a domain (Namecheap, Cloudflare, Google Domains, etc.)
- Point DNS **A record** to your server IP
- Enable HTTPS with Let's Encrypt (required for production cookies and OAuth)

### 2. Google OAuth (required)
In [Google Cloud Console](https://console.cloud.google.com/):

1. Open project `gmail-remen` (or create a new one)
2. **APIs & Services → OAuth consent screen**
   - Set to **External**
   - Add app name, support email, logo
   - Add scopes: `https://www.googleapis.com/auth/gmail.readonly`
   - Add test users while in testing, or **Publish app** for public use
3. **Credentials → OAuth 2.0 Client**
   - Add **Authorized redirect URI**:
     ```
     https://yourdomain.com/auth/gmail/callback
     ```
   - Add **Authorized JavaScript origin**:
     ```
     https://yourdomain.com
     ```
4. Keep `gmailautomation.json` on the server (never commit it to git)

### 3. Environment variables
Copy `.env.production.example` to `.env` on the server:

```bash
openssl rand -hex 32   # use output as SECRET_KEY
```

| Variable | Production value |
|---|---|
| `APP_URL` | `https://yourdomain.com` |
| `SECRET_KEY` | long random string |
| `GROQ_API_KEY` | your Groq key (you pay for all users) |
| `DATABASE_URL` | PostgreSQL connection string |
| `GMAIL_REDIRECT_URI` | `https://yourdomain.com/auth/gmail/callback` |

### 4. PostgreSQL
Use managed PostgreSQL (recommended):
- [Neon](https://neon.tech) — free tier
- [Supabase](https://supabase.com)
- [Railway](https://railway.app)
- Or self-host with `docker-compose.prod.yml`

### 5. Groq API
- Add billing/limits at [console.groq.com](https://console.groq.com)
- You are the platform — all user summaries use **your** `GROQ_API_KEY`
- Set rate limits / free plan cap in `FREE_PLAN_MONTHLY_LIMIT`

### 6. Telegram
- Each user brings their own bot from @BotFather
- No platform Telegram token needed for SaaS

---

## Option A — Docker (easiest)

On a VPS (DigitalOcean, Hetzner, AWS EC2, etc.):

```bash
git clone <your-repo> /opt/mailbrief
cd /opt/mailbrief
cp .env.production.example .env
# edit .env with real values
# upload gmailautomation.json

docker compose -f docker-compose.prod.yml up -d --build
```

Put **nginx** or **Caddy** in front for HTTPS on port 443 → proxy to port 8000.

---

## Option B — VPS with systemd + nginx

```bash
# On Ubuntu server
sudo apt update && sudo apt install -y python3-venv nginx certbot python3-certbot-nginx postgresql

sudo mkdir -p /opt/mailbrief
sudo chown $USER:$USER /opt/mailbrief
# upload project files to /opt/mailbrief

cd /opt/mailbrief
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt gunicorn
cp .env.production.example .env
# edit .env

sudo -u postgres psql -f scripts/postgres/setup.sql
python scripts/init_db.py

# systemd
sudo cp deploy/mailbrief.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mailbrief

# nginx + SSL
sudo cp deploy/nginx.conf /etc/nginx/sites-available/mailbrief
sudo ln -s /etc/nginx/sites-available/mailbrief /etc/nginx/sites-enabled/
sudo certbot --nginx -d yourdomain.com
sudo systemctl reload nginx
```

---

## Option C — Railway / Render (managed)

See **`DEPLOY_RENDER.md`** for the full Render guide.

Quick summary for Render:
1. Push to GitHub
2. New → Blueprint → connect repo (uses `render.yaml`)
3. Set `GROQ_API_KEY` and `GOOGLE_CREDENTIALS_JSON` in Render dashboard
4. Update Google OAuth redirect to `https://YOUR-APP.onrender.com/auth/gmail/callback`

---

## Option D — Railway / other platforms

## Security before launch

- [ ] Change `SECRET_KEY` from default
- [ ] Use HTTPS only (`APP_URL=https://...`)
- [ ] Strong PostgreSQL password
- [ ] Never commit `.env` or `gmailautomation.json`
- [ ] Google OAuth app published (or test users added)
- [ ] Set Groq usage limits / billing alerts
- [ ] Back up PostgreSQL regularly

---

## After launch

1. Open `https://yourdomain.com`
2. Register a test account
3. Connect Gmail → add Telegram bot → enable automation
4. Send yourself a test email
5. Confirm summary arrives in Telegram

---

## Monetization (next steps)

- Stripe for paid plans (`pro` plan in `users.plan`)
- Custom domain per tenant
- Email verification on signup
- Admin panel for usage stats
