"""
Notion 관련 DTO classes
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator

from src.dto.common.base_dto import BaseDTO
from src.dto.common.enums import NotionPropertyType


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
        default=None, description="Request user ID"
    )


class NotionPageResponseDTO(BaseDTO):
    """Notion page creation response"""

    page_id: str = Field(..., description="Created page ID")
    page_url: str = Field(..., description="Page URL")
    created_time: datetime = Field(..., description="Page creation time")
    last_edited_time: Optional[datetime] = Field(
        default=None, description="Last edit time"
    )