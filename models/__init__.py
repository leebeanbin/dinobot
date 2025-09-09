# Models modules
"""
Models package for MeetupLoader
- dtos.py: Data Transfer Objects for type-safe data handling
- interfaces.py: Service interface definitions
"""

from .dtos import (
    # Base
    BaseDTO,
    CommandType,
    NotionPropertyType,
    MessageType,
    # Notion DTOs
    NotionPropertyDTO,
    NotionSchemaDTO,
    NotionPageCreateRequestDTO,
    NotionPageResponseDTO,
    # Discord DTOs
    DiscordUserDTO,
    DiscordGuildDTO,
    DiscordCommandRequestDTO,
    DiscordMessageResponseDTO,
    ThreadInfoDTO,
    # Webhook DTOs
    NotionWebhookRequestDTO,
    WebhookProcessResultDTO,
    # Metrics DTOs
    CommandExecutionMetricDTO,
    APICallMetricDTO,
    CachePerformanceMetricDTO,
    # Status DTOs
    ServiceStatusDTO,
    MongoDBStatusDTO,
    SystemStatusDTO,
    # Business DTOs
    TaskCreateRequestDTO,
    MeetingCreateRequestDTO,
    # Converter
    DTOConverter,
)

from .interfaces import (
    # Service Interfaces
    INotionService,
    IDiscordService,
    ICacheService,
    IMetricsService,
    IWebhookService,
    IMonitoringService,
    IBusinessService,
    IServiceManager,
    # Protocols
    LoggerProtocol,
    SettingsProtocol,
)

__all__ = [
    # Base
    "BaseDTO",
    "CommandType",
    "NotionPropertyType",
    "MessageType",
    # Notion DTOs
    "NotionPropertyDTO",
    "NotionSchemaDTO",
    "NotionPageCreateRequestDTO",
    "NotionPageResponseDTO",
    # Discord DTOs
    "DiscordUserDTO",
    "DiscordGuildDTO",
    "DiscordCommandRequestDTO",
    "DiscordMessageResponseDTO",
    "ThreadInfoDTO",
    # Webhook DTOs
    "NotionWebhookRequestDTO",
    "WebhookProcessResultDTO",
    # Metrics DTOs
    "CommandExecutionMetricDTO",
    "APICallMetricDTO",
    "CachePerformanceMetricDTO",
    # Status DTOs
    "ServiceStatusDTO",
    "MongoDBStatusDTO",
    "SystemStatusDTO",
    # Business DTOs
    "TaskCreateRequestDTO",
    "MeetingCreateRequestDTO",
    # Converter
    "DTOConverter",
    # Service Interfaces
    "INotionService",
    "IDiscordService",
    "ICacheService",
    "IMetricsService",
    "IWebhookService",
    "IMonitoringService",
    "IBusinessService",
    "IServiceManager",
    # Protocols
    "LoggerProtocol",
    "SettingsProtocol",
]
