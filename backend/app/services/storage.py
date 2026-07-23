"""Temporary file storage and signed download URL helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings, get_settings


@dataclass(slots=True)
class TempArtifact:
    """A short-lived download workspace on disk."""

    artifact_id: str
    directory: Path
    expires_at: int

    @property
    def output_template(self) -> str:
        """yt-dlp outtmpl pointing inside this artifact directory."""
        return str(self.directory / "%(id)s.%(ext)s")


class StorageService:
    """
    Manages short-lived download artifacts on local disk.

    Files live under ``TEMP_DIR/{artifact_id}/`` and are cleaned up after TTL.
    Signed tokens authorize temporary download URLs — nothing is kept permanently.
    """

    META_NAME = ".cliperry-meta.json"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.temp_root = Path(self.settings.temp_dir)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def allocate(self, artifact_id: str | None = None) -> TempArtifact:
        """Create a fresh temporary directory with expiry metadata."""
        aid = artifact_id or str(uuid.uuid4())
        directory = self.temp_root / aid
        directory.mkdir(parents=True, exist_ok=True)
        expires_at = int(time.time()) + self.settings.temp_file_ttl_seconds
        meta = {
            "artifact_id": aid,
            "expires_at": expires_at,
            "created_at": int(time.time()),
        }
        (directory / self.META_NAME).write_text(json.dumps(meta), encoding="utf-8")
        return TempArtifact(artifact_id=aid, directory=directory, expires_at=expires_at)

    def task_dir(self, task_id: str) -> Path:
        """Return (and create) the working directory for a task id."""
        return self.allocate(task_id).directory

    def create_download_token(self, task_id: str, expires_at: int | None = None) -> str:
        """Create an HMAC-signed token for a temporary download URL."""
        if expires_at is None:
            expires_at = int(time.time()) + self.settings.temp_file_ttl_seconds
        payload = f"{task_id}:{expires_at}"
        signature = hmac.new(
            self.settings.secret_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{expires_at}.{signature}"

    def verify_download_token(self, task_id: str, token: str) -> bool:
        """Validate a signed download token and expiry."""
        try:
            expires_str, _signature = token.split(".", 1)
            expires_at = int(expires_str)
        except (ValueError, AttributeError):
            return False

        if expires_at < int(time.time()):
            return False

        expected = self.create_download_token(task_id, expires_at=expires_at)
        return hmac.compare_digest(expected, token)

    def cleanup_task_dir(self, task_id: str) -> None:
        """Remove temporary files for a completed/expired task."""
        path = self.temp_root / task_id
        if not path.exists():
            return
        for child in path.iterdir():
            if child.is_file():
                child.unlink(missing_ok=True)
        try:
            path.rmdir()
        except OSError:
            pass

    def cleanup_expired(self) -> int:
        """
        Delete artifact directories whose TTL has passed.

        Returns:
            Number of directories removed.
        """
        now = int(time.time())
        removed = 0
        if not self.temp_root.exists():
            return 0

        for path in self.temp_root.iterdir():
            if not path.is_dir():
                continue
            meta_path = path / self.META_NAME
            expires_at: int | None = None
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    expires_at = int(meta.get("expires_at", 0))
                except (json.JSONDecodeError, TypeError, ValueError):
                    expires_at = 0
            else:
                # No meta → treat mtime + TTL as expiry
                expires_at = int(path.stat().st_mtime) + self.settings.temp_file_ttl_seconds

            if expires_at is not None and expires_at <= now:
                self.cleanup_task_dir(path.name)
                removed += 1
        return removed
