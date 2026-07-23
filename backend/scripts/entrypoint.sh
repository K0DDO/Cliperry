#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python - <<'PY'
import os
import time
import sys

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

echo "Running migrations..."
alembic upgrade head

echo "Starting: $*"
exec "$@"
