"""Pydantic schemas for task progress endpoint."""

from uuid import UUID

from pydantic import BaseModel, Field


class TaskStatusResponse(BaseModel):
    """Progress snapshot for a download task."""

    task_id: UUID
    status: str = Field(description="queued | processing | completed | failed")
    progress: int = Field(ge=0, le=100)
    speed: str | None = None
    eta: str | None = None
    size: str | None = None
    error_message: str | None = None
    download_url: str | None = None
    title: str | None = None
    platform: str | None = None
    quality: str | None = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "task_id": "11111111-1111-1111-1111-111111111111",
                    "status": "processing",
                    "progress": 75,
                    "speed": "8.5MB/s",
                    "eta": "20s",
                    "size": "850MB / 1.2GB",
                }
            ]
        },
    }
