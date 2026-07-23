"""ORM models package — import all models for Alembic metadata discovery."""

from app.models.device import Device
from app.models.download import Download, DownloadStatus
from app.models.settings import Settings
from app.models.task import Task, TaskStatus
from app.models.user import User

__all__ = [
    "User",
    "Device",
    "Download",
    "DownloadStatus",
    "Task",
    "TaskStatus",
    "Settings",
]
