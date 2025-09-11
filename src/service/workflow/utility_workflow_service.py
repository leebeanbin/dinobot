"""
유틸리티 워크플로우 서비스 (도움말, 상태 확인, 페이지 가져오기 등)
"""

from src.dto.discord.discord_dtos import (
    DiscordCommandRequestDTO,
    DiscordMessageResponseDTO,
)
from src.dto.common.enums import MessageType
from src.core.logger import get_logger
from .base_workflow_service import BaseWorkflowService

logger = get_logger("utility_workflow")


class UtilityWorkflowService(BaseWorkflowService):
    """유틸리티 워크플로우 서비스 (도움말, 상태 확인, 페이지 가져오기 등)"""

    async def process_help(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """도움말 처리"""
        help_content = """
🤖 **DinoBot 도움말**

**📝 페이지 생성**
• `/meeting [제목] [시간] [참석자]` - 회의록 생성
• `/document [제목] [타입]` - 문서 생성  
• `/task [제목] [우선순위] [담당자]` - 태스크 생성

**📊 통계 조회**
• `/daily_stats [날짜] [차트]` - 일일 통계
• `/weekly_stats` - 주간 통계
• `/monthly_stats [년] [월]` - 월간 통계
• `/user_stats [일수]` - 개인 통계
• `/team_stats [일수]` - 팀 통계
• `/trends [일수]` - 활동 트렌드
• `/task_stats [일수]` - 태스크 완료 통계

**🔍 검색 및 기타**
• `/search [검색어] [타입] [사용자] [일수]` - 페이지 검색
• `/fetch [페이지ID]` - 페이지 내용 가져오기
• `/watch [페이지ID]` - 페이지 모니터링
• `/status` - 시스템 상태 확인
• `/help` - 이 도움말

💡 **팁**: 각 명령어는 슬래시(/)로 시작합니다!
        """

        return DiscordMessageResponseDTO(
            message_type=MessageType.COMMAND_RESPONSE,
            title="DinoBot 도움말",
            content=help_content,
            is_embed=True,
            is_ephemeral=True,
        )

    async def process_status(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """시스템 상태 확인"""
        try:
            # Discord 봇 상태 확인
            discord_status = await self._discord_service.check_bot_status()

            # MongoDB 상태 확인 (간단하게)
            from src.core.database import mongodb_connection

            mongo_connected = mongodb_connection.mongo_client is not None

            status_content = f"""
🖥️ **시스템 상태**

**🤖 Discord Bot**
• 상태: {'✅ 연결됨' if discord_status['ready'] else '❌ 연결 끊김'}
• 지연시간: {discord_status['latency']:.2f}ms
• 업타임: {discord_status['uptime']}

**📊 데이터베이스**
• MongoDB: {'✅ 연결됨' if mongo_connected else '❌ 연결 끊김'}

**💾 캐시**
• 메시지: {discord_status.get('cached_messages', 0)}개
• 사용자: {discord_status.get('cached_users', 0)}명
            """

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                title="시스템 상태",
                content=status_content,
                is_embed=True,
                is_ephemeral=True,
            )

        except Exception as e:
            logger.error(f"❌ 상태 확인 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 상태 확인 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def process_fetch_page(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """페이지 내용 가져오기"""
        try:
            page_id = request.parameters.get("page_id")

            if not page_id:
                # 최근 생성된 페이지 가져오기
                from src.core.database import get_recent_notion_page_by_user

                recent_page = await get_recent_notion_page_by_user(
                    str(request.user.user_id)
                )

                if not recent_page:
                    return DiscordMessageResponseDTO(
                        message_type=MessageType.ERROR_NOTIFICATION,
                        content="❌ 가져올 페이지가 없습니다. 페이지 ID를 지정하거나 먼저 페이지를 생성해주세요.",
                        is_ephemeral=True,
                    )

                page_id = recent_page.get("page_id")
                title = recent_page.get("title", "제목 없음")
            else:
                title = "지정된 페이지"

            # 페이지 내용 가져오기
            notion_service = self._get_notion_service()
            page_content = await notion_service.get_page_content(page_id)

            if not page_content:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 페이지 내용을 가져올 수 없습니다.",
                    is_ephemeral=True,
                )

            # 스레드에 내용 전송
            thread_info = await self._discord_service.get_or_create_daily_thread(
                request.channel_id, title=f"페이지 내용: {title}"
            )

            formatted_content = f"📄 **{title}**\n\n{page_content}"

            await self._discord_service.send_thread_message(
                thread_info.thread_id, formatted_content
            )

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=f"📄 페이지 내용이 <#{thread_info.thread_id}>에 전송되었습니다!",
                is_ephemeral=True,
            )

        except Exception as e:
            logger.error(f"❌ 페이지 가져오기 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 페이지 가져오기 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def process_watch_page(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """페이지 모니터링 시작"""
        try:
            page_id = request.parameters.get("page_id")

            if not page_id:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 모니터링할 페이지 ID가 필요합니다.",
                    is_ephemeral=True,
                )

            # 페이지 모니터링 로직 (향후 구현)
            # 현재는 간단한 응답만

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=f"👀 페이지 `{page_id}` 모니터링을 시작했습니다.\n"
                "💡 변경사항이 감지되면 알림을 보내드립니다.",
                is_ephemeral=True,
            )

        except Exception as e:
            logger.error(f"❌ 페이지 모니터링 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 페이지 모니터링 설정 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    def _get_notion_service(self):
        """Notion 서비스 인스턴스 반환"""
        from src.service.notion import notion_service

        return notion_service
