"""
Webhook DTOs Package
웹훅 관련 데이터 전송 객체들
"""

from .webhook_dtos import (
    NotionWebhookRequestDTO,
    WebhookProcessResultDTO
)

__all__ = [
    "NotionWebhookRequestDTO",
    "WebhookProcessResultDTO"
]