"""Pydantic schemas for analyze endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    """Incoming URL to inspect."""

    url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="Ссылка на видео или плейлист",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Укажите ссылку на видео")
        return cleaned


class FormatInfo(BaseModel):
    """Available download format option."""

    quality: str
    format: str
    size: str | None = None
    format_id: str | None = None
    has_audio: bool = True
    has_video: bool = True


class PlaylistEntryInfo(BaseModel):
    """Video entry inside a playlist."""

    id: str
    title: str
    thumbnail: str | None = None
    url: str | None = None
    duration: str | None = None
    index: int | None = None


class AnalyzeResponse(BaseModel):
    """
    Result of URL analysis.

    Core fields (required by clients):
    platform, title, thumbnail, formats.
    """

    platform: str
    title: str
    thumbnail: str | None = None
    formats: list[FormatInfo] = Field(default_factory=list)

    # Extra metadata for bot / extension UX
    author: str | None = None
    duration: str | None = None
    url: str
    is_playlist: bool = False
    playlist_count: int | None = None
    entries: list[PlaylistEntryInfo] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "platform": "youtube",
                    "title": "Minecraft Survival",
                    "thumbnail": "https://i.ytimg.com/vi/xxx/hqdefault.jpg",
                    "formats": [
                        {"quality": "1080p", "format": "mp4", "size": "120.5MB"},
                        {"quality": "720p", "format": "mp4", "size": "65.0MB"},
                        {"quality": "480p", "format": "mp4", "size": "35.0MB"},
                        {"quality": "audio", "format": "m4a", "size": "4.2MB"},
                    ],
                    "author": "Channel",
                    "duration": "12:34",
                    "url": "https://www.youtube.com/watch?v=xxx",
                    "is_playlist": False,
                    "playlist_count": None,
                    "entries": [],
                }
            ]
        }
    }
