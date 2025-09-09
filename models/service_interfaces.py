"""
Improved service interface definitions following SOLID principles
- Single Responsibility: Each interface has one clear purpose
- Interface Segregation: Smaller, focused interfaces instead of large ones
- Dependency Inversion: Abstract interfaces for better testability
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from .dtos import (
    NotionPageCreateRequestDTO,
    NotionPageResponseDTO,
    NotionSchemaDTO,
    DiscordCommandRequestDTO,
    DiscordMessageResponseDTO,
    ThreadInfoDTO,
)


# ===== Content Management Interfaces =====

class INotionContentReader(ABC):
    """Interface for reading content from Notion"""
    
    @abstractmethod
    async def extract_page_content(self, page_id: str) -> str:
        """Extract text content from a Notion page"""
        pass
    
    @abstractmethod
    async def check_page_exists(self, page_id: str) -> bool:
        """Check if a Notion page exists and is accessible"""
        pass


class INotionContentWriter(ABC):
    """Interface for writing content to Notion"""
    
    @abstractmethod
    async def create_page(self, request: NotionPageCreateRequestDTO) -> NotionPageResponseDTO:
        """Create a new page in Notion database"""
        pass
    
    @abstractmethod
    async def update_page_properties(self, page_id: str, properties: Dict[str, Any]) -> bool:
        """Update properties of an existing Notion page"""
        pass


class INotionSchemaManager(ABC):
    """Interface for managing Notion database schemas"""
    
    @abstractmethod
    async def get_database_schema(self, database_id: str) -> NotionSchemaDTO:
        """Retrieve database schema information"""
        pass
    
    @abstractmethod
    async def ensure_select_options(self, database_id: str, property_name: str, options: List[str]) -> List[str]:
        """Ensure select/multi-select options exist in database"""
        pass


# ===== Communication Interfaces =====

class IDiscordMessageSender(ABC):
    """Interface for sending Discord messages"""
    
    @abstractmethod
    async def send_thread_message(self, thread_id: int, message: str) -> bool:
        """Send message to a specific Discord thread"""
        pass
    
    @abstractmethod
    async def send_direct_message(self, user_id: int, message: str) -> bool:
        """Send direct message to a Discord user"""
        pass


class IDiscordThreadManager(ABC):
    """Interface for managing Discord threads"""
    
    @abstractmethod
    async def get_or_create_daily_thread(self, channel_id: int, date_str: str) -> ThreadInfoDTO:
        """Get or create a daily discussion thread"""
        pass
    
    @abstractmethod
    async def archive_thread(self, thread_id: int) -> bool:
        """Archive a Discord thread"""
        pass


class IDiscordCommandProcessor(ABC):
    """Interface for processing Discord commands"""
    
    @abstractmethod
    async def process_command(self, request: DiscordCommandRequestDTO) -> DiscordMessageResponseDTO:
        """Process a Discord slash command"""
        pass
    
    @abstractmethod
    async def register_command_handlers(self) -> bool:
        """Register command handlers with Discord API"""
        pass


# ===== Data Management Interfaces =====

class IDataSynchronizer(ABC):
    """Interface for data synchronization operations"""
    
    @abstractmethod
    async def synchronize_notion_pages(self) -> int:
        """Synchronize Notion pages with local database"""
        pass
    
    @abstractmethod
    async def remove_deleted_pages(self) -> int:
        """Remove deleted pages from local database"""
        pass


class ICacheManager(ABC):
    """Interface for cache management"""
    
    @abstractmethod
    async def get_cached_data(self, key: str) -> Optional[Any]:
        """Retrieve data from cache"""
        pass
    
    @abstractmethod
    async def set_cached_data(self, key: str, data: Any, ttl_seconds: int = 600) -> bool:
        """Store data in cache with TTL"""
        pass
    
    @abstractmethod
    async def invalidate_cache(self, key: str) -> bool:
        """Invalidate specific cache entry"""
        pass


# ===== Monitoring Interfaces =====

class IHealthChecker(ABC):
    """Interface for health checking operations"""
    
    @abstractmethod
    async def check_service_health(self) -> Dict[str, Any]:
        """Check health status of the service"""
        pass
    
    @abstractmethod
    async def check_dependencies_health(self) -> List[Dict[str, Any]]:
        """Check health of external dependencies"""
        pass


class IMetricsCollector(ABC):
    """Interface for metrics collection"""
    
    @abstractmethod
    async def record_operation_metric(self, operation: str, duration_ms: float, success: bool) -> None:
        """Record operation performance metric"""
        pass
    
    @abstractmethod
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        pass


# ===== Business Logic Interfaces =====

class ITaskWorkflowManager(ABC):
    """Interface for task-related business workflows"""
    
    @abstractmethod
    async def execute_task_creation_workflow(self, assignee: str, task_name: str, requester_id: int) -> DiscordMessageResponseDTO:
        """Execute complete task creation workflow"""
        pass


class IMeetingWorkflowManager(ABC):
    """Interface for meeting-related business workflows"""
    
    @abstractmethod
    async def execute_meeting_creation_workflow(self, title: str, requester_id: int) -> DiscordMessageResponseDTO:
        """Execute complete meeting creation workflow"""
        pass


# ===== Service Factory Interface =====

class IServiceFactory(ABC):
    """Factory interface for creating service instances"""
    
    @abstractmethod
    def create_notion_content_reader(self) -> INotionContentReader:
        """Create Notion content reader service"""
        pass
    
    @abstractmethod
    def create_notion_content_writer(self) -> INotionContentWriter:
        """Create Notion content writer service"""
        pass
    
    @abstractmethod
    def create_discord_message_sender(self) -> IDiscordMessageSender:
        """Create Discord message sender service"""
        pass
    
    @abstractmethod
    def create_cache_manager(self) -> ICacheManager:
        """Create cache manager service"""
        pass