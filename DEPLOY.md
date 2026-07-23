# Cliperry — Deployment

Production stack: Docker Compose (`docker-compose.prod.yml`) — PostgreSQL, Redis, API, Celery worker, optional Telegram bot.

Pipeline (GitHub Actions):

```text
push main → build (GHCR) → deploy VPS → healthcheck
```

---

## 1. Install Docker (VPS)

Ubuntu 22.04 / 24.04:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git rsync
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker "$USER"
# re-login, then:
docker version
docker compose version
```

Create deploy directory:

```bash
sudo mkdir -p /opt/cliperry
sudo chown "$USER":"$USER" /opt/cliperry
```

Put a reverse proxy (nginx / Caddy / Traefik) in front of `BACKEND_HOST_PORT` (default `8000`) with TLS. Set `TRUST_PROXY_HEADERS=true` and real `TRUSTED_HOSTS`.

---

## 2. Configure environment

On the VPS:

```bash
cd /opt/cliperry
# after first sync / clone:
cp .env.production.example .env
nano .env   # or vim
```

Replace every `CHANGE_ME` value:

| Variable | Notes |
|---|---|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `POSTGRES_PASSWORD` | strong password; keep in sync with `DATABASE_URL*` |
| `ADMIN_PASSWORD` | ≥ 12 chars |
| `TRUSTED_HOSTS` | public hostnames, no `*` |
| `CORS_ORIGINS` | real HTTPS origins |
| `CORS_EXTENSION_IDS` | Chrome extension id(s) |
| `BACKEND_PUBLIC_URL` | public API URL, e.g. `https://api.example.com` |
| `TELEGRAM_BOT_TOKEN` | optional; enables bot profile |
| `CLIPERRY_IMAGE` | set by CD; for manual: `cliperry-backend:latest` |

Never commit `.env`.

SSH key for CD: create a deploy user key on the VPS and add the **private** key to GitHub Secrets (see below). Restrict the key to the deploy path if possible.

---

## 3. First launch (manual)

```bash
cd /opt/cliperry
chmod +x scripts/deploy.sh

# API + worker
./scripts/deploy.sh

# with Telegram bot
ENABLE_BOT=true ./scripts/deploy.sh
```

Or without the script:

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml --profile bot up -d --build
```

Checks:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
```

---

## 4. Updates

### Automatic (recommended)

Push to `main` → GitHub Actions CD builds the image, syncs the repo to the VPS, restarts Compose, then probes `/ready`.

### Manual on VPS

```bash
cd /opt/cliperry
git pull   # if you deploy via git clone
# or wait for rsync from CD

CLIPERRY_IMAGE=ghcr.io/<owner>/<repo>/cliperry-backend:<tag> ./scripts/deploy.sh
```

Rollback to a previous tag:

```bash
CLIPERRY_IMAGE=ghcr.io/<owner>/<repo>/cliperry-backend:<older-sha> ./scripts/deploy.sh
```

---

## 5. GitHub Actions CI/CD

Workflow: [`.github/workflows/cd.yml`](.github/workflows/cd.yml)

| Job | What it does |
|---|---|
| **Build** | Build `backend` Docker image → push to GHCR → run unit tests |
| **Deploy VPS** | `rsync` project → `docker login` GHCR → `scripts/deploy.sh` |
| **Healthcheck** | `GET {HEALTHCHECK_URL}/ready` from the runner |

### Repository secrets

| Secret | Description |
|---|---|
| `VPS_HOST` | VPS IP or hostname |
| `VPS_USER` | SSH user (e.g. `deploy`) |
| `VPS_SSH_PRIVATE_KEY` | Private key (PEM) for that user |
| `VPS_PORT` | SSH port (optional; default `22`) |
| `DEPLOY_PATH` | Absolute path, e.g. `/opt/cliperry` |
| `HEALTHCHECK_URL` | Public base URL, e.g. `https://api.example.com` |

### Repository variables (optional)

| Variable | Description |
|---|---|
| `ENABLE_BOT` | `true` to start Telegram bot on deploy |

### GitHub setup

1. Create environment **`production`** (Settings → Environments).
2. Add the secrets above.
3. Ensure Packages (GHCR) is allowed for Actions (`GITHUB_TOKEN` packages:write is in the workflow).
4. On the VPS, the deploy user must run `docker` without sudo (docker group) and write to `DEPLOY_PATH`.
5. First time: copy `.env` manually onto the VPS (CD never overwrites `.env`).

### Trigger

- Push to `main`
- Or **Actions → CD → Run workflow**

---

## 6. Useful commands

```bash
# status
docker compose -f docker-compose.prod.yml ps

# logs
docker compose -f docker-compose.prod.yml logs -f --tail=200 backend worker

# stop
docker compose -f docker-compose.prod.yml down

# DB backup
docker exec cliperry-postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

---

## 7. Checklist before go-live

- [ ] Strong `SECRET_KEY`, `POSTGRES_PASSWORD`, `ADMIN_PASSWORD`
- [ ] `APP_ENV=production`, `DEBUG=false`, `ENABLE_WORKER_TEST=false`
- [ ] TLS reverse proxy + `TRUSTED_HOSTS` / `TRUST_PROXY_HEADERS`
- [ ] CORS and extension IDs set
- [ ] `/ready` returns 200 behind the public URL
- [ ] GitHub secrets configured; test deploy via `workflow_dispatch`
