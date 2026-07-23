"""History / download list schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    """One download history row."""

    id: UUID
    title: str | None = None
    platform: str
    status: str
    quality: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    """Paginated download history."""

    items: list[HistoryItem] = Field(default_factory=list)
    page: int = 1
    page_size: int = 10
    total: int = 0
    total_pages: int = 0
    has_prev: bool = False
    has_next: bool = False
