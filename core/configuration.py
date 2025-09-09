"""
Improved configuration module following Single Responsibility Principle
- Separated configuration concerns into focused classes
- Better type safety and validation
- Clear configuration categories
"""

import os
from typing import Optional
from zoneinfo import ZoneInfo
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DiscordConfiguration(BaseSettings):
    """Configuration for Discord-related settings"""
    
    token: str = Field(..., description="Discord bot token")
    application_id: str = Field(..., alias="discord_app_id", description="Discord application ID")
    guild_id: str = Field(..., description="Target Discord guild/server ID")
    default_channel_id: Optional[int] = Field(None, description="Default channel for bot messages")
    
    class Config:
        env_prefix = "DISCORD_"


class NotionConfiguration(BaseSettings):
    """Configuration for Notion API settings"""
    
    token: str = Field(..., description="Notion integration token")
    factory_tracker_database_id: str = Field(..., alias="factory_tracker_db_id", description="Factory tracker database ID")
    board_database_id: str = Field(..., alias="board_db_id", description="Board database ID")
    
    class Config:
        env_prefix = "NOTION_"


class DatabaseConfiguration(BaseSettings):
    """Configuration for database connections"""
    
    mongodb_url: str = Field(default="mongodb://localhost:27017", description="MongoDB connection URL")
    mongodb_database_name: str = Field(default="meetuploader", description="MongoDB database name")
    
    @validator('mongodb_url')
    def validate_mongodb_url(cls, value):
        if not value.startswith(('mongodb://', 'mongodb+srv://')):
            raise ValueError('MongoDB URL must start with mongodb:// or mongodb+srv://')
        return value


class ServerConfiguration(BaseSettings):
    """Configuration for web server settings"""
    
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8888, ge=1, le=65535, description="Server port number")
    timezone: str = Field(default="Asia/Seoul", description="Application timezone")
    
    @validator('timezone')
    def validate_timezone(cls, value):
        try:
            ZoneInfo(value)
        except Exception:
            raise ValueError(f'Invalid timezone: {value}')
        return value


class SecurityConfiguration(BaseSettings):
    """Configuration for security-related settings"""
    
    webhook_secret: str = Field(default="my-notion-webhook-secret", description="Webhook verification secret")
    
    class Config:
        env_prefix = "SECURITY_"


class PerformanceConfiguration(BaseSettings):
    """Configuration for performance optimization settings"""
    
    schema_cache_ttl_seconds: int = Field(default=3600, ge=60, description="Schema cache TTL in seconds")
    page_content_cache_ttl_seconds: int = Field(default=600, ge=60, description="Page content cache TTL in seconds")
    sync_interval_seconds: int = Field(default=180, ge=30, description="Synchronization interval in seconds")
    api_retry_attempts: int = Field(default=3, ge=1, le=10, description="API retry attempts")
    batch_processing_size: int = Field(default=50, ge=1, le=1000, description="Batch processing size")
    concurrent_operations_limit: int = Field(default=10, ge=1, le=50, description="Concurrent operations limit")
    
    class Config:
        env_prefix = "PERFORMANCE_"


class MessagingConfiguration(BaseSettings):
    """Configuration for messaging and content settings"""
    
    discord_message_chunk_size: int = Field(default=1800, ge=100, le=2000, description="Discord message chunk size")
    notification_retry_attempts: int = Field(default=3, ge=1, le=10, description="Notification retry attempts")
    
    class Config:
        env_prefix = "MESSAGING_"


class ApplicationConfiguration:
    """
    Main application configuration aggregator following Composition pattern
    
    Advantages:
    - Single point of configuration access
    - Separated concerns
    - Better testability
    - Type safety
    """
    
    def __init__(self):
        self.discord = DiscordConfiguration()
        self.notion = NotionConfiguration()
        self.database = DatabaseConfiguration()
        self.server = ServerConfiguration()
        self.security = SecurityConfiguration()
        self.performance = PerformanceConfiguration()
        self.messaging = MessagingConfiguration()
    
    def validate_all_configurations(self) -> bool:
        """Validate all configuration sections"""
        try:
            # Validate required configurations exist
            assert self.discord.token, "Discord token is required"
            assert self.notion.token, "Notion token is required"
            assert self.database.mongodb_url, "MongoDB URL is required"
            return True
        except (AssertionError, ValueError) as error:
            raise ValueError(f"Configuration validation failed: {error}")
    
    def get_timezone(self) -> ZoneInfo:
        """Get timezone object for the application"""
        return ZoneInfo(self.server.timezone)
    
    def is_development_mode(self) -> bool:
        """Check if application is running in development mode"""
        return os.getenv("ENVIRONMENT", "production").lower() in ["development", "dev", "local"]
    
    def get_log_level(self) -> str:
        """Get appropriate log level based on environment"""
        if self.is_development_mode():
            return os.getenv("LOG_LEVEL", "DEBUG")
        return os.getenv("LOG_LEVEL", "INFO")


# Global configuration instance
application_config = ApplicationConfiguration()

# Backward compatibility - maintain existing interface
class Settings(BaseSettings):
    """Backward compatible settings class"""
    
    @property
    def discord_token(self) -> str:
        return application_config.discord.token
    
    @property
    def discord_app_id(self) -> str:
        return application_config.discord.application_id
    
    @property
    def discord_guild_id(self) -> str:
        return application_config.discord.guild_id
    
    @property
    def notion_token(self) -> str:
        return application_config.notion.token
    
    @property
    def factory_tracker_db_id(self) -> str:
        return application_config.notion.factory_tracker_database_id
    
    @property
    def board_db_id(self) -> str:
        return application_config.notion.board_database_id
    
    @property
    def mongodb_url(self) -> str:
        return application_config.database.mongodb_url
    
    @property
    def mongodb_db_name(self) -> str:
        return application_config.database.mongodb_database_name
    
    @property
    def host(self) -> str:
        return application_config.server.host
    
    @property
    def port(self) -> int:
        return application_config.server.port
    
    @property
    def webhook_secret(self) -> str:
        return application_config.security.webhook_secret
    
    @property
    def discord_message_chunk_size(self) -> int:
        return application_config.messaging.discord_message_chunk_size
    
    @property
    def sync_recent_threshold(self) -> int:
        return application_config.performance.sync_interval_seconds
    
    @property
    def api_retry_attempts(self) -> int:
        return application_config.performance.api_retry_attempts
    
    @property
    def batch_size(self) -> int:
        return application_config.performance.batch_processing_size


# Global settings instance for backward compatibility
settings = Settings()