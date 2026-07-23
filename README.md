# Cliperry

Modern universal video downloader — Telegram Bot + Chrome Extension, powered by a FastAPI backend.

> Phase 1 complete: backend foundation (API, PostgreSQL, Redis, Docker).  
> Parsers, Celery downloads, Bot, Extension, and Admin arrive in later phases.

## Architecture

```
Telegram Bot ──┐
               ├──► FastAPI ──► PostgreSQL
Chrome Ext  ───┘       │
                       ├──► Redis (rate limit / Celery broker)
                       └──► Celery workers (Phase 2)
```

Clients never parse platforms themselves. The backend validates URLs, resolves a parser via `ParserRegistry`, queues downloads, and issues temporary signed download URLs.

## Project layout

```
cliperry/
├── backend/          # FastAPI app
├── extension/        # Chrome MV3 (Phase 4)
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick start (Phase 1)

### Prerequisites

- Docker + Docker Compose
- Python 3.12+ (optional, for local non-Docker runs)

### 1. Configure environment

```bash
cp .env.example .env
```

### 2. Start foundation services

```bash
docker compose up --build
```

This starts:

| Service    | Port | Notes                          |
|------------|------|--------------------------------|
| backend    | 8000 | FastAPI + auto-migrate         |
| postgres   | 5432 | Primary database               |
| redis      | 6379 | Rate limiting / future Celery  |

Optional profiles (not needed in Phase 1):

```bash
docker compose --profile workers up   # Celery worker stub
docker compose --profile bot up       # Bot placeholder
```

### 3. Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Open interactive docs: http://localhost:8000/docs

## API (Phase 1)

### `POST /api/analyze`

```json
{ "url": "https://www.youtube.com/watch?v=..." }
```

Validates the URL and looks up a parser. With an empty registry (Phase 1) returns **422** `unsupported_platform`. Adult domains are rejected with **403**.

### `POST /api/download`

```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "quality": "1080p",
  "format": "mp4"
}
```

Creates `Download` + `Task` rows with status `queued`. Returns:

```json
{
  "task_id": "...",
  "status": "queued",
  "download_id": "..."
}
```

### `GET /api/tasks/{id}`

Returns progress for a task owned by the calling device.

### Identity

Send optional header `X-Device-Id: <uuid>`. If omitted, the API creates an anonymous device and echoes the id in the response header. Persist it on the client.

## Telegram Bot

```bash
# in .env
TELEGRAM_BOT_TOKEN=123:ABC
BACKEND_PUBLIC_URL=http://backend:8000

docker compose up --build bot
# or locally:
cd backend && python -m app.bot
```

Commands: `/start` `/help` `/history` `/settings`  
Main flow: send a video URL → preview + quality buttons → download progress.


```bash
# enqueue
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -H "X-Device-Id: <uuid>" \
  -d '{"url":"https://www.youtube.com/watch?v=...","quality":"720p"}'

# poll progress
curl http://localhost:8000/api/tasks/<task_id> -H "X-Device-Id: <uuid>"

# realtime (WebSocket)
# ws://localhost:8000/ws/tasks/<task_id>?device_id=<uuid>
```

Worker must listen on the `downloads` queue (already configured in docker-compose).


Background jobs use Redis as broker/result backend.

```bash
docker compose up --build
# services: postgres, redis, backend, worker
```

Smoke-test from API:

```bash
curl -X POST "http://localhost:8000/api/worker/test"
# {"task_id":"...","status":"SUCCESS","result":"Cliperry worker works"}
```

Or from the backend container:

```bash
docker compose exec backend python -m app.workers.run_test
```

Queues: `cliperry` (default / smoke tests), `downloads` (future yt-dlp jobs).


SQLAlchemy 2.0 async + Alembic.

```bash
cd backend
# ensure DATABASE_URL points at PostgreSQL
alembic upgrade head
python -m app.database.check
```

Expected check output: `OK: PostgreSQL connection successful` and tables
`users`, `devices`, `settings`, `downloads`, `tasks`.


```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt

# Ensure Postgres + Redis are running (e.g. docker compose up postgres redis)
export DATABASE_URL=postgresql+asyncpg://cliperry:cliperry@localhost:5432/cliperry
export DATABASE_URL_SYNC=postgresql+psycopg2://cliperry:cliperry@localhost:5432/cliperry
export REDIS_URL=redis://localhost:6379/0

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Roadmap

| Phase | Scope |
|-------|--------|
| **1** | FastAPI, models, Alembic, API stubs, Docker, security |
| **2** | yt-dlp parsers (YouTube, TikTok, Instagram, Twitter/X), Celery, temp signed URLs |
| **3** | Telegram bot (aiogram 3), playlists, progress |
| **4** | Chrome Extension MV3 + Cliperry design system |
| **5** | Admin dashboard `/admin` |

## Security notes

- Secrets only via environment / `.env` (never commit real values)
- URL validation + adult domain blocklist
- Redis rate limiting on analyze / download
- Request logging with `X-Request-Id`
- CORS limited to configured origins + `chrome-extension://`

## License

Proprietary — Cliperry.
