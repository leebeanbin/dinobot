"""
Discord 관련 DTO classes
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import Field

from src.dto.common.base_dto import BaseDTO
from src.dto.common.enums import MessageType, CommandType


class DiscordUserDTO(BaseDTO):
    """Discord user information"""

    user_id: int = Field(..., description="Discord user ID")
    username: str = Field(..., description="Discord username")
    display_name: Optional[str] = Field(default=None, description="Display name")


class DiscordGuildDTO(BaseDTO):
    """Discord server information"""

    guild_id: int = Field(..., description="Discord server ID")
    channel_id: Optional[int] = Field(default=None, description="Channel ID")
    thread_id: Optional[int] = Field(default=None, description="Thread ID")


class DiscordCommandRequestDTO(BaseDTO):
    """Discord slash command request"""

    command_type: CommandType = Field(..., description="Command type")
    user: DiscordUserDTO = Field(..., description="Command user")
    guild: DiscordGuildDTO = Field(..., description="Server information")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Command parameters"
    )
    executed_at: datetime = Field(
        default_factory=datetime.now, description="Command execution time"
    )

    # Additional parameters for analytics and logging
    channel_id: Optional[int] = Field(default=None, description="Channel ID where command was executed")
    thread_id: Optional[int] = Field(default=None, description="Thread ID if in thread")
    message_id: Optional[int] = Field(default=None, description="Message ID of the command")
    interaction_id: Optional[str] = Field(default=None, description="Discord interaction ID")


class DiscordMessageResponseDTO(BaseDTO):
    """Discord message response"""

    message_type: MessageType = Field(..., description="Message type")
    content: str = Field(..., description="Message content")
    title: Optional[str] = Field(default=None, description="Message title (for embed)")
    is_embed: bool = Field(default=False, description="Use embed format")
    is_ephemeral: bool = Field(default=False, description="Show to user only")
    attachments: Optional[List[str]] = Field(
        default=None, description="File attachment paths"
    )


class ThreadInfoDTO(BaseDTO):
    """Thread information DTO"""

    thread_id: int = Field(..., description="Thread ID")
    thread_name: str = Field(..., description="Thread name")
    parent_channel_id: int = Field(..., description="Parent channel ID")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Thread creation time"
    )
    is_archived: bool = Field(default=False, description="Thread archive status")
    member_count: Optional[int] = Field(
        default=None, description="Thread member count"
    )

    # Additional metadata
    last_message_id: Optional[int] = Field(
        default=None, description="Last message ID in thread"
    )
    rate_limit_per_user: Optional[int] = Field(
        default=None, description="Thread rate limit (slowmode)"
    )