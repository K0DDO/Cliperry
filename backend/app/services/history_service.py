"""Download history service."""

from __future__ import annotations

import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.download import Download
from app.schemas.history import HistoryItem, HistoryResponse


class HistoryService:
    """Paginated download history for a device."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_downloads(
        self,
        device: Device,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> HistoryResponse:
        page = max(1, page)
        page_size = max(1, min(page_size, 50))

        total = int(
            (
                await self.session.execute(
                    select(func.count())
                    .select_from(Download)
                    .where(Download.device_id == device.id)
                )
            ).scalar_one()
        )

        total_pages = max(1, math.ceil(total / page_size)) if total else 0
        if total_pages and page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size
        rows = (
            await self.session.execute(
                select(Download)
                .where(Download.device_id == device.id)
                .order_by(Download.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        ).scalars().all()

        items = [
            HistoryItem(
                id=row.id,
                title=row.title,
                platform=row.platform,
                status=row.status.value,
                quality=row.quality,
                created_at=row.created_at,
            )
            for row in rows
        ]

        return HistoryResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_prev=page > 1 and total > 0,
            has_next=bool(total_pages) and page < total_pages,
        )
