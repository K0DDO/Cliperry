"""Add composite index for download history queries.

Revision ID: 0004_download_device_created
Revises: 0003_task_size
Create Date: 2026-07-23
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_download_device_created"
down_revision: Union[str, None] = "0003_task_size"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_downloads_device_created",
        "downloads",
        ["device_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_downloads_device_created", table_name="downloads")
