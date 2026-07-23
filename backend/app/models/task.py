"""Download task / queue model."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.download import Download


class TaskStatus(str, enum.Enum):
    """Queue status for a download job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Queued download job with live progress metadata."""

    __tablename__ = "tasks"

    download_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("downloads.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(
            TaskStatus,
            name="task_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=TaskStatus.QUEUED,
        nullable=False,
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    speed: Mapped[str | None] = mapped_column(String(64), nullable=True)
    eta: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_token: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    download: Mapped[Download] = relationship("Download", back_populates="task")

    def __repr__(self) -> str:
        return f"<Task id={self.id} status={self.status.value} progress={self.progress}>"
