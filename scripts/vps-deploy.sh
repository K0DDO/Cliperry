#!/usr/bin/env bash
# Safe production deploy for Cliperry on a shared VPS.
# MUST run only under /opt/cliperry as user `deploy`.
# Never touches other projects (briefly, moex-bot, Amnezia, etc.).
set -euo pipefail

DEPLOY_ROOT="/opt/cliperry"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
APP_SERVICES=(backend worker beat)
# Optional bot — enable with ENABLE_BOT=true
if [[ "${ENABLE_BOT:-false}" == "true" ]]; then
  APP_SERVICES+=(bot)
  COMPOSE_PROFILES=(--profile bot)
else
  COMPOSE_PROFILES=()
fi

log() { echo "==> $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

# --- Safety: cwd and identity ---
[[ "$(pwd -P)" == "$DEPLOY_ROOT" ]] || die "Refusing to run outside $DEPLOY_ROOT (cwd=$(pwd -P))"
[[ -d "$DEPLOY_ROOT" ]] || die "Missing $DEPLOY_ROOT"
cd "$DEPLOY_ROOT"

log "whoami=$(whoami) pwd=$(pwd)"
[[ "$(whoami)" != "root" ]] || log "WARNING: running as root — prefer user deploy"

# --- Required files ---
[[ -f "$COMPOSE_FILE" ]] || die "Missing $COMPOSE_FILE"
[[ -f backend/Dockerfile ]] || die "Missing backend/Dockerfile"
[[ -f "$ENV_FILE" ]] || die "Missing $ENV_FILE (server-only; never commit)"

# Load DB credentials for backup without printing them
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
: "${POSTGRES_USER:?POSTGRES_USER missing in $ENV_FILE}"
: "${POSTGRES_DB:?POSTGRES_DB missing in $ENV_FILE}"

compose() {
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "${COMPOSE_PROFILES[@]}" "$@"
}

# --- Validate compose ---
log "Validating docker compose config"
if ! compose config -q; then
  die "docker compose config failed"
fi

# --- Git update (never touch .env.production) ---
log "Updating code from origin/main"
[[ -d .git ]] || die "Not a git repository — clone Cliperry into $DEPLOY_ROOT first"
git fetch origin
git checkout main
# Keep local .env.production if somehow tracked (it should not be)
git pull origin main

# Ensure secrets file still present after pull
[[ -f "$ENV_FILE" ]] || die "$ENV_FILE disappeared after git pull"

# --- Backup PostgreSQL ---
log "Backing up PostgreSQL (cliperry only)"
mkdir -p backups
BACKUP_FILE="backups/predeploy_$(date +%F_%H-%M).sql"
if ! docker exec cliperry-postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" >"$BACKUP_FILE"; then
  rm -f "$BACKUP_FILE"
  die "PostgreSQL backup failed — deploy aborted"
fi
[[ -s "$BACKUP_FILE" ]] || die "Backup file empty — deploy aborted"
gzip -f "$BACKUP_FILE"
log "Backup OK: ${BACKUP_FILE}.gz"

# Tag current app image for rollback (best-effort)
PREV_TAG="cliperry-backend:previous"
if docker image inspect cliperry-backend:latest >/dev/null 2>&1; then
  docker tag cliperry-backend:latest "$PREV_TAG" || true
  log "Tagged current image as $PREV_TAG"
fi

rollback() {
  echo "ERROR: Deploy failed — attempting rollback to previous app image" >&2
  if docker image inspect "$PREV_TAG" >/dev/null 2>&1; then
    docker tag "$PREV_TAG" cliperry-backend:latest || true
    compose up -d --no-deps "${APP_SERVICES[@]}" || true
    echo "Rollback: restarted app services from $PREV_TAG" >&2
  else
    echo "Rollback: no previous image available" >&2
  fi
}

trap 'rollback' ERR

# --- Migrations (app container only; no down/prune) ---
log "Running Alembic migrations"
compose run --rm --no-deps --entrypoint alembic backend upgrade head

# --- Rebuild ONLY application services (not postgres/redis) ---
log "Building app services: ${APP_SERVICES[*]}"
compose build "${APP_SERVICES[@]}"

log "Starting app services (no compose down)"
compose up -d --no-deps "${APP_SERVICES[@]}"

# Ensure data services are up (never recreate volumes)
log "Ensuring postgres/redis are running"
compose up -d --no-deps postgres redis

# --- Health checks (max ~60s) ---
log "Waiting for health (up to 60s)"
deadline=$((SECONDS + 60))
postgres_ok=0
redis_ok=0
backend_ok=0

while (( SECONDS < deadline )); do
  pg_status="$(docker inspect cliperry-postgres --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' 2>/dev/null || echo missing)"
  rd_status="$(docker inspect cliperry-redis --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' 2>/dev/null || echo missing)"
  be_status="$(docker inspect cliperry-backend --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' 2>/dev/null || echo missing)"

  [[ "$pg_status" == "healthy" ]] && postgres_ok=1
  [[ "$rd_status" == "healthy" ]] && redis_ok=1
  # backend healthcheck hits /ready
  if [[ "$be_status" == "healthy" ]] || curl -fsS http://127.0.0.1:8000/ready >/dev/null 2>&1; then
    backend_ok=1
  fi

  if (( postgres_ok && redis_ok && backend_ok )); then
    break
  fi
  sleep 3
done

log "Service status"
compose ps || true

if (( !postgres_ok || !redis_ok || !backend_ok )); then
  echo "ERROR: Health check failed (postgres=$postgres_ok redis=$redis_ok backend=$backend_ok)" >&2
  compose logs --tail=100 backend || true
  compose logs --tail=100 worker || true
  compose logs --tail=100 postgres || true
  compose logs --tail=100 redis || true
  exit 1
fi

trap - ERR
log "Deploy OK — Cliperry only (other VPS services untouched)"
