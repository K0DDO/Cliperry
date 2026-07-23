"""Health and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.database.redis import redis_ping
from app.database.session import get_engine

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Liveness payload — process is running."""

    status: str = Field(default="ok", examples=["ok"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
)
async def health() -> HealthResponse:
    """
    Return process liveness.

    Used by Docker / orchestrators. Does not check dependencies —
    use ``GET /ready`` for that.
    """
    return HealthResponse(status="ok")


@router.get("/ready", summary="Readiness probe")
async def ready() -> JSONResponse:
    """Return readiness — PostgreSQL and Redis must be reachable."""
    checks: dict[str, bool] = {"postgres": False, "redis": False}

    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = True
    except Exception:
        checks["postgres"] = False

    checks["redis"] = await redis_ping()

    ok = all(checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ready" if ok else "not_ready", "checks": checks},
    )
