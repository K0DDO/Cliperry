"""Admin panel data access."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.schemas import (
    AdminTaskItem,
    AdminTaskListResponse,
    AdminUserItem,
    AdminUserListResponse,
    DashboardResponse,
    DashboardStats,
    RecentError,
)
from app.models.download import Download, DownloadStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.device import Device


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def dashboard(self) -> DashboardResponse:
        users_total = await self._count(User)
        users_active = await self._count(User, User.is_active.is_(True))
        users_blocked = await self._count(User, User.is_active.is_(False))

        downloads_total = await self._count(Download)
        downloads_completed = await self._count(
            Download, Download.status == DownloadStatus.COMPLETED
        )
        downloads_failed = await self._count(
            Download, Download.status == DownloadStatus.FAILED
        )

        tasks_queued = await self._count(Task, Task.status == TaskStatus.QUEUED)
        tasks_processing = await self._count(Task, Task.status == TaskStatus.PROCESSING)
        errors_total = await self._count(Task, Task.status == TaskStatus.FAILED)

        recent_rows = (
            await self.session.execute(
                select(Task)
                .where(Task.status == TaskStatus.FAILED)
                .options(selectinload(Task.download))
                .order_by(Task.created_at.desc())
                .limit(8)
            )
        ).scalars().all()

        recent_errors = [
            RecentError(
                task_id=row.id,
                title=row.download.title if row.download else None,
                platform=row.download.platform if row.download else None,
                error_message=row.error_message,
                created_at=row.created_at,
            )
            for row in recent_rows
        ]

        return DashboardResponse(
            stats=DashboardStats(
                users_total=users_total,
                users_active=users_active,
                users_blocked=users_blocked,
                downloads_total=downloads_total,
                downloads_completed=downloads_completed,
                downloads_failed=downloads_failed,
                tasks_active=tasks_queued + tasks_processing,
                tasks_queued=tasks_queued,
                tasks_processing=tasks_processing,
                errors_total=errors_total,
            ),
            recent_errors=recent_errors,
        )

    async def list_users(self, *, page: int = 1, page_size: int = 20) -> AdminUserListResponse:
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        total = await self._count(User)
        offset = (page - 1) * page_size

        users = (
            await self.session.execute(
                select(
                    User,
                    func.count(Device.id.distinct()).label("devices_count"),
                    func.count(Download.id.distinct()).label("downloads_count"),
                )
                .outerjoin(Device, Device.user_id == User.id)
                .outerjoin(Download, Download.user_id == User.id)
                .group_by(User.id)
                .order_by(User.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        ).all()

        items: list[AdminUserItem] = []
        for user, devices_count, downloads_count in users:
            items.append(
                AdminUserItem(
                    id=user.id,
                    telegram_id=user.telegram_id,
                    is_active=user.is_active,
                    created_at=user.created_at,
                    devices_count=int(devices_count or 0),
                    downloads_count=int(downloads_count or 0),
                )
            )

        return AdminUserListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def set_user_blocked(self, user_id: uuid.UUID, *, blocked: bool) -> AdminUserItem:
        user = await self.session.get(User, user_id)
        if user is None:
            raise LookupError("User not found")
        user.is_active = not blocked
        await self.session.flush()

        devices_count = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(Device).where(Device.user_id == user.id)
                )
            ).scalar_one()
        )
        downloads_count = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(Download).where(Download.user_id == user.id)
                )
            ).scalar_one()
        )
        return AdminUserItem(
            id=user.id,
            telegram_id=user.telegram_id,
            is_active=user.is_active,
            created_at=user.created_at,
            devices_count=devices_count,
            downloads_count=downloads_count,
        )

    async def list_tasks(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
    ) -> AdminTaskListResponse:
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        stmt = select(Task).options(selectinload(Task.download))
        count_stmt = select(func.count()).select_from(Task)

        if status_filter:
            try:
                status_enum = TaskStatus(status_filter)
            except ValueError as exc:
                raise ValueError(f"Unknown status: {status_filter}") from exc
            stmt = stmt.where(Task.status == status_enum)
            count_stmt = count_stmt.where(Task.status == status_enum)

        total = int((await self.session.execute(count_stmt)).scalar_one())
        rows = (
            await self.session.execute(
                stmt.order_by(Task.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()

        items = [
            AdminTaskItem(
                id=row.id,
                status=row.status.value,
                progress=row.progress,
                speed=row.speed,
                eta=row.eta,
                error_message=row.error_message,
                celery_task_id=row.celery_task_id,
                created_at=row.created_at,
                download_id=row.download_id,
                title=row.download.title if row.download else None,
                platform=row.download.platform if row.download else None,
                quality=row.download.quality if row.download else None,
                url=row.download.url if row.download else None,
            )
            for row in rows
        ]

        return AdminTaskListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
        )

    async def _count(self, model, *filters) -> int:  # noqa: ANN001
        stmt = select(func.count()).select_from(model)
        for condition in filters:
            stmt = stmt.where(condition)
        return int((await self.session.execute(stmt)).scalar_one())
