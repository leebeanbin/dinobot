"""
회의록 생성 워크플로우 서비스
"""

from typing import Optional
from datetime import datetime, timedelta

from src.dto.discord.discord_dtos import (
    DiscordCommandRequestDTO,
    DiscordMessageResponseDTO,
)
from src.dto.common.enums import MessageType
from src.dto.notion.request_dtos import MeetingCreateRequestDTO
from src.core.logger import get_logger
from src.core.database import save_notion_page
from src.core.config import settings
from .base_workflow_service import BaseWorkflowService

logger = get_logger("meeting_workflow")


class MeetingWorkflowService(BaseWorkflowService):
    """회의록 생성 워크플로우 서비스"""

    async def create_meeting(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """회의록 생성 전체 워크플로우"""
        try:
            # 1. 필수 파라미터 검증
            validation_result = self._validate_request(request)
            if validation_result:
                return validation_result

            # 2. 회의록 생성
            meeting_request = self._prepare_meeting_data(request)
            notion_result, page_url = await self._create_notion_page(meeting_request)

            # 3. 데이터베이스 저장
            await self._save_to_database(notion_result, meeting_request, request)

            # 4. Discord 이벤트 생성
            discord_event_created = await self._create_discord_event(
                request, meeting_request, page_url
            )

            # 5. 스레드 안내 메시지 전송
            await self._send_thread_notification(
                request, meeting_request, page_url, notion_result
            )

            # 6. 응답 생성
            return self._build_success_response(
                request, meeting_request, page_url, discord_event_created
            )

        except Exception as meeting_error:
            logger.error(f"❌ 회의록 생성 워크플로우 실패: {meeting_error}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 회의록 생성 실패: {str(meeting_error)}",
                is_ephemeral=True,
            )

    def _validate_request(
        self, request: DiscordCommandRequestDTO
    ) -> Optional[DiscordMessageResponseDTO]:
        """회의 파라미터 유효성 검증"""
        title = request.parameters.get("title") or request.parameters.get("name")
        meeting_date = request.parameters.get("meeting_date")
        participants = request.parameters.get("participants", [])

        if not title:
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 회의록 제목이 필요합니다. (title 또는 name 파라미터 필요)",
                is_ephemeral=True,
            )

        if not meeting_date:
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 회의 시간이 필요합니다.\n"
                "📝 사용 예시:\n"
                "• 오늘 16:30\n"
                "• 내일 14:00\n"
                "• 2024-12-25 14:00\n"
                "• 12/25 14:00\n"
                "• 16:30 (오늘)",
                is_ephemeral=True,
            )

        if not participants:
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content='❌ 참석자(participants)가 필요합니다. 예: 소현,정빈 또는 ["소현", "정빈"]',
                is_ephemeral=True,
            )

        # 참석자 리스트 정규화 및 검증
        if isinstance(participants, str):
            participants = [p.strip() for p in participants.split(",")]

        from src.core.constants import VALID_PERSONS
        valid_persons = VALID_PERSONS
        invalid_participants = [p for p in participants if p not in valid_persons]
        if invalid_participants:
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 올바른 참석자를 선택해주세요.\n"
                f"잘못된 참석자: {', '.join(invalid_participants)}\n"
                f"사용 가능한 값: {', '.join(valid_persons)}",
                is_ephemeral=True,
            )

        return None

    def _prepare_meeting_data(
        self, request: DiscordCommandRequestDTO
    ) -> MeetingCreateRequestDTO:
        """회의록 요청 DTO 구성"""
        title = request.parameters.get("title") or request.parameters.get("name")
        participants = request.parameters.get("participants", [])

        if isinstance(participants, str):
            participants = [p.strip() for p in participants.split(",")]

        unique_title = self._generate_unique_title(title)

        return MeetingCreateRequestDTO(
            title=unique_title,
            meeting_type=request.parameters.get("meeting_type", "정기회의"),
            attendees=participants,
        )

    async def _create_notion_page(
        self, meeting_request: MeetingCreateRequestDTO
    ) -> tuple:
        """Notion 회의록 생성"""
        with self._logger_manager.performance_logger("notion_meeting_creation"):
            notion_result = await self._notion_service.create_meeting_page(
                title=meeting_request.title,
                participants=meeting_request.attendees,
            )

            # 페이지 URL 추출
            page_url = notion_result.get("url", "https://notion.so")

            return notion_result, page_url

    async def _save_to_database(
        self,
        notion_result: dict,
        meeting_request: MeetingCreateRequestDTO,
        request: DiscordCommandRequestDTO,
    ):
        """회의록 정보를 데이터베이스에 저장"""
        try:
            await save_notion_page(
                page_id=notion_result.get("id", ""),
                database_id=settings.board_db_id,
                page_type="meeting",
                title=meeting_request.title,
                created_by=str(request.user.user_id),
                metadata={
                    "meeting_type": meeting_request.meeting_type,
                    "attendees": meeting_request.attendees,
                    "discord_user": request.user.username,
                },
            )
        except Exception as save_error:
            logger.warning(f"⚠️ 페이지 정보 저장 실패 (계속 진행): {save_error}")

    async def _create_discord_event(
        self,
        request: DiscordCommandRequestDTO,
        meeting_request: MeetingCreateRequestDTO,
        page_url: str,
    ) -> bool:
        """Discord 이벤트 생성"""
        meeting_date_str = request.parameters.get("meeting_date")
        if not meeting_date_str:
            return False

        try:
            meeting_datetime = self._parse_meeting_date(meeting_date_str)

            if meeting_datetime:
                event_title = f"📝 {meeting_request.title}"
                event_description = (
                    f"회의 유형: {meeting_request.meeting_type}\n"
                    f"참석자: {', '.join(meeting_request.attendees)}\n\n"
                    f"노션 페이지: {page_url}"
                )

                return await self._discord_service.create_discord_event(
                    title=event_title,
                    description=event_description,
                    start_time=meeting_datetime,
                    duration_hours=1,
                    voice_channel_name="회의실",
                )
            else:
                logger.warning(f"⚠️ 날짜 형식을 인식할 수 없습니다: {meeting_date_str}")
                return False

        except Exception as event_error:
            logger.warning(f"⚠️ Discord 이벤트 생성 실패: {event_error}")
            return False

    def _parse_meeting_date(self, meeting_date_str: str) -> Optional[datetime]:
        """회의 날짜 문자열을 datetime 객체로 변환"""
        meeting_datetime = None
        now = datetime.now()

        # 1. 상대적 날짜 표현 처리
        if "오늘" in meeting_date_str:
            time_part = meeting_date_str.replace("오늘", "").strip()
            if time_part:
                try:
                    time_obj = datetime.strptime(time_part, "%H:%M").time()
                    meeting_datetime = now.replace(
                        hour=time_obj.hour,
                        minute=time_obj.minute,
                        second=0,
                        microsecond=0,
                    )
                except ValueError:
                    meeting_datetime = now.replace(
                        hour=14, minute=0, second=0, microsecond=0
                    )
            else:
                meeting_datetime = now.replace(
                    hour=14, minute=0, second=0, microsecond=0
                )

        elif "내일" in meeting_date_str:
            time_part = meeting_date_str.replace("내일", "").strip()
            tomorrow = now + timedelta(days=1)
            if time_part:
                try:
                    time_obj = datetime.strptime(time_part, "%H:%M").time()
                    meeting_datetime = tomorrow.replace(
                        hour=time_obj.hour,
                        minute=time_obj.minute,
                        second=0,
                        microsecond=0,
                    )
                except ValueError:
                    meeting_datetime = tomorrow.replace(
                        hour=14, minute=0, second=0, microsecond=0
                    )
            else:
                meeting_datetime = tomorrow.replace(
                    hour=14, minute=0, second=0, microsecond=0
                )

        # 2. 절대적 날짜 형식 처리
        else:
            date_formats = [
                "%Y-%m-%d %H:%M",  # 2024-12-25 14:00
                "%Y/%m/%d %H:%M",  # 2024/12/25 14:00
                "%m/%d %H:%M",  # 12/25 14:00 (현재 년도)
                "%Y-%m-%d",  # 2024-12-25 (기본 시간: 14:00)
                "%Y/%m/%d",  # 2024/12/25 (기본 시간: 14:00)
                "%m/%d",  # 12/25 (현재 년도, 기본 시간: 14:00)
                "%H:%M",  # 16:30 (오늘)
            ]

            for fmt in date_formats:
                try:
                    if fmt == "%H:%M":
                        # 시간만 있는 경우 오늘 날짜에 적용
                        time_obj = datetime.strptime(meeting_date_str, fmt).time()
                        meeting_datetime = now.replace(
                            hour=time_obj.hour,
                            minute=time_obj.minute,
                            second=0,
                            microsecond=0,
                        )
                    else:
                        parsed_date = datetime.strptime(meeting_date_str, fmt)
                        # 년도가 없는 형식인 경우 현재 년도 사용
                        if fmt in ["%m/%d %H:%M", "%m/%d"]:
                            parsed_date = parsed_date.replace(year=now.year)
                        # 시간이 없는 형식인 경우 14:00으로 기본 설정
                        if fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m/%d"]:
                            parsed_date = parsed_date.replace(hour=14, minute=0)
                        meeting_datetime = parsed_date
                    break
                except ValueError:
                    continue

        return meeting_datetime

    async def _send_thread_notification(
        self,
        request: DiscordCommandRequestDTO,
        meeting_request: MeetingCreateRequestDTO,
        page_url: str,
        notion_result: dict,
    ):
        """스레드에 안내 메시지 전송"""
        channel_id = request.guild.channel_id or settings.default_discord_channel_id
        if channel_id:
            try:
                thread_info = await self._discord_service.get_or_create_daily_thread(
                    channel_id, title=meeting_request.title
                )
                guide_message = self._build_guide_message(
                    meeting_request.title, page_url, notion_result.get("id")
                )
                await self._discord_service.send_thread_message(
                    thread_info.thread_id, guide_message
                )
            except Exception as thread_error:
                logger.warning(f"⚠️ 스레드 메시지 전송 실패: {thread_error}")

    def _build_guide_message(self, title: str, page_url: str, page_id: str) -> str:
        """회의 가이드 메시지 생성"""
        return f"""
📝 **{title}** 회의가 생성되었습니다!

🔗 **노션 페이지**: {page_url}

📋 **회의 진행 가이드**:
1. 회의 전: 안건 및 자료 준비
2. 회의 중: 주요 논의사항 기록
3. 회의 후: 결정사항 및 액션아이템 정리

💡 **팁**: 노션 페이지에서 실시간으로 회의록을 작성하세요!
        """

    def _build_success_response(
        self,
        request: DiscordCommandRequestDTO,
        meeting_request: MeetingCreateRequestDTO,
        page_url: str,
        discord_event_created: bool,
    ) -> DiscordMessageResponseDTO:
        """성공 응답 생성"""
        title = request.parameters.get("title") or request.parameters.get("name")
        meeting_date_str = request.parameters.get("meeting_date")

        response_content = (
            f"✅ **회의록 생성 완료**\n"
            f"📝 **제목**: `{title}` → `{meeting_request.title}`\n"
            f"🏷️ **유형**: `{meeting_request.meeting_type}`\n"
            f"🔗 **노션 링크**: {page_url}\n\n"
            f"📝 당일 스레드에 작성 가이드를 전송했습니다."
        )

        if meeting_request.attendees:
            participants_string = ", ".join(meeting_request.attendees)
            response_content += f"\n👥 **참석자**: `{participants_string}`"

        # Discord 이벤트 생성 결과 추가
        if meeting_date_str:
            response_content += f"\n🎯 **회의 일정**: `{meeting_date_str}`"
            if discord_event_created:
                response_content += (
                    f"\n📅 Discord 이벤트가 '내 회의실' 음성 채널에 생성되었습니다."
                )
            else:
                response_content += (
                    f"\n⚠️ Discord 이벤트 생성에 실패했습니다. (날짜 형식 확인 필요)"
                )

        return DiscordMessageResponseDTO(
            message_type=MessageType.COMMAND_RESPONSE,
            title="회의록 생성 완료",
            content=response_content,
            is_embed=True,
            is_ephemeral=True,
        )
