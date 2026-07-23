"""Synchronous SQLAlchemy engine/session for Celery workers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_sync_engine():
    """Return (and lazily create) the sync engine."""
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    settings = get_settings()
    _engine = create_engine(
        settings.database_url_sync,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return _engine


def get_sync_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        get_sync_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def sync_session() -> Generator[Session, None, None]:
    """Yield a sync DB session with commit/rollback."""
    factory = get_sync_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
