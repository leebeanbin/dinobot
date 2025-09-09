"""
Service interface definition module
- Defines contracts for each service
- Abstract interfaces for dependency injection
- Abstraction layer for testing and extensibility
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Protocol
from datetime import datetime

from .dtos import (
    NotionPageCreateRequestDTO,
    NotionPageResponseDTO,
    NotionSchemaDTO,
    DiscordCommandRequestDTO,
    DiscordMessageResponseDTO,
    ThreadInfoDTO,
    NotionWebhookRequestDTO,
    WebhookProcessResultDTO,
    CommandExecutionMetricDTO,
    APICallMetricDTO,
    CachePerformanceMetricDTO,
    SystemStatusDTO,
    TaskCreateRequestDTO,
    MeetingCreateRequestDTO,
)


# ===== Notion Service Interface =====


class INotionService(ABC):
    """
    Service interface for Notion API interactions

    Responsibilities:
    - Notion database schema management
    - Page creation and updates
    - Automatic property option management
    - Page content extraction and summarization
    """

    @abstractmethod
    async def get_database_schema(self, database_id: str) -> NotionSchemaDTO:
        """
        Retrieve Notion database schema information.
        Performance optimized through caching.

        Args:
            database_id: Notion database ID

        Returns:
            Database schema information

        Raises:
            NotionAPIException: When API call fails
        """
        pass

    @abstractmethod
    async def ensure_select_options(
        self,
        database_id: str,
        property_name: str,
        required_options: List[str]
    ) -> List[str]:
        """
        Ensure select/multi-select options exist in the database.
        Automatically adds missing options.

        Args:
            database_id: Target database ID
            property_name: Property name
            required_options: Required option list

        Returns:
            Final option list (including existing ones)

        Raises:
            NotionAPIException: When API call fails
        """
        pass

    @abstractmethod
    async def create_page(
        self,
        request: NotionPageCreateRequestDTO
    ) -> NotionPageResponseDTO:
        """
        Create a new page in Notion database.
        Automatically handles type conversion and validation.

        Args:
            request: Page creation request

        Returns:
            Creation result information

        Raises:
            NotionAPIException: When API call fails
            UserInputException: When input validation fails
        """
        pass

    @abstractmethod
    async def extract_page_content(self, page_id: str) -> str:
        """
        Extract text content from Notion page.

        Args:
            page_id: Target page ID

        Returns:
            Extracted text content

        Raises:
            NotionAPIException: When API call fails
        """
        pass

    @abstractmethod
    def generate_meeting_summary(self, original_text: str) -> str:
        """
        Generate meeting summary from original text.

        Args:
            original_text: Original meeting content

        Returns:
            Generated summary text
        """
        pass

    # Business logic methods
    @abstractmethod
    async def create_task(self, request: TaskCreateRequestDTO) -> NotionPageResponseDTO:
        """
        Create task page in Factory Tracker database.

        Args:
            request: Task creation request

        Returns:
            Created page information
        """
        pass

    @abstractmethod
    async def create_meeting_minutes(self, request: MeetingCreateRequestDTO) -> NotionPageResponseDTO:
        """
        Create meeting minutes page in Board database.

        Args:
            request: Meeting creation request

        Returns:
            Created page information
        """
        pass


# ===== Discord Service Interface =====


class IDiscordService(ABC):
    """
    Service interface for Discord bot interactions

    Responsibilities:
    - Discord bot lifecycle management
    - Slash command processing
    - Thread management
    - Message sending
    - User information management
    """

    @abstractmethod
    async def process_command(
        self,
        request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """
        Process Discord slash command.

        Args:
            request: Command execution request

        Returns:
            Discord response message

        Raises:
            DiscordAPIException: When Discord API call fails
        """
        pass

    @abstractmethod
    async def get_or_create_daily_thread(
        self,
        channel_id: int,
        date_str: str
    ) -> ThreadInfoDTO:
        """
        Retrieve or create daily thread.

        Args:
            channel_id: Parent channel ID
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Thread information

        Raises:
            DiscordAPIException: When Discord API call fails
        """
        pass

    @abstractmethod
    async def send_thread_message(self, thread_id: int, message: str) -> bool:
        """
        Send message to specific thread.

        Args:
            thread_id: Target thread ID
            message: Message content

        Returns:
            Success status

        Raises:
            DiscordAPIException: When Discord API call fails
        """
        pass

    @abstractmethod
    async def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve Discord user information.

        Args:
            user_id: Target user ID

        Returns:
            User information (None if not found)

        Raises:
            DiscordAPIException: When Discord API call fails
        """
        pass

    @abstractmethod
    async def check_bot_status(self) -> Dict[str, Any]:
        """
        Check Discord bot status.

        Returns:
            Bot status information
        """
        pass


# ===== Cache Service Interface =====


class ICacheService(ABC):
    """
    Cache service interface for performance optimization

    Responsibilities:
    - Schema information caching
    - Thread information caching
    - Cache statistics management
    """

    @abstractmethod
    async def get_schema_cache(self, database_id: str) -> Optional[NotionSchemaDTO]:
        """Retrieve cached schema information"""
        pass

    @abstractmethod
    async def set_schema_cache(self, schema: NotionSchemaDTO) -> bool:
        """Store schema in cache"""
        pass

    @abstractmethod
    async def invalidate_schema_cache(self, database_id: str) -> bool:
        """Invalidate specific schema cache"""
        pass

    @abstractmethod
    async def get_thread_cache(
        self,
        channel_id: int,
        date_str: str
    ) -> Optional[ThreadInfoDTO]:
        """Retrieve cached thread information"""
        pass

    @abstractmethod
    async def set_thread_cache(self, thread_info: ThreadInfoDTO) -> bool:
        """Store thread information in cache"""
        pass

    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Retrieve cache statistics"""
        pass


# ===== Metrics Service Interface =====


class IMetricsService(ABC):
    """
    Metrics collection service interface

    Responsibilities:
    - Command execution metrics recording
    - API call metrics recording
    - Cache performance metrics recording
    - Performance statistics generation
    """

    @abstractmethod
    async def record_command_metric(self, metric: CommandExecutionMetricDTO) -> bool:
        """Record command execution metric"""
        pass

    @abstractmethod
    async def record_api_call_metric(self, metric: APICallMetricDTO) -> bool:
        """Record API call metric"""
        pass

    @abstractmethod
    async def record_cache_metric(self, metric: CachePerformanceMetricDTO) -> bool:
        """Record cache performance metric"""
        pass

    @abstractmethod
    async def get_daily_stats(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Retrieve daily statistics"""
        pass

    @abstractmethod
    async def get_realtime_performance(self) -> Dict[str, Any]:
        """Retrieve real-time performance metrics"""
        pass


# ===== Webhook Service Interface =====


class IWebhookService(ABC):
    """
    Webhook processing service interface

    Responsibilities:
    - Notion webhook request processing
    - Webhook security verification
    - Content extraction and Discord notification
    """

    @abstractmethod
    async def process_notion_webhook(self, request: NotionWebhookRequestDTO) -> WebhookProcessResultDTO:
        """
        Process Notion webhook request.

        Args:
            request: Webhook request information

        Returns:
            Processing result

        Raises:
            WebhookProcessingException: When processing fails
        """
        pass

    @abstractmethod
    async def verify_webhook_security(self, secret: str, request_data: Dict[str, Any]) -> bool:
        """
        Verify webhook security.

        Args:
            secret: Provided secret
            request_data: Request data

        Returns:
            Verification result
        """
        pass


# ===== Monitoring Service Interface =====


class IMonitoringService(ABC):
    """
    System monitoring service interface

    Responsibilities:
    - Overall system status checking
    - Service health checking
    - Performance warning detection
    """

    @abstractmethod
    async def check_system_status(self) -> SystemStatusDTO:
        """Check overall system status"""
        pass

    @abstractmethod
    async def check_service_health(self) -> List[Dict[str, Any]]:
        """Check individual service health"""
        pass

    @abstractmethod
    async def check_performance_warnings(self) -> List[Dict[str, Any]]:
        """Check performance warnings"""
        pass


# ===== Business Service Interface =====


class IBusinessService(ABC):
    """
    Business logic service interface

    Responsibilities:
    - High-level business workflow coordination
    - Cross-service operation orchestration
    - Business rule enforcement
    """

    @abstractmethod
    async def execute_task_creation_workflow(
        self,
        assignee: str,
        task_name: str,
        requester_user_id: int,
        channel_id: int
    ) -> DiscordMessageResponseDTO:
        """Execute task creation business workflow"""
        pass

    @abstractmethod
    async def execute_meeting_creation_workflow(
        self,
        title: str,
        requester_user_id: int,
        channel_id: int
    ) -> DiscordMessageResponseDTO:
        """Execute meeting minutes creation business workflow"""
        pass

    @abstractmethod
    async def execute_webhook_summary_workflow(
        self,
        page_id: str,
        channel_id: int
    ) -> WebhookProcessResultDTO:
        """Execute webhook summary business workflow"""
        pass


# ===== Protocol Definitions =====


class LoggerProtocol(Protocol):
    """Logger protocol definition"""

    def info(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def debug(self, message: str) -> None: ...


class SettingsProtocol(Protocol):
    """Settings protocol definition"""

    discord_token: str
    notion_token: str
    mongodb_url: str
    webhook_secret: str


# ===== Main Service Manager Interface =====


class IServiceManager(ABC):
    """
    Main service manager interface for dependency injection

    Responsibilities:
    - Service instance management
    - Dependency injection coordination
    - Service lifecycle management
    """

    @property
    @abstractmethod
    def notion_service(self) -> INotionService:
        """Get Notion service instance"""
        pass

    @property
    @abstractmethod
    def discord_service(self) -> IDiscordService:
        """Get Discord service instance"""
        pass

    @property
    @abstractmethod
    def cache_service(self) -> ICacheService:
        """Get cache service instance"""
        pass

    @property
    @abstractmethod
    def metrics_service(self) -> IMetricsService:
        """Get metrics service instance"""
        pass

    @property
    @abstractmethod
    def business_service(self) -> IBusinessService:
        """Get business service instance"""
        pass

    @abstractmethod
    async def initialize_all_services(self) -> bool:
        """Initialize all services"""
        pass

    @abstractmethod
    async def shutdown_all_services(self) -> bool:
        """Shutdown all services"""
        pass

    @abstractmethod
    async def check_service_status(self) -> SystemStatusDTO:
        """Check status of all services"""
        pass
