"""Configuration settings for DinoBot."""

import os
from typing import Optional, Any
from zoneinfo import ZoneInfo
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 설정 관리자 초기화 (순환 import 방지)
try:
    from .config_manager import config_manager
except ImportError:
    config_manager = None


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
    mongodb_db_name: str = "dinobot"

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 설정 관리자와 동기화
        if config_manager:
            self._sync_with_config_manager()

    def _sync_with_config_manager(self):
        """설정 관리자와 동기화 (동기 버전)"""
        # 설정 관리자에서 값 가져오기 (동기적으로)
        for key, schema in config_manager.schemas.items():
            if key in config_manager.values:
                value = config_manager.values[key].value
                if value is not None:
                    # Pydantic 필드명으로 변환 (대문자 -> 소문자)
                    field_name = key.lower()
                    if hasattr(self, field_name):
                        setattr(self, field_name, value)

    def get_from_config_manager(self, key: str, default: Any = None):
        """설정 관리자에서 값 가져오기 (동기 버전)"""
        if config_manager and key in config_manager.values:
            return config_manager.values[key].value
        return default

    def set_to_config_manager(self, key: str, value: Any):
        """설정 관리자에 값 설정"""
        if config_manager:
            return config_manager.set(key, value, "settings_sync")
        return False

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def tz(self) -> ZoneInfo:
        """Get timezone object."""
        return ZoneInfo(self.timezone)


# Global settings instance
settings = Settings()
