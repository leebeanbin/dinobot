"""
메트릭 관련 DTO classes
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import Field

from .base_dto import BaseDTO


class CommandExecutionMetricDTO(BaseDTO):
    """Command execution metrics"""

    command_type: str = Field(..., description="Command type")
    user_id: str = Field(..., description="User ID")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    success: bool = Field(..., description="Execution success")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")
    
    # Additional context
    guild_id: Optional[str] = Field(default=None, description="Guild ID")
    channel_id: Optional[str] = Field(default=None, description="Channel ID")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Command parameters")


class APICallMetricDTO(BaseDTO):
    """API call performance metrics"""

    api_service: str = Field(..., description="API service name (notion, discord)")
    endpoint: str = Field(..., description="API endpoint")
    method: str = Field(..., description="HTTP method")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    status_code: int = Field(..., description="HTTP status code")
    success: bool = Field(..., description="Call success")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")
    
    # Additional details
    request_size_bytes: Optional[int] = Field(default=None, description="Request size")
    response_size_bytes: Optional[int] = Field(default=None, description="Response size")


class CachePerformanceMetricDTO(BaseDTO):
    """Cache performance metrics"""

    cache_type: str = Field(..., description="Cache type")
    operation: str = Field(..., description="Cache operation (hit/miss/set)")
    key: str = Field(..., description="Cache key")
    execution_time_ms: float = Field(..., description="Operation time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")