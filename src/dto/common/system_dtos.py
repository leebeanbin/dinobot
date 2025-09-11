"""
시스템 상태 관련 DTO classes
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import Field

from .base_dto import BaseDTO


class ServiceStatusDTO(BaseDTO):
    """Individual service status"""

    service_name: str = Field(..., description="Service name")
    is_healthy: bool = Field(..., description="Service health status")
    last_check: datetime = Field(
        default_factory=datetime.now, description="Last health check"
    )
    response_time_ms: Optional[float] = Field(
        default=None, description="Response time in milliseconds"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if unhealthy"
    )


class MongoDBStatusDTO(BaseDTO):
    """MongoDB connection status"""

    is_connected: bool = Field(..., description="Connection status")
    database_name: str = Field(..., description="Database name")
    collections_count: Optional[int] = Field(
        default=None, description="Number of collections"
    )


class SystemStatusDTO(BaseDTO):
    """Overall system status"""

    status: str = Field(..., description="Overall status (healthy/degraded/unhealthy)")
    uptime_seconds: int = Field(..., description="System uptime in seconds")
    services: Dict[str, ServiceStatusDTO] = Field(
        default_factory=dict, description="Individual service statuses"
    )
    mongodb: Optional[MongoDBStatusDTO] = Field(
        default=None, description="MongoDB status"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Status last updated"
    )
    
    # Performance metrics
    memory_usage_mb: Optional[float] = Field(
        default=None, description="Memory usage in MB"
    )
    cpu_usage_percent: Optional[float] = Field(
        default=None, description="CPU usage percentage"
    )