FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN chmod +x /app/scripts/entrypoint.sh \
    /app/scripts/entrypoint-worker.sh \
    /app/scripts/entrypoint-bot.sh \
    /app/scripts/run-tests.sh \
    /app/scripts/celery-health.sh \
    && mkdir -p /tmp/cliperry

FROM base AS runtime

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"]

FROM base AS test

COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
ENV APP_ENV=test \
    DEBUG=true \
    PYTHONPATH=/app
ENTRYPOINT []
CMD ["pytest", "-q"]
