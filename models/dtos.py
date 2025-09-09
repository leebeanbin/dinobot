"""
Data Transfer Objects (DTOs) for MeetupLoader
- Standardized objects for data transfer between services
- Type safety and data validation
- Handles conversion between MongoDB documents and API responses
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class CommandType(str, Enum):
    """Discord command type enumeration"""

    TASK = "task"  # Factory Tracker DB에 Task 생성
    MEETING = "meeting"  # Board DB에 회의록 생성
    DOCUMENT = "document"  # Board DB에 문서 생성 (개발 문서, 기획안, 개발 규칙)
    STATUS = "status"
    HELP = "help"
    FETCH_PAGE = "fetch_page"
    WATCH_PAGE = "watch_page"

    # 통계 관련 명령어들
    DAILY_STATS = "daily_stats"
    WEEKLY_STATS = "weekly_stats"
    MONTHLY_STATS = "monthly_stats"
    USER_STATS = "user_stats"
    TEAM_STATS = "team_stats"
    TRENDS = "trends"
    TASK_STATS = "task_stats"
    SEARCH = "search"


class NotionPropertyType(str, Enum):
    """Notion property type enumeration"""

    TITLE = "title"
    RICH_TEXT = "rich_text"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    STATUS = "status"
    CHECKBOX = "checkbox"
    DATE = "date"
    NUMBER = "number"
    PERSON = "person"
    RELATION = "relation"


class MessageType(str, Enum):
    """Message type classification"""

    COMMAND_RESPONSE = "command_response"
    WEBHOOK_SUMMARY = "webhook_summary"
    ERROR_NOTIFICATION = "error_notification"
    SUCCESS_NOTIFICATION = "success_notification"
    SYSTEM_STATUS = "system_status"


# ===== Base DTO Classes =====


class BaseDTO(BaseModel):
    """Base class for all DTOs"""

    model_config = {
        # Allow field names in Korean (changed to validate_by_name in Pydantic v2)
        "validate_by_name": True,
        # Convert Enum to values during JSON serialization
        "use_enum_values": True,
    }

    def model_dump_json(self, **kwargs):
        """Serialize datetime objects to ISO format"""
        return super().model_dump_json(mode="json", **kwargs)


# ===== Notion Related DTOs =====


class NotionPropertyDTO(BaseDTO):
    """Notion database property information"""

    property_name: str = Field(..., description="Notion property name")
    property_type: NotionPropertyType = Field(..., description="Property type")
    is_required: bool = Field(default=False, description="Is required input")
    default_value: Optional[Any] = Field(default=None, description="Default value")
    select_options: Optional[List[str]] = Field(
        default=None, description="Select/Status option list"
    )

    @field_validator("select_options")
    @classmethod
    def validate_select_options(cls, v, info):
        """Allow options only for Select-type properties"""
        # Access other field values using info.data in Pydantic v2
        property_type = info.data.get("property_type") if info.data else None
        if property_type in [
            NotionPropertyType.SELECT,
            NotionPropertyType.MULTI_SELECT,
            NotionPropertyType.STATUS,
        ]:
            return v or []
        return None


class NotionSchemaDTO(BaseDTO):
    """Notion database schema information"""

    database_id: str = Field(..., description="Notion database ID")
    database_title: str = Field(..., description="Database title")
    properties: List[NotionPropertyDTO] = Field(
        default_factory=list, description="Property list"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Schema last update time"
    )
    cache_expires_at: Optional[datetime] = Field(
        default=None, description="Cache expiration time"
    )


class NotionPageCreateRequestDTO(BaseDTO):
    """Request for creating Notion page"""

    database_id: str = Field(..., description="Target database ID")
    property_values: Dict[str, Any] = Field(
        default_factory=dict, description="Property values"
    )
    requester_user_id: Optional[int] = Field(
        default=None, description="Requesting user Discord ID"
    )

    @field_validator("property_values")
    @classmethod
    def validate_property_values(cls, v):
        """Check if property values is not empty dictionary"""
        return v if isinstance(v, dict) else {}


class NotionPageResponseDTO(BaseDTO):
    """Notion page creation result"""

    page_id: str = Field(..., description="Created page ID")
    page_url: str = Field(..., description="Page URL")
    created_time: datetime = Field(
        default_factory=datetime.now, description="Creation time"
    )
    property_count: int = Field(default=0, description="Number of set properties")


class DiscordUserDTO(BaseDTO):
    """Discord user information"""

    user_id: int = Field(..., description="Discord user ID")
    username: str = Field(..., description="Username")
    display_name: Optional[str] = Field(
        default=None, description="Display name in server"
    )
    avatar_url: Optional[str] = Field(default=None, description="Avatar image URL")


class DiscordGuildDTO(BaseDTO):
    """Discord guild (server) information"""

    guild_id: int = Field(..., description="Discord guild ID")
    guild_name: str = Field(..., description="Server name")
    channel_id: Optional[int] = Field(
        default=None, description="Command execution channel ID"
    )


class DiscordCommandRequestDTO(BaseDTO):
    """Discord command execution request"""

    command_type: CommandType = Field(..., description="Command type")
    user: DiscordUserDTO = Field(..., description="Requesting user info")
    guild: DiscordGuildDTO = Field(..., description="Server info")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Command parameters"
    )
    execution_time: datetime = Field(
        default_factory=datetime.now, description="Command execution time"
    )

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, v, info):
        """Check required parameters by command type"""
        # Access other field values using info.data in Pydantic v2
        command = info.data.get("command_type") if info.data else None
        if command == CommandType.TASK:
            if "person" not in v or "name" not in v:
                raise ValueError("task command requires 'person', 'name' parameters")
        elif command == CommandType.MEETING:
            if "title" not in v:
                raise ValueError("meeting command requires 'title' parameter")
        return v


class DiscordMessageResponseDTO(BaseDTO):
    """Discord message response"""

    content: str = Field(..., description="Message content")
    title: Optional[str] = Field(default=None, description="Message title")
    message_type: MessageType = Field(
        default=MessageType.COMMAND_RESPONSE, description="Message type"
    )
    is_embed: bool = Field(default=False, description="Use embed message")
    is_ephemeral: bool = Field(default=True, description="Ephemeral message")
    buttons: Optional[List[Dict[str, str]]] = Field(
        default=None, description="Button info list"
    )


class ThreadInfoDTO(BaseDTO):
    """Discord thread information"""

    thread_id: int = Field(..., description="Thread ID")
    thread_name: str = Field(..., description="Thread name")
    parent_channel_id: int = Field(..., description="Parent channel ID")
    created_date: str = Field(..., description="Creation date (YYYY-MM-DD)")
    created_time: datetime = Field(
        default_factory=datetime.now, description="Thread creation time"
    )
    last_used_time: datetime = Field(
        default_factory=datetime.now, description="Last used time"
    )
    usage_count: int = Field(default=1, description="Usage count")
    auto_archive_duration: int = Field(
        default=1440, description="Auto archive time (minutes)"
    )


class NotionWebhookRequestDTO(BaseDTO):
    """Notion webhook request"""

    page_id: str = Field(..., description="Notion page ID")
    channel_id: int = Field(..., description="Target Discord channel ID")
    mode: str = Field(default="meeting", description="Processing mode")
    custom_message: Optional[str] = Field(default=None, description="Custom message")
    request_ip: Optional[str] = Field(default=None, description="Requester IP")
    request_time: datetime = Field(
        default_factory=datetime.now, description="Webhook request time"
    )


class WebhookProcessResultDTO(BaseDTO):
    """Webhook processing result"""

    success: bool = Field(..., description="Processing success")
    page_id: str = Field(..., description="Processed page ID")
    extracted_text: Optional[str] = Field(default=None, description="Extracted text")
    text_length: Optional[int] = Field(
        default=None, description="Extracted text length"
    )
    discord_message_sent: bool = Field(
        default=False, description="Discord message sent"
    )
    thread_id: Optional[int] = Field(
        default=None, description="Thread ID where message was sent"
    )
    error_code: Optional[str] = Field(
        default=None, description="Error code (if failed)"
    )
    processing_time_ms: float = Field(..., description="Processing time (ms)")


class CommandExecutionMetricDTO(BaseDTO):
    """Command execution metric"""

    command_type: CommandType = Field(..., description="Command type")
    user_id: int = Field(..., description="User ID")
    guild_id: int = Field(..., description="Guild ID")
    success: bool = Field(..., description="Execution success")
    execution_time_ms: float = Field(..., description="Execution time (ms)")
    error_message: Optional[str] = Field(
        default=None, description="Error message (if failed)"
    )
    memory_usage_mb: Optional[float] = Field(default=None, description="Memory usage")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Execution time"
    )


class APICallMetricDTO(BaseDTO):
    """API call metric"""

    service_name: str = Field(..., description="Service name (discord/notion)")
    endpoint: str = Field(..., description="API endpoint")
    method: str = Field(..., description="HTTP method")
    status_code: int = Field(..., description="Response status code")
    response_time_ms: float = Field(..., description="Response time (ms)")
    request_size_bytes: Optional[int] = Field(
        default=None, description="Request data size"
    )
    response_size_bytes: Optional[int] = Field(
        default=None, description="Response data size"
    )
    user_id: Optional[int] = Field(default=None, description="User ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Call time")


class CachePerformanceMetricDTO(BaseDTO):
    """Cache performance metric"""

    cache_type: str = Field(..., description="Cache type (schema/thread)")
    operation: str = Field(..., description="Operation (hit/miss/set/delete)")
    key: str = Field(..., description="Cache key")
    hit: bool = Field(..., description="Cache hit")
    data_size_bytes: Optional[int] = Field(default=None, description="Cache data size")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Operation time"
    )


class ServiceStatusDTO(BaseDTO):
    """Service status"""

    service_name: str = Field(..., description="Service name")
    status: str = Field(..., description="Status (healthy/unhealthy/degraded)")
    response_time_ms: Optional[float] = Field(default=None, description="Response time")
    last_check_time: datetime = Field(
        default_factory=datetime.now, description="Last status check time"
    )
    error_message: Optional[str] = Field(default=None, description="Error message")
    additional_info: Dict[str, Any] = Field(
        default_factory=dict, description="Additional status info"
    )


class MongoDBStatusDTO(BaseDTO):
    """MongoDB status"""

    connected: bool = Field(..., description="Connection status")
    database_name: str = Field(..., description="Database name")
    collection_count: int = Field(default=0, description="Collection count")
    total_documents: int = Field(default=0, description="Total document count")
    recent_error_count: int = Field(default=0, description="Recent 1-hour error count")


class SystemStatusDTO(BaseDTO):
    """Overall system status"""

    status: str = Field(..., description="Overall status")
    current_time: datetime = Field(
        default_factory=datetime.now, description="Current time"
    )
    uptime_seconds: float = Field(..., description="System uptime (seconds)")
    total_processed_commands: int = Field(
        default=0, description="Total processed commands"
    )
    total_webhook_calls: int = Field(default=0, description="Total webhook calls")
    services: List[ServiceStatusDTO] = Field(
        default_factory=list, description="Service status list"
    )
    mongodb: MongoDBStatusDTO = Field(..., description="MongoDB status")


class TaskCreateRequestDTO(BaseDTO):
    """Task creation request"""

    assignee: str = Field(..., description="Task assignee")
    task_name: str = Field(..., description="Task name")
    priority: Optional[str] = Field(default="Normal", description="Priority")
    due_date: Optional[str] = Field(default=None, description="Due date (YYYY-MM-DD)")
    description: Optional[str] = Field(default=None, description="Task description")
    task_type: Optional[str] = Field(default=None, description="Task type")
    tags: List[str] = Field(default_factory=list, description="Tag list")

    @field_validator("due_date")
    @classmethod
    def validate_due_date_format(cls, v):
        """Validate due date format"""
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("Due date must be in YYYY-MM-DD format")


class MeetingCreateRequestDTO(BaseDTO):
    """Meeting minutes creation request"""

    title: str = Field(..., description="Meeting title")
    meeting_date: Optional[str] = Field(default=None, description="Meeting date")
    attendees: List[str] = Field(default_factory=list, description="Attendee list")
    meeting_type: Optional[str] = Field(
        default="Regular Meeting", description="Meeting type"
    )
    agenda_items: List[str] = Field(default_factory=list, description="Agenda list")


class DTOConverter:
    """DTO conversion utilities"""

    @staticmethod
    def notion_page_response_convert(
        notion_response: Dict[str, Any],
    ) -> NotionPageResponseDTO:
        """Convert Notion API response to DTO"""
        return NotionPageResponseDTO(
            page_id=notion_response.get("id", ""),
            page_url=notion_response.get("url", ""),
            property_count=len(notion_response.get("properties", {})),
        )

    @staticmethod
    def mongodb_doc_to_thread_dto(document: Dict[str, Any]) -> ThreadInfoDTO:
        """Convert MongoDB document to Thread DTO"""
        return ThreadInfoDTO(
            thread_id=document.get("thread_id", 0),
            thread_name=document.get("thread_name", ""),
            parent_channel_id=document.get("parent_channel_id", 0),
            created_date=document.get("created_date", ""),
            usage_count=document.get("usage_count", 1),
            auto_archive_duration=document.get("auto_archive_duration", 1440),
        )

    @staticmethod
    def thread_dto_to_mongodb_doc(thread_dto: ThreadInfoDTO) -> Dict[str, Any]:
        """Convert Thread DTO to MongoDB document"""
        return {
            "thread_id": thread_dto.thread_id,
            "thread_name": thread_dto.thread_name,
            "parent_channel_id": thread_dto.parent_channel_id,
            "created_date": thread_dto.created_date,
            "created_time": thread_dto.created_time,
            "last_used_time": thread_dto.last_used_time,
            "usage_count": thread_dto.usage_count,
            "auto_archive_duration": thread_dto.auto_archive_duration,
        }
