#!/bin/sh
set -e

echo "Waiting for Redis (Celery broker)..."
python - <<'PY'
import os
import sys
import time

import redis

url = os.environ.get("CELERY_BROKER_URL") or os.environ.get("REDIS_URL", "redis://localhost:6379/0")

for attempt in range(60):
    try:
        client = redis.Redis.from_url(url)
        if client.ping():
            print("Redis is ready")
            sys.exit(0)
    except Exception as exc:
        print(f"Redis not ready ({attempt + 1}/60): {exc}")
        time.sleep(1)

print("Redis connection timed out", file=sys.stderr)
sys.exit(1)
PY

echo "Waiting for PostgreSQL..."
python - <<'PY'
import os
import sys
import time

import psycopg2

url = os.environ.get("DATABASE_URL_SYNC", "")
url = url.replace("postgresql+psycopg2://", "postgresql://")

for attempt in range(60):
    try:
        conn = psycopg2.connect(url)
        conn.close()
        print("PostgreSQL is ready")
        sys.exit(0)
    except Exception as exc:
        print(f"PostgreSQL not ready ({attempt + 1}/60): {exc}")
        time.sleep(1)

print("PostgreSQL connection timed out", file=sys.stderr)
sys.exit(1)
PY

echo "Starting Celery worker: $*"
exec "$@"
