"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Runtime settings for the Cliperry backend.

    Values are loaded from environment variables and optional ``.env`` file.
    Never commit real secrets — use ``.env.example`` as a template.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "Cliperry"
    app_env: Literal["development", "staging", "production", "dev", "local", "test"] = (
        "development"
    )
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = Field(default="change-me-in-production", min_length=8)
    api_prefix: str = "/api"
    api_version: str = "0.1.0"

    # --- HTTP server ---
    host: str = "0.0.0.0"
    port: int = 8000
    trusted_hosts: str = "*"
    # Trust X-Forwarded-For only when behind a known reverse proxy.
    trust_proxy_headers: bool = False

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://cliperry:cliperry@localhost:5432/cliperry"
    )
    database_url_sync: str = (
        "postgresql+psycopg2://cliperry:cliperry@localhost:5432/cliperry"
    )

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # --- Temporary storage ---
    temp_dir: str = "/tmp/cliperry"
    temp_file_ttl_seconds: int = 1800
    # Soft cap for yt-dlp downloads (bytes). Default 2 GiB.
    download_max_filesize_bytes: int = 2 * 1024 * 1024 * 1024

    # --- yt-dlp (YouTube bot checks often need cookies on VPS/datacenter IPs) ---
    ytdlp_cookies_from_browser: str = ""
    ytdlp_cookies_file: str = ""
    ytdlp_proxy: str = ""

    # --- Rate limiting ---
    rate_limit_analyze: int = 30
    rate_limit_download: int = 15
    rate_limit_history: int = 60
    rate_limit_tasks: int = 120
    rate_limit_admin_login: int = 10
    rate_limit_ip_global: int = 180
    rate_limit_window_seconds: int = 60
    rate_limit_ws: int = 30
    ws_max_session_seconds: int = 900
    ws_db_fallback_seconds: int = 10

    # --- CORS (comma-separated origins) ---
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Comma-separated chrome extension ids or full chrome-extension:// origins
    cors_extension_ids: str = ""

    # --- Integrations ---
    telegram_bot_token: str = ""
    backend_public_url: str = "http://localhost:8000"
    admin_username: str = "admin"
    admin_password: str = "change-me"
    enable_worker_test: bool = True

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> str:
        if isinstance(value, str):
            return value.upper().strip()
        return "INFO"

    @field_validator("cors_origins", "trusted_hosts", "cors_extension_ids", mode="before")
    @classmethod
    def strip_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        """Parse comma-separated trusted hosts (``*`` allows all)."""
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local", "test"}

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def docs_enabled(self) -> bool:
        """OpenAPI docs are disabled in production unless debug is on."""
        return self.debug or not self.is_production


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton per process)."""
    return Settings()
