"""
Core module providing fundamental system components.

This module contains the essential infrastructure components:
- Configuration management
- Database connections and operations  
- Logging system
- Service lifecycle management
"""

from .config import Settings, settings
from .database import MongoDBConnectionManager, mongodb_connection
from .logger import initialize_logging_system, get_logger, logger_manager
from .service_manager import ServiceManager

__all__ = [
    # Configuration
    'Settings',
    'settings',
    
    # Database
    'MongoDBConnectionManager',
    'mongodb_connection',
    
    # Logging
    'initialize_logging_system',
    'get_logger',
    'logger_manager',
    
    # Service Management
    'ServiceManager'
]