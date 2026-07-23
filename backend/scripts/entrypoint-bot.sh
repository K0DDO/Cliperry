#!/bin/sh
set -e

echo "Waiting for backend..."
python - <<'PY'
import os
import sys
import time
import urllib.request

url = os.environ.get("BACKEND_PUBLIC_URL", "http://backend:8000").rstrip("/") + "/health"

for attempt in range(60):
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            if resp.status == 200:
                print("Backend is ready")
                sys.exit(0)
    except Exception as exc:
        print(f"Backend not ready ({attempt + 1}/60): {exc}")
        time.sleep(1)

print("Backend connection timed out", file=sys.stderr)
sys.exit(1)
PY

echo "Starting Telegram bot: $*"
exec "$@"
