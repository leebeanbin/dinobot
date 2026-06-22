"""
디스코드 서비스 모듈 - 디스코드 bot과의 모든 상호작용 담당
- 슬래시 명령어 처리
- 스레드 관리 및 메시지 전송
- 사용자 인터랙션 처리
- MongoDB를 활용한 캐싱 및 메트릭 수집
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
import discord
from discord import app_commands
from discord.ext import commands

from src.core.config import settings
from src.core.logger import get_logger, logger_manager
from src.core.database import thread_cache_manager, metrics_collector
from src.core.exceptions import (
    DiscordAPIException,
    safe_execution,
    global_exception_handler,
)
from src.core.decorators import track_discord_command
from src.core.metrics import get_metrics_collector

# Analytics and search services are now managed by ServiceManager
# from .analytics import analytics_service
# from .search_service import search_service
from src.interface.service.interfaces import IDiscordService
from src.dto.discord.discord_dtos import (
    DiscordCommandRequestDTO,
    DiscordMessageResponseDTO,
    ThreadInfoDTO,
    DiscordUserDTO,
    DiscordGuildDTO,
)
from src.dto.common.enums import CommandType, MessageType
from src.dto.common.dtos import DTOConverter

# Module logger
logger = get_logger("services.discord")


class DiscordService(IDiscordService):
    """
    디스코드 bot 기능을 구현하는 서비스 클래스

    주요 기능:
    - Discord.py 기반 bot 관리
    - 슬래시 명령어 등록 및 처리
    - 스레드 자동 생성 및 관리
    - MongoDB 연동 캐싱
    - 성능 메트릭 수집
    """

    def __init__(self):
        # Discord bot 설정
        intents = discord.Intents.default()
        # Message Content Intent 활성화 (Discord Developer Portal에서도 활성화 필요)
        intents.message_content = True

        self.bot = commands.Bot(
            command_prefix="!",
            intents=intents,
            description="DinoBot - 노션-디스코드 통합 bot",
        )

        # Internal state management
        self.is_bot_ready = False
        self.target_guild = None
        self.business_logic_callback = None  # Business logic callback handler

        # Register bot event handlers
        self._register_event_handlers()

        # Discord service initialization complete (로그 제거)

    def _register_event_handlers(self):
        """디스코드 bot 이벤트 핸들러들을 등록"""

        @self.bot.event
        async def on_ready():
            """bot이 Discord에 연결되었을 때 실행"""
            logger.info(f"🚀 Discord bot 연결 완료: {self.bot.user}")
            logger.info(f"📊 연결된 서버 수: {len(self.bot.guilds)}개")

            # Configure target guild object
            self.target_guild = discord.Object(id=int(settings.discord_guild_id))

            # 슬래시 명령어 동기화
            try:
                sync_result = await self.bot.tree.sync(guild=self.target_guild)
                logger.info(f"⚡ 슬래시 명령어 동기화 완료: {len(sync_result)}개")
            except Exception as sync_error:
                logger.error(f"❌ 슬래시 명령어 동기화 실패: {sync_error}")

            self.is_bot_ready = True

        @self.bot.event
        async def on_disconnect():
            """bot이 Discord에서 연결이 끊겼을 때 실행"""
            logger.warning("🔌 Discord bot 연결 끊김")
            self.is_bot_ready = False

        @self.bot.event
        async def on_resumed():
            """bot이 Discord에 재연결되었을 때 실행"""
            logger.info("🔄 Discord bot 재연결 완료")
            self.is_bot_ready = True

        @self.bot.event
        async def on_application_command_error(
            interaction: discord.Interaction, error: Exception
        ):
            """슬래시 명령어 에러 발생 시 글로벌 핸들러로 전달"""
            await global_exception_handler.handle_discord_command_exception(
                interaction, error
            )

    async def start_bot(self) -> bool:
        """
        Start Discord bot and register slash commands

        Returns:
            bool: Success status
        """
        try:
            # Register slash commands
            await self._register_slash_commands()

            # Bot login (background execution)
            # Discord bot login starting (로그 제거)
            await self.bot.login(settings.discord_token)

            # Discord bot startup complete (로그 제거)
            return True

        except Exception as start_error:
            logger.error(f"❌ Discord bot startup failed: {start_error}")
            raise DiscordAPIException(
                "Discord bot startup failed", original_exception=start_error
            )

    async def stop_bot(self) -> bool:
        """
        디스코드 bot을 안전하게 종료

        Returns:
            bool: 종료 성공 여부
        """
        try:
            if self.bot.is_closed():
                logger.info("📴 Discord bot 이미 종료됨")
                return True

            await self.bot.close()
            self.is_bot_ready = False
            logger.info("👋 Discord bot 종료 완료")
            return True

        except Exception as shutdown_error:
            logger.error(f"❌ Discord bot 종료 실패: {shutdown_error}")
            return False

    def set_command_callback(self, callback_function):
        """
        명령어 처리를 위한 비즈니스 로직 콜백 설정

        Args:
            callback_function: 명령어 처리 함수 (async def callback(요청_DTO) -> 응답_DTO)
        """
        self.command_callback = callback_function
        logger.debug("📞 명령어 처리 콜백 설정 완료")

    async def _register_slash_commands(self):
        """슬래시 명령어들을 bot에 등록"""

        @self.bot.tree.command(
            name="task",
            description="Factory Tracker에 새 태스크 생성 (담당자 옵션 자동 추가)",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            name="태스크 제목 (필수)",
            person="담당자 이름 (소현, 정빈, 동훈 중 선택, 선택사항)",
            priority="우선순위 (High, Medium, Low 중 선택, 선택사항)",
            days="마감까지 남은 일수 (선택사항, 기본값: 0일 = 오늘)",
            task_type="태스크 타입 (🐞 Bug, 💬 Feature request, 💅 Polish 중 선택, 선택사항)",
        )
        @track_discord_command("task")
        async def task_command(
            interaction: discord.Interaction,
            name: str,  # 제목은 필수
            person: Optional[str] = None,  # 담당자는 선택사항
            priority: Optional[str] = None,
            days: Optional[int] = None,  # 마감까지 남은 일수
            task_type: Optional[str] = None,
        ):
            """Factory Tracker 태스크 생성 명령어"""
            # days를 deadline으로 변환 (기본값: 0일 = 오늘)
            from datetime import datetime, timedelta

            days = days if days is not None else 0  # 기본값: 0일 (오늘)
            deadline = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

            await self._handle_command_common(
                interaction,
                CommandType.TASK,
                {
                    "person": person,    # person 그대로 사용
                    "title": name,       # name -> title로 매핑
                    "priority": priority,
                    "deadline": deadline,
                    "task_type": task_type,
                },
            )

        @self.bot.tree.command(
            name="meeting",
            description="Board DB에 회의록 페이지 생성 및 스레드 안내",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            title="회의록 제목",
            meeting_time="회의 시간 (예: 2024-12-25 14:00, 12/25 14:00, 오늘 16:30)",
            meeting_type="회의 유형 (선택사항)",
            participants="참석자 목록 (쉼표로 구분, 선택사항)",
        )
        @track_discord_command("meeting")
        async def meeting_command(
            interaction: discord.Interaction,
            title: str,
            meeting_time: str,
            meeting_type: Optional[str] = None,
            participants: Optional[str] = None,
        ):
            """회의록 생성 명령어"""
            # 참석자 목록 파싱
            participants_list = []
            if participants:
                participants_list = [
                    p.strip() for p in participants.split(",") if p.strip()
                ]

            await self._handle_command_common(
                interaction,
                CommandType.MEETING,
                {
                    "title": title,
                    "meeting_date": meeting_time,
                    "meeting_type": meeting_type or "정기회의",
                    "participants": participants_list,
                },
            )

        @self.bot.tree.command(
            name="fetch",
            description="노션 페이지 내용을 현재 채널로 가져오기 (기본: 최근 생성된 페이지)",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            page_id="노션 페이지 ID (선택사항, 미입력시 최근 생성된 페이지)",
        )
        @track_discord_command("fetch")
        async def fetch_command(
            interaction: discord.Interaction,
            page_id: Optional[str] = None,
        ):
            """노션 페이지 내용 가져오기 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.FETCH_PAGE,
                {
                    "page_id": page_id,
                    "channel_id": str(interaction.channel_id),
                },
            )

        @self.bot.tree.command(
            name="watch",
            description="노션 페이지 변경사항을 주기적으로 확인하고 알림",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            page_id="감시할 노션 페이지 ID",
            interval="확인 간격 (분, 기본값: 30분)",
        )
        @track_discord_command("watch")
        async def watch_command(
            interaction: discord.Interaction,
            page_id: str,
            interval: int = 30,
        ):
            """노션 페이지 감시 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.WATCH_PAGE,
                {
                    "page_id": page_id,
                    "channel_id": str(interaction.channel_id),
                    "interval": interval,
                },
            )

        @self.bot.tree.command(
            name="help",
            description="사용 가능한 모든 명령어 안내",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @track_discord_command("help")
        async def help_command(interaction: discord.Interaction):
            """명령어 도움말"""
            await self._handle_command_common(interaction, CommandType.HELP, {})

        @self.bot.tree.command(
            name="status",
            description="bot 상태 및 시스템 정보 확인",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @track_discord_command("status")
        async def status_command(interaction: discord.Interaction):
            """시스템 상태 확인 명령어"""
            await self._handle_command_common(interaction, CommandType.STATUS, {})

        # 통계 관련 명령어들
        @self.bot.tree.command(
            name="daily_stats",
            description="일별 통계 조회 (차트 포함)",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            user="특정 사용자 필터링 (선택사항)",
        )
        @track_discord_command("daily_stats")
        async def daily_stats_command(
            interaction: discord.Interaction,
            user: Optional[discord.Member] = None,
        ):
            """일별 통계 조회 명령어"""
            try:
                # 응답 지연 (처리 시간이 오래 걸릴 수 있음)
                await interaction.response.defer(ephemeral=True)

                from datetime import datetime

                now = datetime.now()

                # 사용자 필터 설정
                user_filter = None
                if user:
                    user_filter = str(user.id)

                # 통계와 차트를 함께 가져오기
                result = await analytics_service.get_stats_with_chart(
                    analytics_service.get_daily_stats,
                    now,
                    user_filter,
                    stats_type="daily",
                )
                stats = result["stats"]
                chart_path = result["chart_path"]
                message = analytics_service.format_stats_message(stats, "daily")

                # 사용자 필터가 적용된 경우 메시지에 추가
                if user:
                    message = f"👤 **{user.display_name}님의 활동**\n\n" + message

                # 차트 파일이 있으면 첨부
                if chart_path and os.path.exists(chart_path):
                    file = discord.File(chart_path, filename="daily_stats.png")
                    await interaction.followup.send(message, file=file, ephemeral=True)
                else:
                    await interaction.followup.send(message, ephemeral=True)

            except Exception as e:
                logger.error(f"❌ 일별 통계 조회 실패: {e}")
                try:
                    await interaction.followup.send(
                        "❌ 통계 조회 중 오류가 발생했습니다.", ephemeral=True
                    )
                except:
                    await interaction.response.send_message(
                        "❌ 통계 조회 중 오류가 발생했습니다.", ephemeral=True
                    )

        @self.bot.tree.command(
            name="weekly_stats",
            description="주별 통계 조회 (차트 포함)",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            user="특정 사용자 필터링 (선택사항)",
        )
        @track_discord_command("weekly_stats")
        async def weekly_stats_command(
            interaction: discord.Interaction,
            user: Optional[discord.Member] = None,
        ):
            """주별 통계 조회 명령어"""
            try:
                # 응답 지연 (처리 시간이 오래 걸릴 수 있음)
                await interaction.response.defer(ephemeral=True)

                # 사용자 필터 설정
                user_filter = None
                if user:
                    user_filter = str(user.id)

                # 통계와 차트를 함께 가져오기
                result = await analytics_service.get_stats_with_chart(
                    analytics_service.get_weekly_stats,
                    user_filter,
                    stats_type="weekly",
                )
                stats = result["stats"]
                chart_path = result["chart_path"]
                message = analytics_service.format_stats_message(stats, "weekly")

                # 사용자 필터가 적용된 경우 메시지에 추가
                if user:
                    message = f"👤 **{user.display_name}님의 활동**\n\n" + message

                # 차트 파일이 있으면 첨부
                if chart_path and os.path.exists(chart_path):
                    file = discord.File(chart_path, filename="weekly_stats.png")
                    await interaction.followup.send(message, file=file, ephemeral=True)
                else:
                    await interaction.followup.send(message, ephemeral=True)

            except Exception as e:
                logger.error(f"❌ 주별 통계 조회 실패: {e}")
                try:
                    await interaction.followup.send(
                        "❌ 통계 조회 중 오류가 발생했습니다.", ephemeral=True
                    )
                except:
                    await interaction.response.send_message(
                        "❌ 통계 조회 중 오류가 발생했습니다.", ephemeral=True
                    )

        @self.bot.tree.command(
            name="monthly_stats",
            description="월별 통계 조회 (차트 포함)",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            user="특정 사용자 필터링 (선택사항)",
        )
        @track_discord_command("monthly_stats")
        async def monthly_stats_command(
            interaction: discord.Interaction,
            user: Optional[discord.Member] = None,
        ):
            """월별 통계 조회 명령어"""
            try:
                # 응답 지연 (처리 시간이 오래 걸릴 수 있음)
                await interaction.response.defer(ephemeral=True)

                # 현재 년월 사용
                from datetime import datetime

                now = datetime.now()
                year = now.year
                month = now.month

                # 통계와 차트를 함께 가져오기
                result = await analytics_service.get_stats_with_chart(
                    analytics_service.get_monthly_stats,
                    year,
                    month,
                    stats_type="monthly",
                )
                stats = result["stats"]
                chart_path = result["chart_path"]
                message = analytics_service.format_stats_message(stats, "monthly")

                # 사용자 필터가 적용된 경우 메시지에 추가
                if user:
                    message = f"👤 **{user.display_name}님의 활동**\n\n" + message

                # 차트 파일이 있으면 첨부
                if chart_path and os.path.exists(chart_path):
                    file = discord.File(chart_path, filename="monthly_stats.png")
                    await interaction.followup.send(message, file=file, ephemeral=True)
                else:
                    await interaction.followup.send(message, ephemeral=True)

            except Exception as e:
                logger.error(f"❌ 월별 통계 조회 실패: {e}")
                try:
                    await interaction.followup.send(
                        "❌ 통계 조회 중 오류가 발생했습니다.", ephemeral=True
                    )
                except:
                    await interaction.response.send_message(
                        "❌ 통계 조회 중 오류가 발생했습니다.", ephemeral=True
                    )

        @self.bot.tree.command(
            name="user_stats",
            description="사용자별 생산성 통계",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            user="통계를 조회할 사용자",
        )
        @track_discord_command("user_stats")
        async def user_stats_command(
            interaction: discord.Interaction,
            user: discord.Member,
        ):
            """사용자별 통계 조회 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.USER_STATS,
                {"user": str(user.id)},
            )

        @self.bot.tree.command(
            name="team_stats",
            description="팀 전체 통계 및 협업 분석",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @track_discord_command("team_stats")
        async def team_stats_command(interaction: discord.Interaction):
            """팀 통계 조회 명령어"""
            await self._handle_command_common(interaction, CommandType.TEAM_STATS, {})

        @self.bot.tree.command(
            name="trends",
            description="활동 트렌드 분석 (차트 포함)",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            days="분석 기간 (일수, 기본값: 14일)",
        )
        @track_discord_command("trends")
        async def trends_command(interaction: discord.Interaction, days: int = 14):
            """트렌드 분석 명령어"""
            await self._handle_command_common(
                interaction, CommandType.TRENDS, {"days": days}
            )

        @self.bot.tree.command(
            name="task_stats",
            description="태스크 완료율 및 상태별 통계",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            user="특정 사용자 필터링 (선택사항)",
            status="상태 필터링 (in_progress, done, 선택사항)",
        )
        @track_discord_command("task_stats")
        async def task_stats_command(
            interaction: discord.Interaction,
            user: Optional[discord.Member] = None,
            status: Optional[str] = None,
        ):
            """태스크 통계 조회 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.TASK_STATS,
                {
                    "user": str(user.id) if user else None,
                    "status": status,
                },
            )

        # 검색 명령어
        @self.bot.tree.command(
            name="search",
            description="노션 페이지 검색 (제목 + 내용, 연관 검색어 포함)",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            query="검색할 키워드",
            page_type="페이지 타입 필터 (task, meeting, document, all)",
            user="특정 사용자 필터링 (선택사항)",
            days="검색 기간 (일수, 선택사항)",
        )
        @track_discord_command("search")
        async def search_command(
            interaction: discord.Interaction,
            query: str,
            page_type: Optional[str] = "all",
            user: Optional[discord.Member] = None,
            days: Optional[int] = None,
        ):
            """페이지 검색 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.SEARCH,
                {
                    "query": query,
                    "page_type": page_type,
                    "user": str(user.id) if user else None,
                    "days": days,
                },
            )

        # 문서 생성 명령어
        @self.bot.tree.command(
            name="document",
            description="Board DB에 문서 페이지 생성",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            title="문서 제목",
            doc_type="문서 타입 (개발 문서, 기획안, 개발 규칙, 회의록)",
        )
        @track_discord_command("document")
        async def document_command(
            interaction: discord.Interaction,
            title: str,
            doc_type: str,
        ):
            """문서 생성 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.DOCUMENT,
                {
                    "title": title,
                    "doc_type": doc_type,
                },
            )

        # CRUD Update/Archive 명령어들
        @self.bot.tree.command(
            name="update_task",
            description="태스크 정보 업데이트",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            page_id="업데이트할 태스크의 Notion 페이지 ID",
            title="새로운 태스크 제목 (선택사항)",
            priority="새로운 우선순위 (High, Medium, Low)",
            person="새로운 담당자 (선택사항)",
            status="새로운 상태 (선택사항)",
        )
        @track_discord_command("update_task")
        async def update_task_command(
            interaction: discord.Interaction,
            page_id: str,
            title: Optional[str] = None,
            priority: Optional[str] = None,
            person: Optional[str] = None,
            status: Optional[str] = None,
        ):
            """태스크 업데이트 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.UPDATE_TASK,
                {
                    "page_id": page_id,
                    "title": title,
                    "priority": priority,
                    "person": person,
                    "status": status,
                },
            )

        @self.bot.tree.command(
            name="update_meeting",
            description="회의록 정보 업데이트",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            page_id="업데이트할 회의록의 Notion 페이지 ID",
            title="새로운 회의 제목 (선택사항)",
            participants="새로운 참석자 목록 (선택사항)",
            meeting_type="새로운 회의 유형 (선택사항)",
            status="새로운 상태 (선택사항)",
        )
        @track_discord_command("update_meeting")
        async def update_meeting_command(
            interaction: discord.Interaction,
            page_id: str,
            title: Optional[str] = None,
            participants: Optional[str] = None,
            meeting_type: Optional[str] = None,
            status: Optional[str] = None,
        ):
            """회의록 업데이트 명령어"""
            # 참석자 목록 파싱
            participants_list = []
            if participants:
                participants_list = [
                    p.strip() for p in participants.split(",") if p.strip()
                ]

            await self._handle_command_common(
                interaction,
                CommandType.UPDATE_MEETING,
                {
                    "page_id": page_id,
                    "title": title,
                    "participants": participants_list,
                    "meeting_type": meeting_type,
                    "status": status,
                },
            )

        @self.bot.tree.command(
            name="update_document",
            description="문서 정보 업데이트",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            page_id="업데이트할 문서의 Notion 페이지 ID",
            title="새로운 문서 제목 (선택사항)",
            doc_type="새로운 문서 유형 (선택사항)",
            status="새로운 상태 (선택사항)",
        )
        @track_discord_command("update_document")
        async def update_document_command(
            interaction: discord.Interaction,
            page_id: str,
            title: Optional[str] = None,
            doc_type: Optional[str] = None,
            status: Optional[str] = None,
        ):
            """문서 업데이트 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.UPDATE_DOCUMENT,
                {
                    "page_id": page_id,
                    "title": title,
                    "doc_type": doc_type,
                    "status": status,
                },
            )

        @self.bot.tree.command(
            name="archive",
            description="Notion 페이지를 아카이브 (삭제)",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            page_id="아카이브할 Notion 페이지 ID",
        )
        @track_discord_command("archive_page")
        async def archive_command(
            interaction: discord.Interaction,
            page_id: str,
        ):
            """페이지 아카이브 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.ARCHIVE_PAGE,
                {
                    "page_id": page_id,
                },
            )

        @self.bot.tree.command(
            name="restore",
            description="아카이브된 Notion 페이지 복구",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @app_commands.describe(
            page_id="복구할 Notion 페이지 ID",
        )
        @track_discord_command("restore_page")
        async def restore_command(
            interaction: discord.Interaction,
            page_id: str,
        ):
            """페이지 복구 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.RESTORE_PAGE,
                {
                    "page_id": page_id,
                },
            )

        # ── CareerOS onboarding commands ─────────────────────────────

        @self.bot.tree.command(
            name="onboard",
            description="커리어OS 온보딩 시작 — 커리어 목표·이력서·GitHub를 순서대로 입력합니다",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @track_discord_command("onboard")
        async def onboard_command(interaction: discord.Interaction):
            """커리어OS 온보딩 시작 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.CAREEROS_ONBOARD,
                {"discord_user_id": str(interaction.user.id)},
            )

        @self.bot.tree.command(
            name="career",
            description="커리어OS 프로필 상태 확인 (CandidateGraph)",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @track_discord_command("career")
        async def career_status_command(interaction: discord.Interaction):
            """커리어 프로필 현황 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.CAREEROS_STATUS,
                {"discord_user_id": str(interaction.user.id)},
            )

        @self.bot.tree.command(
            name="restart_onboard",
            description="커리어OS 온보딩 세션 초기화 후 재시작",
            guild=discord.Object(id=int(settings.discord_guild_id)),
        )
        @track_discord_command("restart_onboard")
        async def restart_onboard_command(interaction: discord.Interaction):
            """온보딩 재시작 명령어"""
            await self._handle_command_common(
                interaction,
                CommandType.CAREEROS_RESTART,
                {"discord_user_id": str(interaction.user.id)},
            )

        # ── on_message: route to onboarding handler ──────────────────

        @self.bot.event
        async def on_message(message: discord.Message):
            if message.author.bot:
                return
            try:
                from src.conversation.onboarding_handler import onboarding_handler
                from src.conversation.state import ChannelType

                session = await onboarding_handler.get_session(
                    str(message.author.id), ChannelType.DISCORD
                )
                if not session:
                    return

                attachment_url = None
                attachment_name = None
                if message.attachments:
                    attachment_url = message.attachments[0].url
                    attachment_name = message.attachments[0].filename

                reply = await onboarding_handler.handle_message(
                    channel_user_id=str(message.author.id),
                    channel_type=ChannelType.DISCORD,
                    text=message.content,
                    attachment_url=attachment_url,
                    attachment_name=attachment_name,
                )
                if reply:
                    await message.channel.send(reply)
            except Exception as msg_error:
                logger.warning("on_message onboarding error: %s", msg_error)

        # 슬래시 명령어 등록 완료 (로그 제거)

    @safe_execution("handle_command_common")
    async def _handle_command_common(
        self,
        interaction: discord.Interaction,
        command: CommandType,
        parameters: Dict[str, Any],
    ):
        """
        모든 슬래시 명령어의 공통 처리 로직

        Args:
            interaction: Discord 인터랙션 객체
            command: 명령어 타입
            parameters: 명령어 매개변수들
        """
        # 명령어 처리 시작 알림
        await interaction.response.defer(ephemeral=True)

        start_time = datetime.now()

        try:
            # 요청 DTO 생성
            request = DiscordCommandRequestDTO(
                command_type=command,
                user=DiscordUserDTO(
                    user_id=interaction.user.id,
                    username=interaction.user.name,
                    display_name=interaction.user.display_name,
                    avatar_url=(
                        interaction.user.avatar.url if interaction.user.avatar else None
                    ),
                ),
                guild=DiscordGuildDTO(
                    guild_id=interaction.guild_id or 0,
                    guild_name=(
                        interaction.guild.name if interaction.guild else "Unknown"
                    ),
                    channel_id=interaction.channel_id,
                ),
                parameters=parameters,
                execution_time=start_time,
            )

            # 비즈니스 로직 콜백 호출
            if self.command_callback:
                with logger_manager.performance_logger(
                    f"command_{command.value}_processing"
                ):
                    response = await self.command_callback(request)
            else:
                # 콜백이 없으면 기본 응답
                response = DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 명령어 처리 시스템이 초기화되지 않았습니다.",
                    ephemeral=True,
                )

            # Discord 응답 전송
            await self._send_discord_response(interaction, response)

            # 성공 메트릭 기록
            execution_time = (datetime.now() - start_time).total_seconds()
            await metrics_collector.record_command_usage(
                command.value,
                request.user.user_id,
                request.guild.guild_id,
                success=True,
                execution_time_seconds=execution_time,
            )

            # 비즈니스 메트릭 기록
            metrics = get_metrics_collector()
            if command == CommandType.TASK:
                person = parameters.get("person", "unknown")
                priority = parameters.get("priority", "medium")
                metrics.record_task_created(priority, person)
            elif command == CommandType.MEETING:
                participants = parameters.get("participants", [])
                metrics.record_meeting_created(len(participants))
            elif command == CommandType.DOCUMENT:
                doc_type = parameters.get("doc_type", "unknown")
                metrics.record_document_created(doc_type)

            logger.info(
                f"✅ 명령어 처리 완료: {command.value} by {request.user.username}"
            )

        except Exception as processing_error:
            # 실패 메트릭 기록
            execution_time = (datetime.now() - start_time).total_seconds()
            await metrics_collector.record_command_usage(
                command.value,
                interaction.user.id,
                interaction.guild_id or 0,
                success=False,
                execution_time_seconds=execution_time,
            )

            # 에러를 글로벌 핸들러로 전달
            raise processing_error

    async def _send_discord_response(
        self, interaction: discord.Interaction, response: DiscordMessageResponseDTO
    ):
        """Discord 인터랙션에 응답 메시지 전송"""
        try:
            # 기본 메시지 내용
            message_content = response.content

            # 제목이 있으면 추가
            if response.title:
                message_content = f"**{response.title}**\n{message_content}"

            # 임베드 메시지 생성 (필요한 경우)
            embed = None
            if response.is_embed:
                embed = discord.Embed(
                    title=response.title,
                    description=response.content,
                    color=discord.Color.blue(),
                )
                embed.timestamp = datetime.now()

            # 응답 전송
            await interaction.followup.send(
                content=message_content if not embed else None,
                embed=embed,
                ephemeral=response.is_ephemeral,
            )

        except Exception as response_error:
            logger.error(f"❌ Discord 응답 전송 실패: {response_error}")
            # 최소한의 에러 메시지라도 전송 시도
            try:
                await interaction.followup.send(
                    "⚠️ 응답 전송 중 오류가 발생했습니다.", ephemeral=True
                )
            except:
                pass  # 더 이상 시도하지 않음

    # ===== I디스코드_서비스 인터페이스 구현 =====

    async def process_command(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """
        디스코드 명령어 처리 (외부에서 직접 호출용)

        Args:
            request: 명령어 실행 요청 정보

        Returns:
            DiscordMessageResponseDTO: 응답 메시지 정보
        """
        try:
            # 여기서는 기본적인 응답만 생성 (실제 비즈니스 로직은 콜백에서)
            if request.command_type == CommandType.STATUS:
                status_info = await self.check_bot_status()

                status_message = (
                    f"🤖 **Discord bot 상태**\n"
                    f"• 연결 상태: {'✅ 연결됨' if status_info['ready'] else '❌ 연결 끊김'}\n"
                    f"• 서버 수: {status_info['guild_count']}개\n"
                    f"• 지연시간: {status_info['latency']:.2f}ms\n"
                    f"• 업타임: {status_info['uptime']}"
                )

                return DiscordMessageResponseDTO(
                    message_type=MessageType.SYSTEM_STATUS,
                    title="시스템 상태",
                    content=status_message,
                    embed=True,
                    ephemeral=True,
                )

            # 다른 명령어들은 비즈니스 로직에서 처리
            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content="명령어 처리를 위해 비즈니스 로직 콜백이 필요합니다.",
                ephemeral=True,
            )

        except Exception as processing_error:
            raise DiscordAPIException(
                "명령어 처리 실패", original_exception=processing_error
            )

    @safe_execution("get_or_create_daily_thread")
    async def get_or_create_daily_thread(
        self,
        channel_id: int,
        title: Optional[str] = None,
        date: Optional[datetime] = None,
    ) -> ThreadInfoDTO:
        """
        지정된 날짜의 스레드를 조회하거나 없으면 새로 생성

        Args:
            channel_id: 대상 채널 ID
            title: 스레드에 포함할 제목 (선택사항)
            date: 스레드 날짜 (기본값: 오늘)

        Returns:
            ThreadInfoDTO: 스레드 정보
        """
        try:
            if not date:
                date = datetime.now(settings.tz)

            # 스레드 이름 생성 (YYYY/MM/DD: 제목 형식)
            base_name = f"{date.year}/{date.month:02d}/{date.day:02d}"
            if title:
                thread_name = f"{base_name}: {title}"
            else:
                thread_name = base_name

            logger.info(
                f"🔍 스레드 조회/생성 시작: channel_id={channel_id}, title='{title}', thread_name='{thread_name}'"
            )

            # 1. 캐시에서 스레드 정보 조회
            logger.debug(f"📋 캐시에서 스레드 조회 중: {thread_name}")
            cached_thread = await thread_cache_manager.get_thread_info(
                channel_id, thread_name
            )

            if cached_thread:
                logger.info(f"✅ 캐시에서 스레드 발견: {cached_thread}")
                # 캐시에 있는 스레드 검증
                thread = self.bot.get_channel(cached_thread["thread_id"])

                if thread and isinstance(thread, discord.Thread):
                    # 스레드가 유효하면 사용 시간 업데이트
                    logger.info(f"🎯 기존 스레드 사용: {thread_name} (ID: {thread.id})")
                    await thread_cache_manager.update_thread_usage_time(
                        channel_id, thread_name
                    )

                    logger.debug(f"🎯 스레드 캐시 히트: {thread_name}")
                    return DTOConverter.mongodb_doc_to_thread_dto(cached_thread)
                else:
                    # 스레드가 삭제되었으면 캐시에서 제거
                    logger.warning(f"⚠️ 캐시된 스레드가 존재하지 않음: {thread_name}")
            else:
                logger.info(f"❌ 캐시에서 스레드를 찾을 수 없음: {thread_name}")

            # 2. 새 스레드 생성
            logger.info(
                f"🔧 새 스레드 생성 시작: channel_id={channel_id}, name='{thread_name}'"
            )
            thread_info = await self._create_new_thread(channel_id, thread_name, date)

            logger.info(f"🆕 새 스레드 생성 완료: {thread_name}")
            return thread_info

        except Exception as thread_error:
            logger.error(f"❌ get_or_create_daily_thread 실패: {thread_error}")
            logger.error(
                f"❌ 실패 상세정보: channel_id={channel_id}, title='{title}', thread_name='{thread_name if 'thread_name' in locals() else 'N/A'}'"
            )
            raise DiscordAPIException(
                f"스레드 조회/생성 실패: {channel_id}", original_exception=thread_error
            )

    async def _create_new_thread(
        self, channel_id: int, thread_name: str, date: datetime
    ) -> ThreadInfoDTO:
        """새 스레드를 생성하고 캐시에 저장"""
        try:
            logger.info(
                f"🔧 _create_new_thread 시작: channel_id={channel_id}, thread_name='{thread_name}'"
            )

            # 채널 객체 가져오기
            logger.debug(f"📡 채널 객체 조회 중: {channel_id}")
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.debug(f"📡 캐시에서 찾을 수 없어 API로 채널 조회: {channel_id}")
                channel = await self.bot.fetch_channel(channel_id)

            logger.info(
                f"✅ 채널 확인 완료: {channel.name} (ID: {channel.id}, Type: {type(channel).__name__})"
            )

            # 스레드 안에서 명령어를 실행한 경우, 부모 채널을 찾아서 사용
            if isinstance(channel, discord.Thread):
                logger.info(
                    f"🔄 스레드 안에서 실행됨, 부모 채널로 이동: {channel.parent.name}"
                )
                channel = channel.parent
                if not isinstance(channel, discord.TextChannel):
                    raise ValueError(
                        f"부모 채널 {channel.id}는 텍스트 채널이 아닙니다 (Type: {type(channel).__name__})"
                    )
            elif not isinstance(channel, discord.TextChannel):
                raise ValueError(
                    f"채널 {channel_id}는 텍스트 채널이 아닙니다 (Type: {type(channel).__name__})"
                )

            # 새 스레드 생성
            logger.info(f"🔨 Discord API를 통한 스레드 생성 시도: '{thread_name}'")
            thread = await channel.create_thread(
                name=thread_name,
                auto_archive_duration=1440,  # 24시간
                type=discord.ChannelType.public_thread,
            )
            logger.info(f"✅ 스레드 생성 성공: {thread.name} (ID: {thread.id})")

            # 스레드 정보 DTO 생성
            logger.debug(f"📋 ThreadInfoDTO 생성 중...")
            thread_info = ThreadInfoDTO(
                thread_id=thread.id,
                thread_name=thread_name,
                parent_channel_id=channel_id,
                created_date=date.strftime("%Y-%m-%d"),
                created_time=date,
                last_used_time=datetime.now(),
                usage_count=1,
            )

            # 캐시에 저장
            logger.info(
                f"💾 캐시에 스레드 정보 저장: channel_id={channel_id}, thread_name='{thread_name}', thread_id={thread.id}"
            )
            await thread_cache_manager.save_thread_info(
                channel_id, thread_name, thread.id
            )
            logger.info(f"✅ 캐시 저장 완료")

            return thread_info

        except Exception as creation_error:
            logger.error(f"❌ _create_new_thread 실패: {creation_error}")
            logger.error(
                f"❌ 실패 상세정보: thread_name='{thread_name}', channel_id={channel_id}"
            )
            raise DiscordAPIException(
                f"스레드 생성 실패: {thread_name}", original_exception=creation_error
            )

    async def send_thread_message(
        self,
        thread_id: int,
        content: str = "",
        file_path: str = None,
        embed: dict = None,
    ) -> bool:
        """
        특정 스레드에 메시지를 전송

        Args:
            thread_id: 대상 스레드 ID
            content: 전송할 메시지 내용
            file_path: 첨부할 파일 경로 (선택사항)
            embed: Discord embed 객체 (선택사항)

        Returns:
            bool: 전송 성공 여부
        """
        try:
            # 스레드 객체 가져오기
            thread = self.bot.get_channel(thread_id)
            if not thread:
                thread = await self.bot.fetch_channel(thread_id)

            if not isinstance(thread, discord.Thread):
                logger.error(f"❌ 스레드 {thread_id}를 찾을 수 없음")
                return False

            # Discord embed 객체 생성
            discord_embed = None
            if embed:
                discord_embed = discord.Embed.from_dict(embed)

            # 파일 첨부가 있는 경우
            if file_path and os.path.exists(file_path):
                file = discord.File(file_path)
                await thread.send(content=content, file=file, embed=discord_embed)
                logger.debug(f"📨 스레드 메시지+파일 전송 완료: {thread.name}")
            else:
                # 텍스트만 전송
                await thread.send(content=content, embed=discord_embed)
                logger.debug(f"📨 스레드 메시지 전송 완료: {thread.name}")

            return True

        except Exception as send_error:
            logger.error(f"❌ 스레드 메시지 전송 실패: {send_error}")
            return False

    async def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        디스코드 사용자 정보를 조회

        Args:
            user_id: 조회할 사용자 Discord ID

        Returns:
            Optional[Dict]: 사용자 정보 또는 None
        """
        try:
            user = self.bot.get_user(user_id)
            if not user:
                user = await self.bot.fetch_user(user_id)

            if user:
                return {
                    "id": user.id,
                    "name": user.name,
                    "display_name": user.display_name,
                    "avatar_url": user.avatar.url if user.avatar else None,
                    "created_at": user.created_at.isoformat(),
                    "bot": user.bot,
                }

            return None

        except Exception as lookup_error:
            logger.error(f"❌ 사용자 정보 조회 실패: {lookup_error}")
            return None

    async def check_bot_status(self) -> Dict[str, Any]:
        """
        디스코드 bot의 현재 상태를 확인

        Returns:
            Dict: bot 상태 정보
        """
        try:
            # 업타임 계산
            uptime_seconds = 0
            if hasattr(self.bot, "_ready_time"):
                uptime_seconds = (datetime.now() - self.bot._ready_time).total_seconds()

            # 업타임을 사람이 읽기 쉬운 형태로 변환
            uptime_string = str(timedelta(seconds=int(uptime_seconds)))

            return {
                "ready": self.is_bot_ready and self.bot.is_ready(),
                "user": {
                    "id": self.bot.user.id if self.bot.user else None,
                    "name": self.bot.user.name if self.bot.user else None,
                },
                "guild_count": len(self.bot.guilds),
                "latency": self.bot.latency * 1000,  # ms 단위
                "uptime": uptime_string,
                "uptime_seconds": uptime_seconds,
                "cached_messages": len(self.bot.cached_messages),
                "cached_users": len(self.bot.users),
            }

        except Exception as status_error:
            logger.error(f"❌ bot 상태 확인 실패: {status_error}")
            return {"ready": False, "error": str(status_error)}

    # ===== 통계 관련 명령어들 =====

    # 중복된 메서드 제거됨 - 슬래시 명령어에서 처리

    # 중복된 메서드 제거됨 - 슬래시 명령어에서 처리

    async def user_stats_command(
        self, interaction: discord.Interaction, days: int = 30
    ):
        """개인 활동 통계 조회 명령어"""
        try:
            user_id = str(interaction.user.id)
            stats = await analytics_service.get_user_productivity(user_id, days)
            message = analytics_service.format_stats_message(stats, "user")

            await interaction.response.send_message(message, ephemeral=True)
            logger.info(f"📊 개인 통계 조회 완료: {interaction.user.name}")

        except Exception as e:
            logger.error(f"❌ 개인 통계 조회 실패: {e}")
            await interaction.response.send_message(
                "❌ 통계 조회 중 오류가 발생했습니다.", ephemeral=True
            )

    async def team_stats_command(
        self, interaction: discord.Interaction, days: int = 30
    ):
        """팀 활동 통계 조회 명령어"""
        try:
            stats = await analytics_service.get_team_comparison(days)
            message = analytics_service.format_stats_message(stats, "team")

            await interaction.response.send_message(message, ephemeral=True)
            logger.info(f"📊 팀 통계 조회 완료: {interaction.user.name}")

        except Exception as e:
            logger.error(f"❌ 팀 통계 조회 실패: {e}")
            await interaction.response.send_message(
                "❌ 통계 조회 중 오류가 발생했습니다.", ephemeral=True
            )

    async def trends_command(self, interaction: discord.Interaction, days: int = 14):
        """활동 트렌드 조회 명령어"""
        try:
            stats = await analytics_service.get_activity_trends(days)
            message = analytics_service.format_stats_message(stats, "trends")

            await interaction.response.send_message(message, ephemeral=True)
            logger.info(f"📊 트렌드 조회 완료: {interaction.user.name}")

        except Exception as e:
            logger.error(f"❌ 트렌드 조회 실패: {e}")
            await interaction.response.send_message(
                "❌ 통계 조회 중 오류가 발생했습니다.", ephemeral=True
            )

    # ===== 검색 관련 명령어들 =====

    async def search_command(
        self,
        interaction: discord.Interaction,
        query: str,
        page_type: str = None,
        user: discord.Member = None,
        days: int = 90,
    ):
        """페이지 검색 명령어"""
        try:
            # 검색어 길이 확인
            if len(query.strip()) < 2:
                await interaction.response.send_message(
                    "❌ 검색어는 2글자 이상 입력해주세요.", ephemeral=True
                )
                return

            # 사용자 필터 설정
            user_filter = str(user.id) if user else None

            # 검색 실행
            search_results = await search_service.search_pages(
                query=query,
                page_type=page_type,
                user_filter=user_filter,
                days_limit=days,
                limit=20,
            )

            # 결과 포맷팅
            message = search_service.format_search_results(search_results)

            await interaction.response.send_message(message, ephemeral=True)
            logger.info(f"🔍 검색 완료: {interaction.user.name} -> '{query}'")

        except Exception as e:
            logger.error(f"❌ 검색 실패: {e}")
            await interaction.response.send_message(
                "❌ 검색 중 오류가 발생했습니다.", ephemeral=True
            )

    # ===== 문서 생성 명령어 =====

    async def document_command(
        self, interaction: discord.Interaction, title: str, doc_type: str = "개발 문서"
    ):
        """문서 생성 명령어"""
        try:
            # 문서 유형 검증
            valid_types = ["개발 문서", "기획안", "개발 규칙"]
            if doc_type not in valid_types:
                await interaction.response.send_message(
                    f"❌ 올바른 문서 유형을 선택해주세요: {', '.join(valid_types)}",
                    ephemeral=True,
                )
                return

            # 문서 생성 요청 처리
            from ..main import app

            request = DiscordCommandRequestDTO(
                command_type=CommandType.DOCUMENT,
                user=DiscordUserDTO(
                    user_id=interaction.user.id,
                    username=interaction.user.name,
                    display_name=interaction.user.display_name or interaction.user.name,
                ),
                channel_id=interaction.channel_id,
                parameters={"title": title, "type": doc_type},
            )

            response = await app._process_command_business_logic(request)
            await interaction.response.send_message(
                response.content, ephemeral=response.is_ephemeral
            )
            logger.info(f"📄 문서 생성 완료: {interaction.user.name} -> '{title}'")

        except Exception as e:
            logger.error(f"❌ 문서 생성 실패: {e}")
            await interaction.response.send_message(
                "❌ 문서 생성 중 오류가 발생했습니다.", ephemeral=True
            )

    # ===== 이벤트 생성 관련 메서드 =====

    @safe_execution("create_discord_event")
    async def create_discord_event(
        self,
        title: str,
        description: str,
        start_time: datetime,
        duration_hours: int = 1,
        voice_channel_name: str = "회의실",
    ) -> bool:
        """
        Discord 서버에 스케줄된 이벤트를 생성합니다.

        Args:
            title: 이벤트 제목
            description: 이벤트 설명
            start_time: 이벤트 시작 시간
            duration_hours: 지속 시간 (기본값: 1시간)
            voice_channel_name: 음성 채널 이름 (기본값: "회의실")

        Returns:
            bool: 이벤트 생성 성공 여부
        """
        try:
            # 모든 길드에서 첫 번째 길드 가져오기 (일반적으로 봇이 하나의 서버에만 있음)
            if not self.bot.guilds:
                logger.error("❌ Discord 길드를 찾을 수 없습니다.")
                return False

            guild = self.bot.guilds[0]  # 첫 번째 길드 사용
            logger.info(f"🎯 이벤트 생성 대상 서버: {guild.name}")

            # 음성 채널 찾기
            voice_channel = None

            # 모든 음성 채널 목록 로깅
            logger.info(f"🔍 서버 '{guild.name}'의 음성 채널 목록:")
            for channel in guild.voice_channels:
                logger.info(f"   🔊 {channel.name} (ID: {channel.id})")

            # 지정된 음성 채널 찾기
            for channel in guild.voice_channels:
                if channel.name == voice_channel_name:
                    voice_channel = channel
                    logger.info(
                        f"✅ 음성 채널 찾음: {voice_channel.name} (ID: {voice_channel.id})"
                    )
                    break

            if not voice_channel:
                logger.warning(
                    f"⚠️ '{voice_channel_name}' 음성 채널을 찾을 수 없습니다."
                )
                logger.info(
                    "💡 사용 가능한 음성 채널 중 하나를 선택하거나 채널명을 확인해주세요."
                )
                # 채널을 찾을 수 없어도 이벤트는 생성 (위치 없이)

            # 시간대 문제 해결: Discord는 UTC 시간을 요구함
            if start_time.tzinfo is None:
                # naive datetime인 경우 현재 시간대를 UTC로 변환
                import pytz

                # 한국 시간대를 UTC로 변환
                kst = pytz.timezone("Asia/Seoul")
                start_time = kst.localize(start_time).astimezone(pytz.UTC)
            else:
                # 이미 timezone-aware인 경우 UTC로 변환
                start_time = start_time.astimezone(pytz.UTC)

            # 이벤트 종료 시간 계산
            end_time = start_time + timedelta(hours=duration_hours)

            # 음성 채널이 없으면 이벤트 생성하지 않음
            if not voice_channel:
                logger.warning(
                    "⚠️ 음성 채널을 찾을 수 없어 Discord 이벤트를 생성하지 않습니다."
                )
                return False

            # Discord 이벤트 생성
            logger.info(f"🎯 Discord 이벤트 생성 시도: '{title}'")
            logger.info(f"   📅 시작 시간: {start_time} (UTC)")
            logger.info(f"   📅 종료 시간: {end_time} (UTC)")
            logger.info(f"   🔊 음성 채널: {voice_channel.name}")

            event = await guild.create_scheduled_event(
                name=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                channel=voice_channel,  # entity_type=voice일 때는 channel 사용
                privacy_level=discord.PrivacyLevel.guild_only,
                entity_type=discord.EntityType.voice,  # 음성 채널이 있으므로 voice 타입
                reason="DinoBot을 통한 회의 일정 생성",
            )

            logger.info(f"✅ Discord 이벤트 생성 완료: '{title}' (ID: {event.id})")
            logger.info(f"   📅 시작: {start_time.strftime('%Y-%m-%d %H:%M')}")
            logger.info(f"   📅 종료: {end_time.strftime('%Y-%m-%d %H:%M')}")
            if voice_channel:
                logger.info(f"   🔊 위치: {voice_channel.name}")

            return True

        except discord.HTTPException as e:
            logger.error(f"❌ Discord 이벤트 생성 실패 (HTTP 오류): {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Discord 이벤트 생성 실패: {e}")
            return False

    async def shutdown(self):
        """Discord 서비스 종료"""
        try:
            if self.bot:
                await self.bot.close()
                logger.info("👋 Discord bot 종료 완료")
        except Exception as e:
            logger.warning(f"⚠️ Discord bot 종료 중 경고: {e}")


# Global Discord service instance
discord_service = DiscordService()
