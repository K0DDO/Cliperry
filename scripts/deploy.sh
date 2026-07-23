#!/usr/bin/env bash
# Deploy Cliperry on the VPS (used by GitHub Actions CD and manual updates).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
REQUESTED_IMAGE="${CLIPERRY_IMAGE:-}"
ENABLE_BOT="${ENABLE_BOT:-false}"
HEALTH_URL="${HEALTH_URL:-}"
HEALTH_RETRIES="${HEALTH_RETRIES:-30}"
HEALTH_SLEEP="${HEALTH_SLEEP:-5}"

if [[ ! -f .env ]]; then
  echo "ERROR: .env not found in $ROOT_DIR" >&2
  echo "Copy .env.production.example to .env and fill secrets." >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
# shellcheck source=/dev/null
source .env
set +a

if [[ -n "$REQUESTED_IMAGE" ]]; then
  CLIPERRY_IMAGE="$REQUESTED_IMAGE"
fi
export CLIPERRY_IMAGE="${CLIPERRY_IMAGE:-cliperry-backend:latest}"

if [[ -n "$REQUESTED_IMAGE" ]]; then
  if grep -q '^CLIPERRY_IMAGE=' .env; then
    sed -i.bak "s|^CLIPERRY_IMAGE=.*|CLIPERRY_IMAGE=${CLIPERRY_IMAGE}|" .env
    rm -f .env.bak
  else
    echo "CLIPERRY_IMAGE=${CLIPERRY_IMAGE}" >> .env
  fi
fi

PROFILE_ARGS=()
if [[ "$ENABLE_BOT" == "true" || -n "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  PROFILE_ARGS+=(--profile bot)
fi

echo "==> Pulling images (if remote registry)..."
docker compose -f "$COMPOSE_FILE" "${PROFILE_ARGS[@]}" pull || true

echo "==> Starting stack..."
if [[ -n "${CLIPERRY_IMAGE:-}" && "$CLIPERRY_IMAGE" != cliperry-backend:latest ]]; then
  docker compose -f "$COMPOSE_FILE" "${PROFILE_ARGS[@]}" up -d --pull always --remove-orphans
else
  docker compose -f "$COMPOSE_FILE" "${PROFILE_ARGS[@]}" up -d --build --remove-orphans
fi

echo "==> Waiting for containers..."
sleep 5
docker compose -f "$COMPOSE_FILE" "${PROFILE_ARGS[@]}" ps

if [[ -z "$HEALTH_URL" ]]; then
  HEALTH_URL="${BACKEND_PUBLIC_URL:-http://127.0.0.1:8000}"
fi
HEALTH_URL="${HEALTH_URL%/}"

echo "==> Healthcheck: ${HEALTH_URL}/ready"
for i in $(seq 1 "$HEALTH_RETRIES"); do
  if curl -fsS "${HEALTH_URL}/ready" >/tmp/cliperry-ready.json 2>/dev/null; then
    cat /tmp/cliperry-ready.json
    echo
    echo "Deploy OK"
    exit 0
  fi
  echo "Attempt $i/$HEALTH_RETRIES failed, retrying in ${HEALTH_SLEEP}s..."
  sleep "$HEALTH_SLEEP"
done

echo "ERROR: healthcheck failed after $HEALTH_RETRIES attempts" >&2
docker compose -f "$COMPOSE_FILE" "${PROFILE_ARGS[@]}" logs --tail=80 backend || true
exit 1
