"""User account model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.download import Download
    from app.models.settings import Settings


class User(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """
    Application user.

    Anonymous users have ``telegram_id=None``.
    Telegram linking (Phase 3) sets ``telegram_id``.
    """

    __tablename__ = "users"

    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger,
        unique=True,
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    devices: Mapped[list[Device]] = relationship(
        "Device",
        back_populates="user",
    )
    downloads: Mapped[list[Download]] = relationship(
        "Download",
        back_populates="user",
    )
    settings: Mapped[Settings | None] = relationship(
        "Settings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} active={self.is_active}>"
