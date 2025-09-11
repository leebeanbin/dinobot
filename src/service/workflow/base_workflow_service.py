"""
기본 워크플로우 서비스 추상 클래스
"""

from abc import ABC, abstractmethod
from datetime import datetime


class BaseWorkflowService(ABC):
    """기본 워크플로우 서비스 추상 클래스"""
    
    def __init__(self, notion_service, discord_service, logger_manager):
        self._notion_service = notion_service
        self._discord_service = discord_service
        self._logger_manager = logger_manager
    
    def _generate_unique_title(self, base_title: str) -> str:
        """고유한 제목 생성 (시간 구분자 포함)"""
        now = datetime.now()
        time_suffix = now.strftime("%m%d_%H%M")
        return f"{base_title}_{time_suffix}"