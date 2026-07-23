"""Admin panel response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    users_total: int = 0
    users_active: int = 0
    users_blocked: int = 0
    downloads_total: int = 0
    downloads_completed: int = 0
    downloads_failed: int = 0
    tasks_active: int = 0
    tasks_queued: int = 0
    tasks_processing: int = 0
    errors_total: int = 0


class RecentError(BaseModel):
    task_id: UUID
    title: str | None = None
    platform: str | None = None
    error_message: str | None = None
    created_at: datetime


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_errors: list[RecentError] = Field(default_factory=list)


class AdminUserItem(BaseModel):
    id: UUID
    telegram_id: int | None = None
    is_active: bool
    created_at: datetime
    devices_count: int = 0
    downloads_count: int = 0


class AdminUserListResponse(BaseModel):
    items: list[AdminUserItem]
    total: int
    page: int
    page_size: int


class AdminTaskItem(BaseModel):
    id: UUID
    status: str
    progress: int
    speed: str | None = None
    eta: str | None = None
    error_message: str | None = None
    celery_task_id: str | None = None
    created_at: datetime
    download_id: UUID
    title: str | None = None
    platform: str | None = None
    quality: str | None = None
    url: str | None = None


class AdminTaskListResponse(BaseModel):
    items: list[AdminTaskItem]
    total: int
    page: int
    page_size: int
    status_filter: str | None = None
