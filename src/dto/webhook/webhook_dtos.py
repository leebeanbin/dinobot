"""
웹훅 관련 DTO classes
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import Field

from src.dto.common.base_dto import BaseDTO


class NotionWebhookRequestDTO(BaseDTO):
    """Notion webhook request data"""

    object: str = Field(..., description="Object type")
    event_id: str = Field(..., description="Event ID")
    event_time: datetime = Field(..., description="Event time")
    event_type: str = Field(..., description="Event type")
    database_id: Optional[str] = Field(default=None, description="Database ID")
    page_id: Optional[str] = Field(default=None, description="Page ID")


class WebhookProcessResultDTO(BaseDTO):
    """Webhook processing result"""

    success: bool = Field(..., description="Processing success")
    message: str = Field(..., description="Result message")
    processed_at: datetime = Field(
        default_factory=datetime.now, description="Processing time"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional details"
    )