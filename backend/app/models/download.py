"""Download history model."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.task import Task
    from app.models.user import User


class DownloadStatus(str, enum.Enum):
    """Lifecycle status of a download request."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Download(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """A single download request recorded for history and analytics."""

    __tablename__ = "downloads"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    quality: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[DownloadStatus] = mapped_column(
        Enum(
            DownloadStatus,
            name="download_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=DownloadStatus.QUEUED,
        nullable=False,
        index=True,
    )

    user: Mapped[User | None] = relationship("User", back_populates="downloads")
    device: Mapped[Device] = relationship("Device", back_populates="downloads")
    task: Mapped[Task | None] = relationship(
        "Task",
        back_populates="download",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Download id={self.id} platform={self.platform} status={self.status.value}>"
