# Interview Sarathi — IONOS VPS Deployment Guide

## What to buy on IONOS
- **VPS Linux S** (2 vCPU, 4GB RAM, 80GB SSD) — ~€5-8/month
- Your domain is already bought ✅
- **Managed PostgreSQL** is optional — SQLite works for < 1000 users, switch later

---

## Step 1 — First login to your VPS

```bash
ssh root@YOUR_VPS_IP
```

Update everything:
```bash
apt update && apt upgrade -y
```

Create a non-root user:
```bash
adduser sarathi
usermod -aG sudo sarathi
```

---

## Step 2 — Install dependencies

```bash
apt install -y python3.11 python3.11-venv python3-pip nginx certbot python3-certbot-nginx git curl
```

---

## Step 3 — Install PostgreSQL (optional, recommended for production)

```bash
apt install -y postgresql postgresql-contrib
sudo -u postgres psql
```

Inside PostgreSQL shell:
```sql
CREATE USER sarathi_user WITH PASSWORD 'STRONG_PASSWORD_HERE';
CREATE DATABASE sarathi_db OWNER sarathi_user;
\q
```

Install Python PostgreSQL driver:
```bash
pip install psycopg2-binary
```

---

## Step 4 — Upload and set up the app

```bash
mkdir -p /var/www/interviewsarathi
cd /var/www/interviewsarathi
```

Upload your zip from local machine:
```bash
# Run this on YOUR machine (not the server):
scp Interview_sarathi_2_fixed.zip root@YOUR_VPS_IP:/var/www/interviewsarathi/
```

Back on the server:
```bash
cd /var/www/interviewsarathi
unzip Interview_sarathi_2_fixed.zip
cp -r interview_sarathi_fixed/backend/* /var/www/interviewsarathi/backend/
cp -r interview_sarathi_fixed/frontend  /var/www/interviewsarathi/frontend   # if you have one
```

Create Python virtual environment:
```bash
cd /var/www/interviewsarathi
python3.11 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings \
    python-jose passlib[bcrypt] httpx slowapi pdfminer.six \
    python-docx psycopg2-binary alembic
```

---

## Step 5 — Configure environment

```bash
cp /var/www/interviewsarathi/backend/deploy/.env.production \
   /var/www/interviewsarathi/backend/.env
nano /var/www/interviewsarathi/backend/.env
```

Fill in:
- `DATABASE_URL` with your PostgreSQL credentials
- `SECRET_KEY` — generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `GEMINI_API_KEY`
- `FRONTEND_URL=https://yourdomain.com`
- `SMTP_USER` and `SMTP_PASSWORD` (your IONOS email)
- `ADMIN_SECRET_KEY` — generate same way as SECRET_KEY

---

## Step 6 — Point your domain to the VPS

In **IONOS DNS settings** for your domain:
```
A record:  @    →  YOUR_VPS_IP
A record:  www  →  YOUR_VPS_IP
```

Wait 5-15 minutes for DNS to propagate.

---

## Step 7 — Set up Nginx + SSL

Copy the nginx config:
```bash
cp /var/www/interviewsarathi/backend/deploy/nginx.conf \
   /etc/nginx/sites-available/interviewsarathi

# Edit: replace yourdomain.com with your actual domain
nano /etc/nginx/sites-available/interviewsarathi

ln -s /etc/nginx/sites-available/interviewsarathi /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default   # remove default site
nginx -t                               # test config
systemctl reload nginx
```

Get free SSL certificate:
```bash
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Auto-renew SSL (certbot does this automatically, but verify):
```bash
certbot renew --dry-run
```

---

## Step 8 — Run the app as a system service

```bash
cp /var/www/interviewsarathi/backend/deploy/interviewsarathi.service \
   /etc/systemd/system/interviewsarathi.service

systemctl daemon-reload
systemctl enable interviewsarathi
systemctl start interviewsarathi
systemctl status interviewsarathi   # should say "active (running)"
```

---

## Step 9 — Verify everything works

```bash
curl https://yourdomain.com/health
```

Expected response:
```json
{"status": "ok", "version": "2.2.0", ...}
```

Visit `https://yourdomain.com/docs` to see all API endpoints.

---

## Step 10 — Seed the question packs

```bash
curl -X POST https://yourdomain.com/api/packs/seed \
  -H "X-Admin-Key: YOUR_ADMIN_SECRET_KEY"
```

---

## Useful commands after deployment

| Task | Command |
|---|---|
| View live logs | `journalctl -u interviewsarathi -f` |
| Restart app | `systemctl restart interviewsarathi` |
| Update code | `scp new_zip root@IP:/tmp && unzip && cp...` then restart |
| Check nginx logs | `tail -f /var/log/nginx/error.log` |
| DB backup | `pg_dump sarathi_db > backup_$(date +%Y%m%d).sql` |
| SSL renewal | `certbot renew` (auto, but manual if needed) |

---

## IONOS-specific SMTP settings
Host: `smtp.ionos.com`
Port: `587`
Security: `STARTTLS`
Username: your full IONOS email address
Password: your IONOS email password
