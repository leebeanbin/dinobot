"""
Service interfaces defining contracts for all services.

This module contains interface definitions that establish contracts
for service implementations, enabling dependency injection and
maintaining loose coupling between components.
"""

from .interfaces import INotionService, IDiscordService, IServiceManager

__all__ = [
    # Core Service Interfaces
    "INotionService",
    "IDiscordService",
    "IServiceManager",
]
