"""
태스크 생성 워크플로우 서비스
"""

from typing import Optional
from datetime import datetime, timedelta

from src.dto.discord.discord_dtos import (
    DiscordCommandRequestDTO,
    DiscordMessageResponseDTO,
)
from src.dto.common.enums import MessageType
from src.core.logger import get_logger
from src.core.database import save_notion_page
from src.core.config import settings
from .base_workflow_service import BaseWorkflowService

logger = get_logger("task_workflow")


class TaskWorkflowService(BaseWorkflowService):
    """태스크 생성 워크플로우 서비스"""

    async def create_task(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """태스크 생성 워크플로우"""
        try:
            # 1. 파라미터 검증
            validation_result = self._validate_request(request)
            if validation_result:
                return validation_result

            # 2. 태스크 생성
            title = request.parameters.get("title")
            priority = request.parameters.get("priority", "Medium")
            assignee = request.parameters.get("assignee", request.user.username)

            # 3. 마감일 설정 (기본값: 오늘)
            due_date = datetime.now().replace(
                hour=23, minute=59, second=59, microsecond=0
            )

            # 4. Notion 태스크 생성
            notion_result, page_url = await self._create_notion_page(
                title, priority, assignee, due_date
            )

            # 5. 데이터베이스 저장
            await self._save_to_database(
                notion_result, title, priority, assignee, request
            )

            # 6. 응답 생성
            return self._build_task_success_response(
                title, priority, assignee, due_date, page_url
            )

        except Exception as task_error:
            logger.error(f"❌ 태스크 생성 워크플로우 실패: {task_error}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 태스크 생성 실패: {str(task_error)}",
                is_ephemeral=True,
            )

    def _validate_request(
        self, request: DiscordCommandRequestDTO
    ) -> Optional[DiscordMessageResponseDTO]:
        """태스크 파라미터 유효성 검증"""
        title = request.parameters.get("title")

        if not title:
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 태스크 제목이 필요합니다.",
                is_ephemeral=True,
            )

        return None

    async def _create_notion_page(
        self, title: str, priority: str, assignee: str, due_date: datetime
    ) -> tuple:
        """Notion 태스크 생성"""
        with self._logger_manager.performance_logger("notion_task_creation"):
            notion_result = await self._notion_service.create_task_page(
                title=title, priority=priority, assignee=assignee, due_date=due_date
            )

            # 페이지 URL 추출
            page_url = notion_result.get("url", "https://notion.so")

            return notion_result, page_url

    async def _save_to_database(
        self,
        notion_result: dict,
        title: str,
        priority: str,
        assignee: str,
        request: DiscordCommandRequestDTO,
    ):
        """태스크 정보를 데이터베이스에 저장"""
        try:
            await save_notion_page(
                page_id=notion_result.get("id", ""),
                database_id=settings.task_db_id,
                page_type="task",
                title=title,
                created_by=str(request.user.user_id),
                metadata={
                    "priority": priority,
                    "assignee": assignee,
                    "discord_user": request.user.username,
                },
            )
        except Exception as save_error:
            logger.warning(f"⚠️ 페이지 정보 저장 실패 (계속 진행): {save_error}")

    def get_due_date_indicator(self, due_date: datetime) -> str:
        """마감일 지표와 설명 반환"""
        now = datetime.now()
        today = now.date()
        tomorrow = (now + timedelta(days=1)).date()
        due_date_only = due_date.date()

        if due_date_only == today:
            return "🔴 **오늘 마감**"
        elif due_date_only == tomorrow:
            return "🟡 **내일 마감**"
        elif due_date_only < today:
            days_overdue = (today - due_date_only).days
            return f"⚫ **{days_overdue}일 지연**"
        else:
            days_remaining = (due_date_only - today).days
            if days_remaining <= 3:
                return f"🟠 **{days_remaining}일 남음**"
            elif days_remaining <= 7:
                return f"🟢 **{days_remaining}일 남음**"
            else:
                return f"🔵 **{days_remaining}일 남음**"

    def _build_task_success_response(
        self,
        title: str,
        priority: str,
        assignee: str,
        due_date: datetime,
        page_url: str,
    ) -> DiscordMessageResponseDTO:
        """태스크 생성 성공 응답"""
        due_date_indicator = self.get_due_date_indicator(due_date)
        formatted_due_date = due_date.strftime("%Y-%m-%d %H:%M")

        response_content = (
            f"✅ **태스크 생성 완료**\n"
            f"📝 **제목**: `{title}`\n"
            f"📊 **우선순위**: `{priority}`\n"
            f"👤 **담당자**: `{assignee}`\n"
            f"📅 **마감일**: `{formatted_due_date}` {due_date_indicator}\n"
            f"🔗 **노션 링크**: {page_url}"
        )

        return DiscordMessageResponseDTO(
            message_type=MessageType.COMMAND_RESPONSE,
            title="태스크 생성 완료",
            content=response_content,
            is_embed=True,
            is_ephemeral=True,
        )
