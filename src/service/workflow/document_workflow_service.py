"""
문서 생성 워크플로우 서비스
"""

from typing import Optional

from src.dto.discord.discord_dtos import (
    DiscordCommandRequestDTO,
    DiscordMessageResponseDTO,
)
from src.dto.common.enums import MessageType
from src.core.logger import get_logger
from src.core.database import save_notion_page
from src.core.config import settings
from .base_workflow_service import BaseWorkflowService

logger = get_logger("document_workflow")


class DocumentWorkflowService(BaseWorkflowService):
    """문서 생성 워크플로우 서비스"""

    async def create_document(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """문서 생성 워크플로우"""
        try:
            # 1. 파라미터 검증
            validation_result = self._validate_request(request)
            if validation_result:
                return validation_result

            # 2. 문서 생성
            title = request.parameters.get("title") or request.parameters.get("name")
            from src.core.constants import DEFAULT_DOCUMENT_TYPE
            doc_type = request.parameters.get("doc_type", DEFAULT_DOCUMENT_TYPE)
            unique_title = self._generate_unique_title(title)

            # 3. Notion 문서 생성
            notion_result, page_url = await self._create_notion_page(
                unique_title, doc_type
            )

            # 4. 데이터베이스 저장
            await self._save_to_database(notion_result, unique_title, doc_type, request)

            # 5. 스레드 안내 메시지 전송
            await self._send_thread_notification(request, unique_title, page_url)

            # 6. 응답 생성
            return self._build_document_success_response(unique_title)

        except Exception as document_error:
            logger.error(f"❌ 문서 생성 워크플로우 실패: {document_error}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 문서 생성 실패: {str(document_error)}",
                is_ephemeral=True,
            )

    def _validate_request(
        self, request: DiscordCommandRequestDTO
    ) -> Optional[DiscordMessageResponseDTO]:
        """문서 파라미터 유효성 검증"""
        title = request.parameters.get("title") or request.parameters.get("name")
        from src.core.constants import DEFAULT_DOCUMENT_TYPE, VALID_DOCUMENT_TYPES, config_helper
        doc_type = request.parameters.get("doc_type", DEFAULT_DOCUMENT_TYPE)

        if not title:
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=config_helper.format_error_message("missing_title"),
                is_ephemeral=True,
            )

        # 문서 타입 유효성 검증
        valid_doc_types = VALID_DOCUMENT_TYPES
        if doc_type not in valid_doc_types:
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 올바른 문서 타입을 선택해주세요.\n"
                f"잘못된 타입: {doc_type}\n"
                f"사용 가능한 값: {', '.join(valid_doc_types)}",
                is_ephemeral=True,
            )

        return None

    async def _create_notion_page(self, unique_title: str, doc_type: str) -> tuple:
        """Notion 문서 생성"""
        with self._logger_manager.performance_logger("notion_document_creation"):
            notion_result = await self._notion_service.create_document_page(
                title=unique_title, doc_type=doc_type
            )

            # 페이지 URL 추출
            page_url = notion_result.get("url", "https://notion.so")

            return notion_result, page_url

    async def _save_to_database(
        self,
        notion_result: dict,
        unique_title: str,
        doc_type: str,
        request: DiscordCommandRequestDTO,
    ):
        """문서 정보를 데이터베이스에 저장"""
        try:
            await save_notion_page(
                page_id=notion_result.get("id", ""),
                database_id=settings.board_db_id,
                page_type="document",
                title=unique_title,
                created_by=str(request.user.user_id),
                metadata={
                    "doc_type": doc_type,
                    "discord_user": request.user.username,
                },
            )
        except Exception as save_error:
            logger.warning(f"⚠️ 페이지 정보 저장 실패 (계속 진행): {save_error}")

    async def _send_thread_notification(
        self, request: DiscordCommandRequestDTO, unique_title: str, page_url: str
    ):
        """문서 스레드 안내 메시지 전송"""
        channel_id = request.guild.channel_id or settings.default_discord_channel_id
        if channel_id:
            try:
                thread_info = await self._discord_service.get_or_create_daily_thread(
                    channel_id, title=unique_title
                )

                document_notification = (
                    f"📄 **새 문서가 생성되었습니다!**\n"
                    f"📝 **제목**: {unique_title}\n"
                    f"📂 **유형**: {request.parameters.get('doc_type', '개발 문서')}\n"
                    f"👤 **작성자**: {request.user.username}\n"
                    f"🔗 **노션 링크**: {page_url}\n\n"
                    f"💡 이제 해당 문서에 내용을 작성해보세요!"
                )

                await self._discord_service.send_thread_message(
                    thread_info.thread_id, document_notification
                )
            except Exception as thread_error:
                logger.warning(f"⚠️ 스레드 메시지 전송 실패: {thread_error}")

    def _build_document_success_response(
        self, unique_title: str
    ) -> DiscordMessageResponseDTO:
        """문서 생성 성공 응답"""
        return DiscordMessageResponseDTO(
            message_type=MessageType.COMMAND_RESPONSE,
            title="문서 생성 완료",
            content=f"📄 문서 '{unique_title}'이 생성되었습니다!",
            is_embed=True,
            is_ephemeral=True,
        )
