"""Configuration settings for DinoBot."""

import os
from typing import Optional
from zoneinfo import ZoneInfo
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # Discord settings
    discord_token: str
    discord_app_id: str
    discord_guild_id: str
    discord_channel_id: Optional[int] = None
    default_discord_channel_id: Optional[int] = None

    # Notion settings
    notion_token: str
    factory_tracker_db_id: str
    board_db_id: str

    # Google Calendar settings
    google_calendar_credentials_file: str = "credentials.json"
    google_calendar_token_file: str = "token.json"

    # Discord Event settings
    discord_event_channel_id: Optional[int] = None
    discord_event_guild_id: Optional[str] = None

    # MongoDB settings
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "meetuploader"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8889
    timezone: str = "Asia/Seoul"

    # Security settings
    webhook_secret: str = "my-notion-webhook-secret"

    # Caching settings
    schema_cache_ttl: int = 3600  # 1 hour in seconds
    page_content_cache_ttl: int = 600  # 10 minutes in seconds

    # Performance settings
    discord_message_chunk_size: int = 1800  # Discord message split size
    sync_recent_threshold: int = 1800  # 30 minutes in seconds
    cleanup_interval: int = 3600  # 1 hour in seconds
    auto_archive_duration: int = 1440  # 24 hours in minutes

    # API settings
    max_concurrent_requests: int = 10
    api_retry_attempts: int = 3
    api_retry_backoff: float = 1.0
    batch_size: int = 50

    # Logging settings
    log_level: str = "INFO"
    log_to_file: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def tz(self) -> ZoneInfo:
        """Get timezone object."""
        return ZoneInfo(self.timezone)


# Global settings instance
settings = Settings()
