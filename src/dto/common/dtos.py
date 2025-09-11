"""
Data Transfer Objects (DTOs) for DinoBot
중앙집중식 DTO 접근점을 제공합니다.

이 모듈은 개별 DTO 컴포넌트들을 편리하게 import할 수 있도록
중앙집중식 접근점을 제공합니다.
"""

# 모든 데이터 모델들을 import
# data_models.py가 없으므로 개별적으로 import
from .base_dto import BaseDTO
from .enums import CommandType, MessageType
from .system_dtos import SystemStatusDTO, ServiceStatusDTO, MongoDBStatusDTO
from .metrics_dtos import (
    CommandExecutionMetricDTO,
    APICallMetricDTO,
    CachePerformanceMetricDTO,
)

# Discord DTOs import
from ..discord.discord_dtos import DiscordMessageResponseDTO

# 기존 코드와의 호환성을 위한 추가 import들
# (향후 리팩터링에서 제거 예정)
from datetime import datetime
from typing import Optional, List, Dict, Any, Union


# DTOConverter는 별도 파일로 분리 예정
class DTOConverter:
    """DTO conversion utilities (Legacy - to be moved)"""

    @staticmethod
    def from_notion_page(notion_page: dict) -> Dict[str, Any]:
        """Convert Notion page to standardized format"""
        return {
            "page_id": notion_page.get("id", ""),
            "title": notion_page.get("properties", {})
            .get("title", {})
            .get("title", [{}])[0]
            .get("plain_text", ""),
            "created_time": notion_page.get("created_time"),
            "last_edited_time": notion_page.get("last_edited_time"),
            "url": notion_page.get("url", ""),
        }

    @staticmethod
    def to_discord_embed(response: DiscordMessageResponseDTO) -> Dict[str, Any]:
        """Convert DTO to Discord embed format"""
        embed = {
            "description": response.content,
            "color": (
                0x00FF00
                if response.message_type == MessageType.SUCCESS_NOTIFICATION
                else 0xFF0000
            ),
        }

        if response.title:
            embed["title"] = response.title

        return embed

    @staticmethod
    def mongodb_doc_to_thread_dto(mongodb_doc: dict) -> Dict[str, Any]:
        """Convert MongoDB document to thread DTO format"""
        return {
            "channel_id": mongodb_doc.get("channel_id"),
            "thread_name": mongodb_doc.get("thread_name"),
            "thread_id": mongodb_doc.get("thread_id"),
            "created_at": mongodb_doc.get("created_at"),
            "last_used": mongodb_doc.get("last_used"),
            "use_count": mongodb_doc.get("use_count", 0),
        }
