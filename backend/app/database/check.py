"""CLI utility: verify PostgreSQL connectivity and list tables."""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from app.config import get_settings
from app.database.session import check_database_connection, dispose_engine, get_engine


async def main() -> int:
    settings = get_settings()
    print(f"DATABASE_URL = {settings.database_url}")

    ok = await check_database_connection()
    if not ok:
        print("FAILED: cannot connect to PostgreSQL")
        await dispose_engine()
        return 1

    print("OK: PostgreSQL connection successful")

    async with get_engine().connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )
        )
        tables = [row[0] for row in result.fetchall()]

    if tables:
        print("Tables:")
        for name in tables:
            print(f"  - {name}")
    else:
        print("No tables yet — run: alembic upgrade head")

    await dispose_engine()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
