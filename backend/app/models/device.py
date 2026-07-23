"""Device model — anonymous client identity (extension / bot / API)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.download import Download
    from app.models.user import User


class Device(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """
    Client device identified by a stable ``device_id`` (UUID string).

    ``user_id`` is nullable so a device can exist before account linking.
    """

    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user: Mapped[User | None] = relationship("User", back_populates="devices")
    downloads: Mapped[list[Download]] = relationship(
        "Download",
        back_populates="device",
    )

    def __repr__(self) -> str:
        return f"<Device id={self.id} device_id={self.device_id}>"
