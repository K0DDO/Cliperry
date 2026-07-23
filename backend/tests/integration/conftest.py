"""Integration fixtures — Postgres + Redis from Docker test env."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.base import Base
from app.models import Device, Download, Settings, Task, User  # noqa: F401


def _database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://cliperry:cliperry@localhost:5434/cliperry",
    )


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6380/0")


def _celery_broker() -> str:
    return os.getenv("CELERY_BROKER_URL", "redis://localhost:6380/1")


def _celery_backend() -> str:
    return os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6380/2")


async def _db_available(url: str) -> bool:
    try:
        engine = create_async_engine(url, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def integration_env() -> dict[str, str]:
    return {
        "DATABASE_URL": _database_url(),
        "REDIS_URL": _redis_url(),
        "CELERY_BROKER_URL": _celery_broker(),
        "CELERY_RESULT_BACKEND": _celery_backend(),
        "APP_ENV": "test",
        "SECRET_KEY": "integration-test-secret-key-32chars!",
        "ADMIN_PASSWORD": "integration-admin-password",
    }


@pytest_asyncio.fixture
async def db_engine(integration_env: dict[str, str]) -> AsyncIterator[AsyncEngine]:
    url = integration_env["DATABASE_URL"]
    if not await _db_available(url):
        pytest.skip("Postgres is not available — start docker compose test env")

    engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seeded_device(db_session: AsyncSession) -> Device:
    user = User(is_active=True)
    db_session.add(user)
    await db_session.flush()

    settings = Settings(user_id=user.id)
    db_session.add(settings)

    device = Device(device_id=str(uuid.uuid4()), user_id=user.id)
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device
