# Testing

## Quick unit tests (local)

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest -m unit -q
```

## Full suite in Docker (unit + integration)

Starts Postgres, Redis, Celery worker, and a test runner:

```bash
cd cliperry
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test
docker compose -f docker-compose.test.yml down -v
```

## Markers

| Marker | Meaning |
|--------|---------|
| `unit` | Isolated mocks, no external services |
| `integration` | Needs Postgres / Redis / worker |
| `parsers` / `services` / `api` | Layer filters |

Examples:

```bash
pytest -m unit
pytest -m "unit and parsers"
pytest -m integration
```

## Layout

```
tests/
├── conftest.py
├── unit/
│   ├── parsers/
│   ├── services/
│   └── api/
├── integration/
│   ├── test_database.py
│   └── test_queue.py
└── test_*.py          # legacy / extra coverage
```
