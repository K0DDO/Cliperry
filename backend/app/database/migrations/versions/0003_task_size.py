"""Add size label to tasks for progress UI.

Revision ID: 0003_task_size
Revises: 0002_task_progress
Create Date: 2026-07-23
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_task_size"
down_revision: Union[str, None] = "0002_task_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("size", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "size")
