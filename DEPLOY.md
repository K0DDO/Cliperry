# Cliperry — production deploy (shared VPS)

Стек: FastAPI + Postgres + Redis + Celery (+ Beat) + опционально Telegram-бот.  
Платформа: **YouTube + TikTok + Instagram**.

Репозиторий: https://github.com/K0DDO/Cliperry

```text
GitHub Actions → SSH as deploy → /opt/cliperry only →
  git pull → pg_dump backup → alembic → build/up app → healthcheck
```

На одном VPS могут жить другие проекты (`/opt/briefly`, `/opt/moex-bot`, Amnezia VPN).  
**CI/CD трогает только Cliperry** в `/opt/cliperry` и никогда не выполняет `docker compose down` / `prune` / firewall / systemd чужих сервисов.

---

## Содержание

1. [Изоляция на shared VPS](#1-изоляция-на-shared-vps)
2. [Пользователь deploy](#2-пользователь-deploy)
3. [SSH-ключ и GitHub Secrets](#3-ssh-ключ-и-github-secrets)
4. [Первый запуск на сервере](#4-первый-запуск-на-сервере)
5. [Файл `.env.production`](#5-файл-envproduction)
6. [Reverse proxy (Caddy)](#6-reverse-proxy-caddy)
7. [GitHub Actions](#7-github-actions)
8. [Ручной деплой / откат](#8-ручной-деплой--откат)
9. [Проверки](#9-проверки)
10. [Что запрещено](#10-что-запрещено)

---

## 1. Изоляция на shared VPS

| Путь / сервис | Владелец CI |
|---|---|
| `/opt/cliperry` | **да** — только этот проект |
| `/opt/briefly` | нет |
| `/opt/moex-bot` | нет |
| Amnezia VPN контейнеры | нет |
| Другие Docker-сети / volumes | нет |

Workflow: `.github/workflows/deploy.yml`  
Скрипт на сервере: `scripts/vps-deploy.sh` (cwd жёстко `/opt/cliperry`).

---

## 2. Пользователь `deploy`

Один раз под `root` (или существующим админом):

### 2.1 Создать пользователя

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy
```

Пароль для `deploy` **не задаём** — только SSH-ключ.

### 2.2 Каталог проекта

```bash
mkdir -p /opt/cliperry /opt/cliperry/backups
chown -R deploy:deploy /opt/cliperry
```

### 2.3 SSH только по ключу

На **локальной** машине (откуда будешь класть ключ в GitHub):

```bash
ssh-keygen -t ed25519 -f cliperry_deploy -C "cliperry-github-actions" -N ""
```

Появятся:

- `cliperry_deploy` — **приватный** ключ → GitHub Secret `VPS_SSH_KEY`
- `cliperry_deploy.pub` — **публичный** → на сервер

На сервере:

```bash
mkdir -p /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
# вставь содержимое cliperry_deploy.pub одной строкой:
nano /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh
```

В `/etc/ssh/sshd_config` (или drop-in) желательно:

```text
PasswordAuthentication no
PubkeyAuthentication yes
```

Затем:

```bash
systemctl reload ssh
```

### 2.4 Проверка подключения

С локальной машины:

```bash
ssh -i cliperry_deploy deploy@107.172.44.182
whoami   # → deploy
id -nG   # → ... docker ...
cd /opt/cliperry && pwd
docker ps
```

Если `docker` без sudo работает и cwd `/opt/cliperry` — готово.

---

## 3. SSH-ключ и GitHub Secrets

В репозитории: **Settings → Secrets and variables → Actions**.

| Secret | Значение |
|---|---|
| `VPS_HOST` | `107.172.44.182` (или домен) |
| `VPS_USER` | `deploy` |
| `VPS_SSH_KEY` | весь приватный ключ `cliperry_deploy`, включая `-----BEGIN … KEY-----` / `-----END …-----` |

Опционально:

| Secret / Variable | Назначение |
|---|---|
| `VPS_HOST_KEY` | pinned host key (вместо `ssh-keyscan`) |
| Variable `HEALTHCHECK_URL` | публичный URL API, например `https://api.example.com` |
| Variable `ENABLE_BOT` | `true` чтобы при деплое поднимать профиль `bot` |

**Никогда:**

- не коммить приватный ключ;
- не печатать `VPS_SSH_KEY` / `.env.production` / токены в workflow;
- не класть `.env.production` в git.

Environment: workflow использует GitHub Environment `production` — создай его в Settings → Environments (можно без protection rules на старте).

---

## 4. Первый запуск на сервере

Под `deploy`:

```bash
cd /opt/cliperry
git clone https://github.com/K0DDO/Cliperry.git .
# если каталог не пустой:
# git clone https://github.com/K0DDO/Cliperry.git /tmp/cliperry && shopt -s dotglob && mv /tmp/cliperry/* /opt/cliperry/

cp .env.production.example .env.production
nano .env.production
```

Заполни секреты (см. ниже), затем **первый** подъём стека (postgres/redis один раз):

```bash
chmod +x scripts/vps-deploy.sh
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Дальше обновления — через Actions или `./scripts/vps-deploy.sh` (пересобирает только app-сервисы).

---

## 5. Файл `.env.production`

Файл **только на сервере**, не в Git.

```bash
cd /opt/cliperry
cp .env.production.example .env.production
nano .env.production
```

Сгенерируй секреты:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Обязательно

| Переменная | Комментарий |
|---|---|
| `SECRET_KEY` | ≥ 32 символов |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | БД |
| `ADMIN_PASSWORD` | ≥ 12 символов |
| `TRUSTED_HOSTS` | домен API **без** `*` |
| `TRUST_PROXY_HEADERS` | `true` за Caddy |
| `BACKEND_PUBLIC_URL` | `https://api.yourdomain.com` |
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `ENABLE_WORKER_TEST` | `false` |

`docker-compose.prod.yml` читает `env_file: .env.production`.  
Деплой **никогда не перезаписывает** этот файл.

---

## 6. Reverse proxy (Caddy)

Backend слушает только loopback. По умолчанию **`127.0.0.1:8001`** (`BACKEND_HOST_PORT`), чтобы не конфликтовать с Briefly на `:8000`. Наружу — 80/443 через Caddy (или nginx).

Пример `/etc/caddy/Caddyfile`:

```caddy
api.yourdomain.com {
    encode gzip
    reverse_proxy 127.0.0.1:8001 {
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
        header_up Host {host}
    }
}
```

```bash
sudo systemctl reload caddy
```

UFW (один раз, вручную админом — **не из Actions**):

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 7. GitHub Actions

Файл: `.github/workflows/deploy.yml`

Триггеры:

- `push` в `main`
- `workflow_dispatch` (Actions → Deploy → Run workflow)

Пайплайн:

1. Unit-тесты в Docker
2. SSH как `deploy@VPS_HOST`
3. `cd /opt/cliperry` + `./scripts/vps-deploy.sh`:
   - проверка `docker-compose.prod.yml`, `backend/Dockerfile`, `.env.production`
   - `docker compose config`
   - `git fetch` / `checkout main` / `pull`
   - backup: `pg_dump` → `backups/predeploy_*.sql.gz`
   - `alembic upgrade head`
   - `docker compose build` только `backend` (+ `worker` / `beat` / опционально `bot`)
   - `docker compose up -d --no-deps` только app-сервисов
   - health: postgres / redis / backend (~60 с)
   - при ошибке — rollback на тег `cliperry-backend:previous`

Postgres и Redis **не** пересобираются без нужды.  
`docker compose down` **не** вызывается.

---

## 8. Ручной деплой / откат

На сервере:

```bash
cd /opt/cliperry
./scripts/vps-deploy.sh
```

Откат образа (если тег previous есть):

```bash
docker tag cliperry-backend:previous cliperry-backend:latest
docker compose -f docker-compose.prod.yml --env-file .env.production \
  up -d --no-deps backend worker beat
```

Восстановление БД из бэкапа (только если нужно):

```bash
gunzip -c backups/predeploy_YYYY-MM-DD_HH-MM.sql.gz \
  | docker exec -i cliperry-postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

---

## 9. Проверки

```bash
whoami                    # deploy
pwd                       # /opt/cliperry
docker compose -f docker-compose.prod.yml --env-file .env.production ps
curl -fsS http://127.0.0.1:8001/ready
docker inspect cliperry-postgres --format='{{.State.Health.Status}}'  # healthy
docker inspect cliperry-redis --format='{{.State.Health.Status}}'     # healthy
```

Чужие сервисы должны остаться нетронутыми:

```bash
docker ps --format '{{.Names}}' | grep -E 'amnezia|briefly|moex' || true
```

---

## 10. Что запрещено

GitHub Actions / `vps-deploy.sh` **не должны**:

- останавливать весь Docker;
- делать `docker compose down` вне проекта;
- удалять volumes / `docker system prune`;
- менять firewall / iptables / сети хоста;
- заходить в `/opt/briefly`, `/opt/moex-bot`, Amnezia;
- перезапускать чужие systemd-юниты;
- выполнять команды вне `/opt/cliperry`;
- печатать `.env.production`, `BOT_TOKEN`, `VPS_SSH_KEY` и прочие секреты.

---

## Сервисы Cliperry

| Контейнер | Роль |
|---|---|
| `cliperry-postgres` | БД |
| `cliperry-redis` | брокер / rate limit |
| `cliperry-backend` | FastAPI |
| `cliperry-worker` | yt-dlp |
| `cliperry-beat` | cleanup |
| `cliperry-bot` | Telegram (`ENABLE_BOT=true` / profile `bot`) |
