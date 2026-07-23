# Cliperry — полный гайд по запуску и деплою

Стек: FastAPI + Postgres + Redis + Celery (+ Beat) + опционально Telegram-бот.  
Платформа сейчас: **YouTube only** (soft-launch).

Автодеплой:

```text
git push main → GitHub Actions → build GHCR → rsync на VPS → docker compose → /ready
```

Репозиторий: https://github.com/K0DDO/Cliperry

---

## Содержание

1. [Что нужно](#1-что-нужно)
2. [Подготовка VPS](#2-подготовка-vps)
3. [Docker](#3-docker)
4. [Первый деплой кода](#4-первый-деплой-кода)
5. [Файл `.env`](#5-файл-env)
6. [Reverse proxy + TLS (Caddy)](#6-reverse-proxy--tls-caddy)
7. [Первый запуск стека](#7-первый-запуск-стека)
8. [Проверки](#8-проверки)
9. [Telegram-бот](#9-telegram-бот)
10. [Chrome Extension](#10-chrome-extension)
11. [Автодеплой GitHub Actions](#11-автодеплой-github-actions)
12. [Обновления и откат](#12-обновления-и-откат)
13. [Бэкапы и логи](#13-бэкапы-и-логи)
14. [Чеклист go-live](#14-чеклист-go-live)
15. [Типичные проблемы](#15-типичные-проблемы)

---

## 1. Что нужно

| Вещь | Зачем |
|---|---|
| VPS Ubuntu 22.04/24.04 | ≥ 2 GB RAM, 2 CPU, 40 GB SSD |
| Домен | например `api.yourdomain.com` → A-запись на IP VPS |
| GitHub-репозиторий | уже есть: `K0DDO/Cliperry` |
| SSH-доступ к VPS | для ручного деплоя и CD |
| (опционально) Telegram BotFather token | бот |
| (опционально) cookies YouTube | если VPS IP режется YouTube |

Локально для разработки достаточно `docker compose up` (не prod).

---

## 2. Подготовка VPS

Зайди по SSH:

```bash
ssh root@YOUR_VPS_IP
```

Создай пользователя для деплоя (не работай постоянно из root):

```bash
adduser deploy
usermod -aG sudo deploy
# если используешь ключи — скопируй свой pubkey в /home/deploy/.ssh/authorized_keys
su - deploy
```

Создай каталог приложения:

```bash
sudo mkdir -p /opt/cliperry /opt/cliperry/backups
sudo chown -R deploy:deploy /opt/cliperry
```

Открой порты (UFW):

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

**Важно:** порт `8000` наружу **не открывай** — backend слушает только `127.0.0.1:8000`.

DNS: у регистратора домена создай A-запись:

```text
api.yourdomain.com  →  YOUR_VPS_IP
```

---

## 3. Docker

Под пользователем `deploy` (или с `sudo`):

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
sudo usermod -aG docker deploy
```

Выйди из SSH и зайди снова, затем:

```bash
docker version
docker compose version
```

---

## 4. Первый деплой кода

### Вариант A — git clone (проще для ручного старта)

```bash
cd /opt
git clone https://github.com/K0DDO/Cliperry.git cliperry
cd /opt/cliperry
```

### Вариант B — ждать rsync от GitHub Actions

CD сам положит файлы в `DEPLOY_PATH` (`/opt/cliperry`).  
Но **первый раз** `.env` всё равно нужно создать вручную (см. ниже).

---

## 5. Файл `.env`

```bash
cd /opt/cliperry
cp .env.production.example .env
nano .env
```

Сгенерируй секреты:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
# ещё раз для пароля БД / админки
```

### Обязательно заполни

| Переменная | Пример | Комментарий |
|---|---|---|
| `SECRET_KEY` | длинная строка ≥ 32 | подпись токенов скачивания |
| `POSTGRES_PASSWORD` | сильный пароль | тот же в `DATABASE_URL*` |
| `DATABASE_URL` | `postgresql+asyncpg://cliperry:PASS@postgres:5432/cliperry` | PASS = POSTGRES_PASSWORD |
| `DATABASE_URL_SYNC` | `postgresql+psycopg2://cliperry:PASS@postgres:5432/cliperry` | то же |
| `ADMIN_PASSWORD` | ≥ 12 символов | панель `/admin` |
| `TRUSTED_HOSTS` | `api.yourdomain.com` | **без** `*` |
| `TRUST_PROXY_HEADERS` | `true` | за Caddy/nginx |
| `BACKEND_PUBLIC_URL` | `https://api.yourdomain.com` | ссылки в боте / files |
| `CORS_ORIGINS` | `https://yourdomain.com` | web UI если есть |
| `CORS_EXTENSION_IDS` | id расширения Chrome | иначе CORS с extension |
| `APP_ENV` | `production` | |
| `DEBUG` | `false` | |
| `ENABLE_WORKER_TEST` | `false` | |

`CLIPERRY_IMAGE` при ручном билде оставь `cliperry-backend:latest`.  
При автодеплое CD сам проставит `ghcr.io/k0ddo/cliperry/cliperry-backend:<sha>`.

**Никогда не коммить `.env` в git.**

---

## 6. Reverse proxy + TLS (Caddy)

Самый простой вариант — Caddy (авто-сертификаты Let's Encrypt).

```bash
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update
sudo apt-get install -y caddy
```

`/etc/caddy/Caddyfile`:

```caddy
api.yourdomain.com {
    encode gzip

    reverse_proxy 127.0.0.1:8000 {
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
        header_up Host {host}
    }
}
```

```bash
sudo systemctl reload caddy
sudo systemctl status caddy
```

Backend в prod уже биндится на `127.0.0.1:8000` — снаружи доступен только через Caddy на 443.

---

## 7. Первый запуск стека

```bash
cd /opt/cliperry
chmod +x scripts/deploy.sh backend/scripts/*.sh

# Без бота:
./scripts/deploy.sh

# Или вручную:
docker compose -f docker-compose.prod.yml up -d --build
```

Сервисы:

| Контейнер | Роль |
|---|---|
| `cliperry-postgres` | БД |
| `cliperry-redis` | брокер / rate limit / pubsub |
| `cliperry-backend` | FastAPI API + admin |
| `cliperry-worker` | скачивание yt-dlp |
| `cliperry-beat` | cleanup temp-файлов каждые 15 мин |
| `cliperry-bot` | Telegram (только с `--profile bot`) |

Миграции Alembic гоняются автоматически при старте backend (`entrypoint.sh`).

---

## 8. Проверки

На VPS:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
docker compose -f docker-compose.prod.yml ps
```

Снаружи:

```bash
curl -fsS https://api.yourdomain.com/health
curl -fsS https://api.yourdomain.com/ready
```

Админка: `https://api.yourdomain.com/admin`  
Логин/пароль из `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`).

Smoke API:

```bash
curl -fsS -X POST https://api.yourdomain.com/api/analyze \
  -H "Content-Type: application/json" \
  -H "X-Device-Id: 00000000-0000-4000-8000-000000000001" \
  -d '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw"}'
```

---

## 9. Telegram-бот

1. У [@BotFather](https://t.me/BotFather) создай бота → получи token.
2. В `.env`:

```env
TELEGRAM_BOT_TOKEN=123456:ABCDEF...
BACKEND_PUBLIC_URL=https://api.yourdomain.com
```

3. Запуск:

```bash
cd /opt/cliperry
ENABLE_BOT=true ./scripts/deploy.sh
# или
docker compose -f docker-compose.prod.yml --profile bot up -d
```

4. В GitHub Variables поставь `ENABLE_BOT=true`, чтобы CD тоже поднимал бота.

Бот ходит в API по `BACKEND_PUBLIC_URL` (должен быть доступен с VPS — обычно это публичный HTTPS).

---

## 10. Chrome Extension

```bash
cd extension
npm install
# для prod API:
# создай .env / задай при билде:
# VITE_API_BASE_URL=https://api.yourdomain.com
npm run build
```

Загрузи `extension/dist` в Chrome → Developer mode → Load unpacked.

В Settings расширения укажи `https://api.yourdomain.com`.  
В `.env` на сервере добавь id расширения в `CORS_EXTENSION_IDS`.

---

## 11. Автодеплой GitHub Actions

Файл: [`.github/workflows/cd.yml`](.github/workflows/cd.yml)

### 11.1. SSH-ключ для CD

На VPS (под `deploy`):

```bash
ssh-keygen -t ed25519 -C "cliperry-cd" -f ~/.ssh/cliperry_cd -N ""
cat ~/.ssh/cliperry_cd.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
cat ~/.ssh/cliperry_cd   # ЭТО приватный ключ → в GitHub Secret
```

### 11.2. Secrets в GitHub

Репозиторий → **Settings → Secrets and variables → Actions → Secrets**:

| Secret | Значение |
|---|---|
| `VPS_HOST` | IP или hostname VPS |
| `VPS_USER` | `deploy` |
| `VPS_SSH_PRIVATE_KEY` | содержимое `~/.ssh/cliperry_cd` целиком |
| `VPS_PORT` | `22` (или свой) |
| `DEPLOY_PATH` | `/opt/cliperry` |
| `HEALTHCHECK_URL` | `https://api.yourdomain.com` |

### 11.3. Environment

Settings → Environments → создай **`production`**.  
Можно включить required reviewers для ручного approve перед деплоем.

### 11.4. Variables (опционально)

| Variable | Значение |
|---|---|
| `ENABLE_BOT` | `true` если нужен Telegram-бот |

### 11.5. Packages (GHCR)

CD пушит образ в `ghcr.io/k0ddo/cliperry/cliperry-backend`.  
`GITHUB_TOKEN` уже имеет `packages:write` в workflow.

На VPS при деплое делается `docker login ghcr.io` временным токеном из Actions.

Если package private — убедись, что Actions может читать/писать packages репозитория (Settings → Actions → General → Workflow permissions: Read and write).

### 11.6. Первый прогон CD

1. На VPS уже есть `/opt/cliperry/.env` (CD **не** затирает `.env`).
2. GitHub → **Actions → CD → Run workflow** (или `git push` в `main`).
3. Смотри jobs: Build → Deploy VPS → Healthcheck.
4. Если Deploy упал по SSH — проверь ключ, `deploy` в docker-группе, firewall.

Локально перед пушем можно прогнать тесты:

```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test
```

---

## 12. Обновления и откат

### Автоматически

```bash
git add .
git commit -m "your message"
git push origin main
```

CD сам соберёт образ, зальёт на VPS и перезапустит контейнеры.

### Вручную на VPS

```bash
cd /opt/cliperry
git pull   # если клонировал через git
./scripts/deploy.sh
```

### Откат на старый образ

```bash
# тег = короткий sha коммита (12 символов), смотри GHCR / Actions log
CLIPERRY_IMAGE=ghcr.io/k0ddo/cliperry/cliperry-backend:OLDSHA \
  HEALTH_URL=http://127.0.0.1:8000 \
  ./scripts/deploy.sh
```

---

## 13. Бэкапы и логи

### Бэкап Postgres (раз в день через cron)

```bash
crontab -e
```

```cron
0 3 * * * cd /opt/cliperry && set -a && . ./.env && set +a && docker exec cliperry-postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > /opt/cliperry/backups/db-$(date +\%Y\%m\%d).sql.gz
```

Храни последние 7–14 дней, копируй бэкапы off-site.

### Логи

```bash
docker compose -f docker-compose.prod.yml logs -f --tail=200 backend
docker compose -f docker-compose.prod.yml logs -f --tail=200 worker
docker compose -f docker-compose.prod.yml logs -f --tail=100 beat bot
```

Ротация логов уже в compose (`json-file`, max-size/max-file).

### YouTube cookies (если бот-чек)

Положи cookies в volume `cookies_data` и укажи в `.env`:

```env
YTDLP_COOKIES_FILE=/app/cookies/cookies.txt
```

Или прокси: `YTDLP_PROXY=socks5://...`

---

## 14. Чеклист go-live

- [ ] DNS `api.…` указывает на VPS
- [ ] Docker + docker compose работают под `deploy`
- [ ] `.env` заполнен, нет `CHANGE_ME` / `*` в `TRUSTED_HOSTS`
- [ ] Caddy отдаёт HTTPS, `curl https://api…/ready` → 200
- [ ] `docker compose -f docker-compose.prod.yml ps` — все healthy
- [ ] Admin открывается, логин работает
- [ ] Analyze YouTube URL через API/бота работает
- [ ] Download → ссылка `/api/files/…` открывает файл
- [ ] GitHub Secrets заполнены
- [ ] Environment `production` создан
- [ ] Test deploy через **Run workflow** успешен
- [ ] (опц.) Bot запущен, `/start` отвечает
- [ ] (опц.) Cron бэкапа БД

---

## 15. Типичные проблемы

| Симптом | Что проверить |
|---|---|
| CD: Permission denied (SSH) | ключ в Secrets, user `deploy`, `authorized_keys` |
| CD: docker permission | `deploy` в группе `docker`, re-login |
| `/ready` 503 | postgres/redis unhealthy; `docker compose ps` / logs |
| YouTube «unavailable» / bot check | cookies / proxy на VPS IP |
| Admin 400 / Host | `TRUSTED_HOSTS` = точный hostname |
| Extension CORS | `CORS_EXTENSION_IDS` = id расширения |
| Нет файла после download | worker logs; `temp_data` volume; size limit 2 GiB |
| Бот не стартует | `TELEGRAM_BOT_TOKEN`, `--profile bot` / `ENABLE_BOT=true` |
| Порт 8000 снаружи | так и должно; ходи через 443 Caddy |

---

## Быстрый TL;DR

```bash
# На VPS
sudo apt install docker… && usermod -aG docker deploy
mkdir -p /opt/cliperry && cd /opt/cliperry
git clone https://github.com/K0DDO/Cliperry.git .
cp .env.production.example .env && nano .env   # секреты!
# Caddy → reverse_proxy 127.0.0.1:8000
./scripts/deploy.sh
curl https://api.yourdomain.com/ready

# GitHub Secrets: VPS_HOST, VPS_USER, VPS_SSH_PRIVATE_KEY, DEPLOY_PATH, HEALTHCHECK_URL
# Environment: production
# Дальше: git push main → автодеплой
```

Локальная разработка (не prod):

```bash
cp .env.example .env
docker compose up --build
# API: http://localhost:8000
```
