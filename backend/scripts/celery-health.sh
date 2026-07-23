#!/bin/sh
# Celery worker liveness for Docker HEALTHCHECK.
set -e
python - <<'PY'
import os
import sys

from redis import Redis

url = os.environ.get("CELERY_BROKER_URL") or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
try:
    client = Redis.from_url(url, socket_connect_timeout=2)
    if not client.ping():
        raise RuntimeError("redis ping failed")
except Exception as exc:
    print(f"worker healthcheck failed: {exc}", file=sys.stderr)
    sys.exit(1)
print("ok")
PY
