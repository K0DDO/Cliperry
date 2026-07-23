"""Per-user preference settings."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Settings(Base, UUIDPrimaryKeyMixin):
    """Default download preferences for a user."""

    __tablename__ = "settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    default_quality: Mapped[str] = mapped_column(
        String(32),
        default="1080p",
        nullable=False,
    )
    default_format: Mapped[str] = mapped_column(
        String(16),
        default="mp4",
        nullable=False,
    )
    audio_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return (
            f"<Settings user_id={self.user_id} "
            f"quality={self.default_quality} format={self.default_format}>"
        )
