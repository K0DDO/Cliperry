"""Anonymous device identity resolution."""

from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.device import Device
from app.models.settings import Settings
from app.models.user import User

DEVICE_HEADER = "X-Device-Id"


def _parse_device_id(raw: str | None) -> str:
    """Validate or generate a device UUID string."""
    if raw:
        try:
            return str(uuid.UUID(raw.strip()))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Device-Id must be a valid UUID",
            ) from exc
    return str(uuid.uuid4())


async def get_or_create_device(
    request: Request,
    session: AsyncSession = Depends(get_db),
    x_device_id: str | None = Header(default=None, alias=DEVICE_HEADER),
) -> Device:
    """
    Resolve the current Device from ``X-Device-Id``.

    Creates an anonymous User + Settings + Device when the id is new.
    """
    device_key = _parse_device_id(x_device_id)

    result = await session.execute(
        select(Device)
        .where(Device.device_id == device_key)
        .options(selectinload(Device.user))
    )
    device = result.scalar_one_or_none()

    if device is not None:
        if device.user is not None and not device.user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive",
            )
        request.state.device_id = device.device_id
        return device

    user = User(is_active=True)
    session.add(user)
    await session.flush()

    settings = Settings(user_id=user.id)
    session.add(settings)

    device = Device(device_id=device_key, user_id=user.id)
    session.add(device)

    # Persist identity even if the route later returns 4xx
    await session.commit()
    await session.refresh(device)

    request.state.device_id = device.device_id
    request.state.new_device = True
    return device
