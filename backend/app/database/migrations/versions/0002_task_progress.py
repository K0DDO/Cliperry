"""Add progress fields to tasks.

Revision ID: 0002_task_progress
Revises: 0001_initial
Create Date: 2026-07-23
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_task_progress"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("speed", sa.String(length=64), nullable=True))
    op.add_column("tasks", sa.Column("eta", sa.String(length=64), nullable=True))
    op.add_column("tasks", sa.Column("celery_task_id", sa.String(length=255), nullable=True))
    op.add_column("tasks", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("tasks", sa.Column("download_url", sa.Text(), nullable=True))
    op.add_column("tasks", sa.Column("download_token", sa.String(length=128), nullable=True))
    op.add_column("tasks", sa.Column("file_path", sa.Text(), nullable=True))
    op.create_index("ix_tasks_celery_task_id", "tasks", ["celery_task_id"], unique=False)
    op.create_unique_constraint("uq_tasks_download_token", "tasks", ["download_token"])


def downgrade() -> None:
    op.drop_constraint("uq_tasks_download_token", "tasks", type_="unique")
    op.drop_index("ix_tasks_celery_task_id", table_name="tasks")
    op.drop_column("tasks", "file_path")
    op.drop_column("tasks", "download_token")
    op.drop_column("tasks", "download_url")
    op.drop_column("tasks", "error_message")
    op.drop_column("tasks", "celery_task_id")
    op.drop_column("tasks", "eta")
    op.drop_column("tasks", "speed")
