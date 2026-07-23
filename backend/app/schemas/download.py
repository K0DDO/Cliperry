"""Pydantic schemas for download endpoint."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DownloadRequest(BaseModel):
    """Create a download task for a URL + quality selection."""

    url: str = Field(..., min_length=1, max_length=2048, examples=["https://youtu.be/..."])
    quality: str = Field(..., min_length=1, max_length=64, examples=["1080p", "720p", "audio"])
    format: str = Field(default="mp4", min_length=1, max_length=32)
    title: str | None = Field(default=None, max_length=512)
    platform: str | None = Field(default=None, max_length=64)

    @field_validator("url", "quality")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Поле не может быть пустым")
        return cleaned


class DownloadCreateResponse(BaseModel):
    """Immediate response after enqueueing a download."""

    task_id: UUID
    status: str = "queued"
    download_id: UUID
