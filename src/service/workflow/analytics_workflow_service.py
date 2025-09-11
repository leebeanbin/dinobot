"""
통계 분석 워크플로우 서비스
"""

from datetime import datetime

from src.dto.discord.discord_dtos import (
    DiscordCommandRequestDTO,
    DiscordMessageResponseDTO,
)
from src.dto.common.enums import MessageType
from src.core.logger import get_logger
from .base_workflow_service import BaseWorkflowService

logger = get_logger("analytics_workflow")


class AnalyticsWorkflowService(BaseWorkflowService):
    """통계 분석 워크플로우 서비스"""

    async def process_daily_stats(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """일일 통계 처리"""
        try:
            target_date_str = request.parameters.get("target_date")
            chart_enabled = request.parameters.get("chart", False)

            # 날짜 파싱
            if target_date_str:
                try:
                    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                except ValueError:
                    return DiscordMessageResponseDTO(
                        message_type=MessageType.ERROR_NOTIFICATION,
                        content="❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.",
                        is_ephemeral=True,
                    )
            else:
                target_date = datetime.now().date()

            analytics_service = self._get_analytics_service()

            if chart_enabled:
                # 차트 포함 통계
                result = await analytics_service.get_stats_with_chart(
                    analytics_service.get_daily_stats,
                    target_date,
                    stats_type="daily",
                )

                if result["has_chart"]:
                    # 스레드에 차트 이미지 전송
                    thread_info = (
                        await self._discord_service.get_or_create_daily_thread(
                            request.channel_id, title="통계 조회"
                        )
                    )

                    chart_path = result["chart_path"]
                    chart_message = f"📊 **{target_date} 일일 통계 차트**\n\n{result['formatted_message']}"

                    await self._discord_service.send_thread_message(
                        thread_info.thread_id, chart_message, file_path=chart_path
                    )

                    return DiscordMessageResponseDTO(
                        message_type=MessageType.COMMAND_RESPONSE,
                        content=f"📊 일일 통계 차트가 <#{thread_info.thread_id}>에 전송되었습니다!",
                        is_ephemeral=True,
                    )
                else:
                    return DiscordMessageResponseDTO(
                        message_type=MessageType.COMMAND_RESPONSE,
                        content=result["formatted_message"],
                        is_ephemeral=True,
                    )
            else:
                # 텍스트만
                result = await analytics_service.get_daily_stats(target_date)
                message = analytics_service.format_stats_message(result, "daily")

                return DiscordMessageResponseDTO(
                    message_type=MessageType.COMMAND_RESPONSE,
                    content=message,
                    is_ephemeral=True,
                )

        except Exception as e:
            logger.error(f"❌ 일일 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def process_weekly_stats(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """주간 통계 처리"""
        try:
            analytics_service = self._get_analytics_service()
            result = await analytics_service.get_weekly_stats()
            message = analytics_service.format_stats_message(result, "weekly")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )
        except Exception as e:
            logger.error(f"❌ 주간 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def process_monthly_stats(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """월간 통계 처리"""
        try:
            year = request.parameters.get("year", datetime.now().year)
            month = request.parameters.get("month", datetime.now().month)

            analytics_service = self._get_analytics_service()
            result = await analytics_service.get_monthly_stats(year, month)
            message = analytics_service.format_stats_message(result, "monthly")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )
        except Exception as e:
            logger.error(f"❌ 월간 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def process_user_stats(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """사용자 통계 처리"""
        try:
            user_id = str(request.user.user_id)
            days = request.parameters.get("days", 30)

            analytics_service = self._get_analytics_service()
            result = await analytics_service.get_user_productivity_stats(user_id, days)
            message = analytics_service.format_stats_message(result, "user")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )
        except Exception as e:
            logger.error(f"❌ 사용자 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def process_team_stats(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """팀 통계 처리"""
        try:
            days = request.parameters.get("days", 30)

            analytics_service = self._get_analytics_service()
            result = await analytics_service.get_team_comparison_stats(days)
            message = analytics_service.format_stats_message(result, "team")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )
        except Exception as e:
            logger.error(f"❌ 팀 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def process_trends_stats(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """트렌드 통계 처리"""
        try:
            days = request.parameters.get("days", 14)

            analytics_service = self._get_analytics_service()
            result = await analytics_service.get_activity_trends_stats(days)
            message = analytics_service.format_stats_message(result, "trends")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )
        except Exception as e:
            logger.error(f"❌ 트렌드 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def process_task_stats(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """태스크 완료 통계 처리"""
        try:
            days = request.parameters.get("days", 30)

            analytics_service = self._get_analytics_service()
            result = await analytics_service.get_task_completion_stats(days)
            message = analytics_service.format_stats_message(result, "task_completion")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )
        except Exception as e:
            logger.error(f"❌ 태스크 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    def _get_analytics_service(self):
        """Analytics 서비스 인스턴스 반환"""
        # 부모 클래스에서 서비스 매니저를 통해 접근
        # 현재는 직접 접근하지만 향후 service manager 통합 예정
        from src.service.analytics import analytics_service

        return analytics_service
