"""
검색 워크플로우 서비스
"""

from src.dto.discord.discord_dtos import (
    DiscordCommandRequestDTO,
    DiscordMessageResponseDTO,
)
from src.dto.common.enums import MessageType
from src.core.logger import get_logger
from .base_workflow_service import BaseWorkflowService

logger = get_logger("search_workflow")


class SearchWorkflowService(BaseWorkflowService):
    """검색 워크플로우 서비스"""

    async def process_search(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """검색 요청 처리"""
        try:
            query = request.parameters.get("query", "").strip()
            page_type = request.parameters.get("page_type")
            user_filter = request.parameters.get("user_filter")
            days = request.parameters.get("days", 90)

            # 검색어 길이 검증
            if len(query) < 2:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 검색어는 2글자 이상 입력해주세요.",
                    is_ephemeral=True,
                )

            # 검색 서비스를 통한 검색 실행
            search_service = self._get_search_service()
            result = await search_service.search_pages(
                query=query,
                page_type=page_type or "both",
                user_filter=user_filter,
                days=days,
            )

            if result.get("success"):
                search_results = result.get("results", [])
                message = search_service.format_search_results(search_results)
            else:
                raise Exception(f"검색 실패: {result.get('error')}")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )

        except Exception as e:
            logger.error(f"❌ 검색 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 검색 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    def _get_search_service(self):
        """Search 서비스 인스턴스 반환"""
        from src.service.search_service import search_service

        return search_service
