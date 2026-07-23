#!/bin/sh
# Celery worker liveness for Docker HEALTHCHECK.
set -e
celery -A app.workers.celery_app.celery_app inspect ping -d "celery@$HOSTNAME" --timeout 5 >/dev/null 2>&1 \
  || celery -A app.workers.celery_app.celery_app inspect ping --timeout 5 >/dev/null 2>&1
