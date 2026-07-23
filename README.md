# Cliperry

Universal video downloader — **Telegram bot** + **Chrome extension**, powered by FastAPI.

**Soft-launch:** YouTube / Shorts, TikTok, Instagram. X — later.

## Stack

FastAPI · PostgreSQL · Redis · Celery (+ Beat) · yt-dlp · aiogram 3 · MV3 extension · Docker

```
Telegram / Extension ──► FastAPI ──► PostgreSQL
                           │
                           ├── Redis (rate limit, pub/sub, Celery)
                           └── Celery worker (download) + Beat (cleanup)
```

## Quick start (local)

```bash
cp .env.example .env
docker compose up --build
```

| Service | Port | Role |
|---|---|---|
| backend | 8000 | API + admin `/admin` |
| worker | — | downloads |
| beat | — | temp cleanup |
| postgres | 5433 | DB (host) |
| redis | 6379 | broker / cache |
| bot | — | optional (`--profile bot`) |

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
# docs: http://localhost:8000/docs
```

## Production / VPS / auto-deploy

**Полный гайд:** [DEPLOY.md](./DEPLOY.md)

Кратко:

1. Пользователь `deploy` + Docker group, каталог `/opt/cliperry`
2. `.env.production` из `.env.production.example` (только на сервере)
3. Caddy/nginx TLS → `127.0.0.1:8001` (`BACKEND_HOST_PORT`)
4. Secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
5. Push `main` или **Actions → Deploy → Run workflow** → SSH → `scripts/vps-deploy.sh`

CI обновляет **только** Cliperry; другие сервисы на VPS не трогает.

## API (основное)

- `POST /api/analyze` — метаданные + качества  
- `POST /api/download` — очередь Celery  
- `GET /api/tasks/{id}` — прогресс  
- `GET /api/files/{id}?token=…` — скачивание (HMAC, TTL)  
- `WS /ws/tasks/{id}?device_id=…` — live progress  
- `GET /api/history` — история устройства  

Клиент шлёт `X-Device-Id` (UUID). Без него API создаст новый и вернёт в заголовке.

## Admin

`http://localhost:8000/admin` — логин из `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

## Tests

```bash
# unit in Docker
docker compose -f docker-compose.test.yml run --rm --no-deps test pytest -q -m unit

# full suite
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test
```

## Layout

```
cliperry/
├── backend/                 # FastAPI + Celery + bot
├── extension/               # Chrome MV3
├── docker-compose.yml       # local
├── docker-compose.prod.yml  # production
├── docker-compose.test.yml  # CI tests
├── scripts/vps-deploy.sh    # safe prod deploy (shared VPS)
├── .github/workflows/deploy.yml
├── DEPLOY.md                # ← полный гайд деплоя
└── .env.production.example
```

## License / notes

Файлы хранятся временно (`TEMP_FILE_TTL_SECONDS`, Beat cleanup). Не используй для пиратства — только контент, на который есть права.
