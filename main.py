"""
DinoBot 메인 애플리케이션
- Discord Notion Integration Bot
- 클린 아키텍처 기반 설계
- 인터페이스와 DTO를 통한 느슨한 결합
- MongoDB를 적극 활용한 성능 최적화
- 실시간 모니터링 및 자동 관리
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import uvicorn
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse

# 핵심 모듈들
from src.core.config import settings
from src.core.dynamic_config import dynamic_config_manager
from src.service.workflow.dynamic_command_service import dynamic_command_service
from src.core.logger import (
    initialize_logging_system,
    get_logger,
    logger_manager,
)
from src.core.metrics import get_metrics_collector
from src.core.database import (
    mongodb_connection,
    initialize_meetup_loader_collections,
    log_system_event,
    save_notion_page,
    get_recent_notion_page_by_user,
)
from src.core.exceptions import global_exception_handler, UserInputException
from src.core.global_error_handler import (
    handle_exception,
    ErrorSeverity,
    setup_global_exception_handlers,
)

# 서비스 관리자
from src.core.service_manager import service_manager

# MCP 관련 import 제거
from src.service.analytics.mongodb_advanced import (
    get_mongodb_analysis_service,
    get_mongodb_auto_management,
    start_realtime_performance_monitoring,
    daily_auto_cleanup_task,
    weekly_backup_task,
)

# 모델 및 DTO
from src.interface.service import IServiceManager
from src.dto.common import (
    CommandType,
    MessageType,
    SystemStatusDTO,
    ServiceStatusDTO,
    MongoDBStatusDTO,
)
from src.dto.discord import (
    DiscordCommandRequestDTO,
    DiscordMessageResponseDTO,
)
from src.dto.notion import (
    TaskCreateRequestDTO,
    MeetingCreateRequestDTO,
)
from src.dto.webhook import (
    NotionWebhookRequestDTO,
    WebhookProcessResultDTO,
)

# Logger initialization
logger = get_logger("main")


class ServiceManager(IServiceManager):
    """
    모든 서비스를 통합 관리하는 메인 클래스

    클린 아키텍처 원칙:
    - 의존성 역전: 인터페이스에 의존
    - 단일 책임: 각 서비스는 하나의 책임만
    - 개방-폐쇄: 확장에는 열려있고 수정에는 닫혀있음
    """

    def __init__(self):
        # 새로운 서비스 매니저 사용
        self._service_manager = service_manager
        self._model_context_processor = (
            None  # Model context processor initialized later
        )
        self._fallback_context_processor = (
            None  # Fallback context processor initialized later
        )

        # FastAPI 애플리케이션
        self.web_application = FastAPI(
            title="DinoBot API",
            description="노션-디스코드 통합 봇 API",
            version="2.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )

        # 시스템 상태
        self.start_time = None
        self.service_ready = False
        self.auto_tasks = []

        # 통합 서비스 관리자 초기화 완료 (로그 제거)

    # ===== I통합_서비스_관리자 인터페이스 구현 =====

    @property
    def notion_service(self):
        return self._service_manager.get_service("notion")

    @property
    def discord_service(self):
        try:
            return self._service_manager.get_service("discord")
        except KeyError:
            return None

    @property
    def cache_service(self):
        # 현재는 MongoDB 직접 사용, 향후 별도 캐시 서비스로 분리 가능
        return None

    @property
    def metrics_service(self):
        # MongoDB 분석 서비스로 대체
        return get_mongodb_analysis_service()

    @property
    def business_service(self):
        # 현재는 자체 구현, 향후 별도 서비스로 분리 가능
        return self

    async def initialize_system(self) -> bool:
        """전체 시스템을 순차적으로 초기화"""
        self.start_time = datetime.now(settings.tz)
        logger.info("🚀 DinoBot 시스템 초기화 시작")

        # 전역 예외 처리기 설정
        setup_global_exception_handlers()

        try:
            # 1. MongoDB 연결
            await mongodb_connection.connect_database()

            # 2. DinoBot 서비스 컬렉션 초기화
            collection_result = await initialize_meetup_loader_collections()

            # 초기화 결과 로깅
            await log_system_event(
                event_type="collections_initialized",
                description=f"컬렉션 초기화 완료: {collection_result['total_collections']}개 (신규: {len(collection_result['created_collections'])}개)",
                severity="info",
                metadata=collection_result,
            )

            # 3. 설정 관리자 초기화
            from src.core.config_manager import config_manager

            await config_manager.initialize()

            # 3.5. 설정 상태 확인 및 조건부 초기화
            if config_manager.is_fully_configured():
                logger.info(
                    "✅ 모든 필수 설정이 완료되었습니다. 전체 서비스를 시작합니다."
                )
                await self._initialize_full_services()
            else:
                missing_configs = config_manager.get_missing_configs()
                logger.warning(
                    f"⚠️ 필수 설정이 누락되었습니다: {', '.join(missing_configs)}"
                )
                logger.info(
                    "🔧 설정 웹 UI만 활성화합니다. http://localhost:8889/config 에서 설정을 완료하세요."
                )
                await self._initialize_config_only()

            # 4. 서비스별 초기화는 조건부 초기화에서 처리됨

            # 5. 초기 데이터 동기화 완료 대기
            await asyncio.sleep(5)  # 동기화 완료 대기

            # 6. Discord 봇 초기화 (전체 서비스 모드에서만)
            if config_manager.is_fully_configured():
                try:
                    discord_service = self._service_manager.get_service("discord")
                    await discord_service.start_bot()

                    # Discord 봇에 비즈니스 로직 콜백 설정
                    discord_service.set_command_callback(
                        self._process_command_business_logic
                    )
                except KeyError:
                    logger.warning("⚠️ Discord 서비스가 비활성화되어 있습니다.")

            # 6. MCP 관련 초기화 제거
            self._mcp_manager = None
            self._mcp_fallback_manager = None

            # 7. FastAPI 라우트 설정
            self._setup_web_routes()

            # 8. 글로벌 예외 핸들러 설정
            self._setup_exception_handlers()

            # 9. 자동 관리 작업 시작
            await self._start_auto_tasks()

            # 10. 실시간 모니터링 시작
            await start_realtime_performance_monitoring()

            self.service_ready = True
            logger.info("✅ 전체 시스템 초기화 완료")
            return True

        except Exception as initialization_error:
            logger.error(f"❌ 시스템 초기화 실패: {initialization_error}")
            await self.shutdown_system()
            raise

    async def shutdown_system(self) -> bool:
        """전체 시스템을 안전하게 종료"""
        logger.info("🔄 시스템 종료 프로세스 시작")

        try:
            # 자동 작업들 취소
            if self.auto_tasks:
                logger.info("⏹️ 백그라운드 작업들 종료 중...")
                for task in self.auto_tasks:
                    if not task.done():
                        task.cancel()
                try:
                    await asyncio.gather(*self.auto_tasks, return_exceptions=True)
                except asyncio.CancelledError:
                    pass  # 취소된 작업들은 정상

            # Notion 동기화 서비스 종료
            logger.info("🔄 Notion 동기화 서비스 종료 중...")
            sync_service = self._service_manager.get_service("sync")
            if sync_service:
                await sync_service.stop_synchronization_monitor()

            # Discord 봇 종료 (HTTP 세션 정리 포함)
            logger.info("🤖 Discord 봇 종료 중...")
            try:
                discord_service = self._service_manager.get_service("discord")
                await discord_service.stop_bot()

                # Discord 봇의 HTTP 세션 정리 (더 안전한 방법)
                try:
                    if (
                        hasattr(discord_service.bot, "http")
                        and discord_service.bot.http
                    ):
                        await discord_service.bot.http.close()
                        logger.debug("🔐 Discord HTTP 세션 정리 완료")
                except Exception as session_cleanup_error:
                    logger.warning(
                        f"⚠️ Discord HTTP 세션 정리 중 경고: {session_cleanup_error}"
                    )
            except KeyError:
                logger.warning("⚠️ Discord 서비스가 비활성화되어 있습니다.")

            # MongoDB 연결 종료
            logger.info("🗄️ MongoDB 연결 종료 중...")
            try:
                disconnect_result = mongodb_connection.disconnect()
                if disconnect_result is not None:
                    await disconnect_result
                logger.info("🗄️ MongoDB 연결 종료 완료")
            except Exception as mongo_error:
                logger.warning(f"⚠️ MongoDB 연결 종료 중 경고: {mongo_error}")

            logger.info("👋 DinoBot 시스템 종료 완료")
            return True

        except Exception as shutdown_error:
            logger.error(f"❌ 시스템 종료 중 에러: {shutdown_error}")
            return False

    async def check_service_status(self) -> SystemStatusDTO:
        """전체 서비스 상태를 확인"""
        try:
            # MongoDB 상태 확인
            mongo_status = await mongodb_connection.mongo_client.admin.command("ping")
            mongo_response_time = 1.0  # 실제로는 ping 시간 측정

            # Discord 봇 상태 확인
            discord_status = (
                await self.discord_service.check_bot_status()
                if self.discord_service
                else {"ready": False, "response_time": 0.0}
            )

            # 업타임 계산
            uptime_seconds = (
                (datetime.now(settings.tz) - self.start_time).total_seconds()
                if self.start_time
                else 0
            )

            # 서비스 상태 리스트 생성
            service_status_list = [
                ServiceStatusDTO(
                    service_name="MongoDB",
                    is_healthy=mongodb_connection.connection_status,
                    response_time_ms=mongo_response_time,
                    error_message=(
                        None
                        if mongodb_connection.connection_status
                        else "MongoDB connection failed"
                    ),
                ),
                ServiceStatusDTO(
                    service_name="Discord Bot",
                    is_healthy=discord_status.get("ready", False),
                    response_time_ms=discord_status.get("response_time", 0.0),
                    error_message=(
                        None if discord_status.get("ready") else "Discord bot not ready"
                    ),
                ),
            ]

            # MongoDB 상태 생성
            mongodb_status = MongoDBStatusDTO(
                is_connected=mongodb_connection.connection_status,
                database_name="meetuploader",  # 실제 DB 이름
                collections_count=0,  # 실제로는 db.list_collection_names() 호출
            )

            # 서비스 상태를 딕셔너리로 변환
            services_dict = {
                service.service_name: service for service in service_status_list
            }

            return SystemStatusDTO(
                status="healthy" if self.service_ready else "initializing",
                uptime_seconds=int(uptime_seconds),
                services=services_dict,
                mongodb=mongodb_status,
            )

        except Exception as status_check_error:
            logger.error(f"❌ 서비스 상태 확인 실패: {status_check_error}")
            # 에러 시 빈 서비스 리스트와 기본 MongoDB 상태
            mongodb_status = MongoDBStatusDTO(
                is_connected=False,
                database_name="meetuploader",
                collections_count=0,
            )

            return SystemStatusDTO(
                status="critical",
                uptime_seconds=0,
                services={},
                mongodb=mongodb_status,
            )

    # ===== 비즈니스 로직 구현 =====

    def _generate_unique_title(self, base_title: str) -> str:
        """제목에 시간 구분자를 추가하여 중복 방지"""
        now = datetime.now(settings.tz)
        time_suffix = now.strftime("%H:%M")
        return f"{base_title} ({time_suffix})"

    async def _process_command_business_logic(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """디스코드 명령어의 비즈니스 로직 처리"""
        try:
            # 워크플로우 서비스를 통한 명령어 처리
            if request.command_type == CommandType.TASK:
                task_service = self._service_manager.get_workflow_service("task")
                return await task_service.create_task(request)
            elif request.command_type == CommandType.MEETING:
                meeting_service = self._service_manager.get_workflow_service("meeting")
                return await meeting_service.create_meeting(request)
            elif request.command_type == CommandType.DOCUMENT:
                document_service = self._service_manager.get_workflow_service(
                    "document"
                )
                return await document_service.create_document(request)
            # 기존 워크플로우들은 기존 메서드 유지
            elif request.command_type == CommandType.STATUS:
                return await self._status_check_workflow(request)
            elif request.command_type == CommandType.FETCH_PAGE:
                return await self._fetch_page_workflow(request)
            elif request.command_type == CommandType.WATCH_PAGE:
                return await self._watch_page_workflow(request)
            elif request.command_type == CommandType.HELP:
                return await self._help_workflow(request)
            elif request.command_type == CommandType.DAILY_STATS:
                return await self._daily_stats_workflow(request)
            elif request.command_type == CommandType.WEEKLY_STATS:
                return await self._weekly_stats_workflow(request)
            elif request.command_type == CommandType.MONTHLY_STATS:
                return await self._monthly_stats_workflow(request)
            elif request.command_type == CommandType.USER_STATS:
                return await self._user_stats_workflow(request)
            elif request.command_type == CommandType.TEAM_STATS:
                return await self._team_stats_workflow(request)
            elif request.command_type == CommandType.TRENDS:
                return await self._trends_workflow(request)
            elif request.command_type == CommandType.TASK_STATS:
                return await self._task_stats_workflow(request)
            elif request.command_type == CommandType.SEARCH:
                return await self._search_workflow(request)
            # CRUD Update/Archive 워크플로우들
            elif request.command_type == CommandType.UPDATE_TASK:
                return await self._update_task_workflow(request)
            elif request.command_type == CommandType.UPDATE_MEETING:
                return await self._update_meeting_workflow(request)
            elif request.command_type == CommandType.UPDATE_DOCUMENT:
                return await self._update_document_workflow(request)
            elif request.command_type == CommandType.ARCHIVE_PAGE:
                return await self._archive_page_workflow(request)
            elif request.command_type == CommandType.RESTORE_PAGE:
                return await self._restore_page_workflow(request)
            elif request.command_type == CommandType.CAREEROS_ONBOARD:
                return await self._careeros_onboard_workflow(request)
            elif request.command_type == CommandType.CAREEROS_STATUS:
                return await self._careeros_status_workflow(request)
            elif request.command_type == CommandType.CAREEROS_RESTART:
                return await self._careeros_restart_workflow(request)
            else:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content=f"❌ 지원하지 않는 명령어: {request.command_type}",
                    is_ephemeral=True,
                )

        except Exception as processing_error:
            logger.error(f"❌ 명령어 비즈니스 로직 처리 실패: {processing_error}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 명령어 처리 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def _task_creation_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """태스크 생성 전체 워크플로우"""
        try:
            # 1. 필수 파라미터 검증
            base_title = request.parameters.get("title") or request.parameters.get("name")
            person = request.parameters.get("person") or request.parameters.get("assignee")

            if not base_title:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 태스크 제목이 필요합니다. (title 또는 name 파라미터 필요)",
                    is_ephemeral=True,
                )

            if not person:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 담당자(person 또는 assignee)가 필요합니다. 사용 가능한 값: 소현, 정빈, 동훈",
                    is_ephemeral=True,
                )

            # 담당자 유효성 검증
            valid_persons = ["소현", "정빈", "동훈"]
            if person not in valid_persons:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content=f"❌ 올바른 담당자를 선택해주세요: {', '.join(valid_persons)}",
                    is_ephemeral=True,
                )

            # 2. 태스크 생성 request DTO 구성 (시간 구분자 추가)
            unique_title = self._generate_unique_title(base_title)

            task_request = TaskCreateRequestDTO(
                assignee=person,
                task_name=unique_title,
                priority=request.parameters.get("priority", "Medium"),
                due_date=request.parameters.get("deadline"),
            )

            # 2. 기존 Notion 서비스를 통한 태스크 생성
            with logger_manager.performance_logger("notion_task_creation"):
                # due_date 파싱
                due_date = task_request.due_date
                if due_date and isinstance(due_date, str):
                    try:
                        due_date = datetime.fromisoformat(due_date)
                    except:
                        due_date = datetime.now() + timedelta(days=7)
                elif not due_date:
                    # 기본값: 오늘 마감
                    due_date = datetime.now().replace(
                        hour=23, minute=59, second=59, microsecond=0
                    )

                # Due date 지표 생성
                def get_due_date_indicator(due_date: datetime) -> str:
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

                due_date_indicator = get_due_date_indicator(due_date)

                notion_result = await self._notion_service.create_factory_task(
                    task_name=task_request.task_name,
                    assignee=task_request.assignee,
                    priority=task_request.priority,
                    due_date=due_date,
                    task_type=task_request.task_type,
                    description=task_request.description,
                )

                # 3. 생성된 페이지 정보를 데이터베이스에 저장
                try:
                    await save_notion_page(
                        page_id=notion_result.get("id", ""),
                        database_id=settings.factory_tracker_db_id,  # Factory Tracker DB ID
                        page_type="task",
                        title=task_request.task_name,
                        created_by=str(request.user.user_id),
                        metadata={
                            "assignee": task_request.assignee,
                            "priority": task_request.priority,
                            "due_date": task_request.due_date,
                            "discord_user": request.user.username,
                        },
                    )
                except Exception as save_error:
                    logger.warning(f"⚠️ 페이지 정보 저장 실패 (계속 진행): {save_error}")

            # 3. 당일 스레드에 태스크 생성 알림 전송
            # Discord 명령어에서 자동으로 channel_id 추출
            channel_id = request.guild.channel_id if request.guild else None
            logger.info(
                f"🔍 추출된 channel_id: {channel_id} (guild_id: {request.guild.guild_id if request.guild else None})"
            )

            if channel_id:
                thread_info = await self._discord_service.get_or_create_daily_thread(
                    channel_id, title=task_request.task_name
                )
            else:
                # channel_id가 없는 경우 기본 채널 사용
                default_channel_id = getattr(
                    settings, "discord_channel_id", None
                ) or getattr(settings, "default_discord_channel_id", None)
                if default_channel_id:
                    thread_info = (
                        await self._discord_service.get_or_create_daily_thread(
                            default_channel_id, title=task_request.task_name
                        )
                    )
                else:
                    # 기본 채널도 없으면 스레드 생성 건너뛰기
                    logger.warning("Discord 채널 ID가 설정되지 않아 스레드 생성 건너뜀")
                    # 스레드 없이도 계속 진행
                    thread_info = None

            # 4. 스레드에 알림 전송
            if thread_info:
                page_url = await self._notion_service.extract_page_url(notion_result)
                task_notification = (
                    f"🎯 **새 태스크 생성됨**\n\n"
                    f"👤 **담당자**: {task_request.assignee}\n"
                    f"📝 **제목**: {task_request.task_name}\n"
                    f"⚡ **우선순위**: {task_request.priority}\n"
                    f"🔗 **노션 링크**: {page_url}\n\n"
                    f"💡 페이지 ID: `{notion_result.get('id', 'N/A')}`\n"
                    f"📋 `/fetch page_id:{notion_result.get('id', 'N/A')}`로 내용을 확인할 수 있습니다."
                )

                # 기존 Discord 서비스를 통한 알림 전송
                await self._discord_service.send_thread_message(
                    thread_info.thread_id, task_notification
                )

            # 4. 성공 응답 생성
            formatted_due_date = due_date.strftime("%Y-%m-%d %H:%M")
            page_url = notion_result.get("url", "https://notion.so")
            response_content = (
                f"✅ **태스크 생성 완료**\n"
                f"👤 **담당자**: `{task_request.assignee}`\n"
                f"📝 **제목**: `{base_title}` → `{task_request.task_name}`\n"
                f"⚡ **우선순위**: `{task_request.priority}`\n"
                f"📅 **마감일**: `{formatted_due_date}` {due_date_indicator}\n"
                f"🔗 **노션 링크**: {page_url}\n\n"
                f"📢 스레드에 알림이 전송되었습니다!"
            )

            if task_request.due_date:
                response_content += f"\n📅 **due_date**: `{task_request.due_date}`"

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                title="태스크 생성 완료",
                content=response_content,
                is_embed=True,
                is_ephemeral=True,
            )

        except Exception as task_error:
            logger.error(f"❌ 태스크 생성 워크플로우 실패: {task_error}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 태스크 생성 실패: {str(task_error)}",
                is_ephemeral=True,
            )

    async def _meeting_creation_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """회의록 생성 전체 워크플로우"""
        try:
            # 1. 필수 파라미터 검증
            base_title = request.parameters.get("title") or request.parameters.get("name")
            meeting_time = request.parameters.get("meeting_date")
            participants = request.parameters.get("participants", [])

            if not base_title:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 회의록 제목이 필요합니다.",
                    is_ephemeral=True,
                )

            if not meeting_time:
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

            # 참석자 리스트 정규화 (문자열을 리스트로 변환)
            if isinstance(participants, str):
                participants = [p.strip() for p in participants.split(",")]

            # 참석자 유효성 검증
            valid_persons = ["소현", "정빈", "동훈"]
            invalid_participants = [p for p in participants if p not in valid_persons]
            if invalid_participants:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content=f"❌ 올바른 참석자를 선택해주세요.\n"
                    f"잘못된 참석자: {', '.join(invalid_participants)}\n"
                    f"사용 가능한 값: {', '.join(valid_persons)}",
                    is_ephemeral=True,
                )

            # 2. 회의록 생성 request DTO 구성 (시간 구분자 추가)
            unique_title = self._generate_unique_title(base_title)

            meeting_request = MeetingCreateRequestDTO(
                title=unique_title,
                meeting_type=request.parameters.get("meeting_type", "정기회의"),
                attendees=participants,
            )

            # 2. 기존 Notion 서비스를 통한 회의록 생성
            with logger_manager.performance_logger("notion_meeting_creation"):
                notion_result = await self._notion_service.create_meeting_page(
                    title=meeting_request.title,
                    participants=meeting_request.attendees,
                )

                # 페이지 URL 추출
                page_url = notion_result.get("url", "https://notion.so")

                # 3. 생성된 페이지 정보를 데이터베이스에 저장
                try:
                    await save_notion_page(
                        page_id=notion_result.get("id", ""),
                        database_id=settings.board_db_id,  # Board DB ID
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

            # 3. Discord 이벤트 생성 (회의 일정이 있는 경우)
            meeting_date_str = request.parameters.get("meeting_date")
            discord_event_created = False
            if meeting_date_str:
                try:
                    # 문자열 날짜를 datetime 객체로 변환
                    from datetime import datetime, timedelta

                    meeting_datetime = None
                    now = datetime.now()

                    # 1. 상대적 날짜 표현 처리
                    if "오늘" in meeting_date_str:
                        time_part = meeting_date_str.replace("오늘", "").strip()
                        if time_part:
                            # 시간이 있는 경우 (예: "오늘 16:30")
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
                                    time_obj = datetime.strptime(
                                        meeting_date_str, fmt
                                    ).time()
                                    meeting_datetime = now.replace(
                                        hour=time_obj.hour,
                                        minute=time_obj.minute,
                                        second=0,
                                        microsecond=0,
                                    )
                                else:
                                    parsed_date = datetime.strptime(
                                        meeting_date_str, fmt
                                    )
                                    # 년도가 없는 형식인 경우 현재 년도 사용
                                    if fmt in ["%m/%d %H:%M", "%m/%d"]:
                                        parsed_date = parsed_date.replace(year=now.year)
                                    # 시간이 없는 형식인 경우 14:00으로 기본 설정
                                    if fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m/%d"]:
                                        parsed_date = parsed_date.replace(
                                            hour=14, minute=0
                                        )
                                    meeting_datetime = parsed_date
                                break
                            except ValueError:
                                continue

                    if meeting_datetime:
                        # Discord 이벤트 생성
                        event_title = f"📝 {meeting_request.title}"
                        event_description = (
                            f"회의 유형: {meeting_request.meeting_type}\n"
                            f"참석자: {', '.join(meeting_request.attendees)}\n\n"
                            f"노션 페이지: {page_url}"
                        )

                        discord_event_created = (
                            await self._discord_service.create_discord_event(
                                title=event_title,
                                description=event_description,
                                start_time=meeting_datetime,
                                duration_hours=1,
                                voice_channel_name="내 회의실",
                            )
                        )

                        if discord_event_created:
                            logger.info(f"✅ Discord 이벤트 생성 완료: {event_title}")
                        else:
                            logger.warning(f"⚠️ Discord 이벤트 생성 실패: {event_title}")

                    else:
                        logger.warning(
                            f"⚠️ 날짜 형식을 인식할 수 없습니다: {meeting_date_str}"
                        )
                        # 날짜 형식이 잘못된 경우에도 회의록 생성은 계속하되 이벤트만 생성하지 않음

                except Exception as event_error:
                    logger.warning(
                        f"⚠️ Discord 이벤트 생성 실패 (계속 진행): {event_error}"
                    )

            # 4. 당일 스레드에 안내 메시지 전송
            channel_id = request.guild.channel_id or settings.default_discord_channel_id
            if channel_id:
                try:
                    thread_info = (
                        await self._discord_service.get_or_create_daily_thread(
                            channel_id, title=meeting_request.title
                        )
                    )
                    guide_message = self._generate_meeting_guide_message(
                        meeting_request.title, page_url, notion_result.get("id")
                    )
                    await self._discord_service.send_thread_message(
                        thread_info.thread_id, guide_message
                    )
                except Exception as thread_error:
                    logger.warning(f"⚠️ 스레드 메시지 전송 실패: {thread_error}")

            # 5. 성공 응답 생성
            response_content = (
                f"✅ **회의록 생성 완료**\n"
                f"📝 **제목**: `{base_title}` → `{meeting_request.title}`\n"
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

        except Exception as meeting_error:
            logger.error(f"❌ 회의록 생성 워크플로우 실패: {meeting_error}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 회의록 생성 실패: {str(meeting_error)}",
                is_ephemeral=True,
            )

    async def _document_creation_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """문서 생성 워크플로우 (Board DB)"""
        try:
            # 요청에서 필수 파라미터 추출
            title = request.parameters.get("title") or request.parameters.get("name")
            doc_type = request.parameters.get("doc_type", "개발 문서")  # 기본값

            if not title:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 문서 제목이 필요합니다.",
                    is_ephemeral=True,
                )

            # 문서 타입 유효성 검증 (Notion의 실제 Status 옵션과 일치)
            valid_doc_types = ["개발 문서", "기획안", "개발 규칙", "회의록"]
            if doc_type not in valid_doc_types:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content=f"❌ 올바른 문서 타입을 선택해주세요.\n"
                    f"잘못된 타입: {doc_type}\n"
                    f"사용 가능한 값: {', '.join(valid_doc_types)}",
                    is_ephemeral=True,
                )

            # 고유한 제목 생성
            unique_title = self._generate_unique_title(title)

            # 기존 Notion 서비스를 통한 문서 생성
            with logger_manager.performance_logger("notion_document_creation"):
                notion_result = await self._notion_service.create_document_page(
                    title=unique_title, doc_type=doc_type
                )

                # 페이지 URL 추출
                page_url = notion_result.get("url", "https://notion.so")

                # 생성된 페이지 정보를 데이터베이스에 저장
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

            # 당일 스레드에 문서 생성 알림 전송
            thread_info = await self._discord_service.get_or_create_daily_thread(
                request.channel_id, title=unique_title
            )

            document_notification = (
                f"📄 **새 문서 생성됨**\n\n"
                f"📝 **제목**: {unique_title}\n"
                f"📂 **유형**: {doc_type}\n"
                f"👤 **작성자**: {request.user.username}\n"
                f"🔗 **노션 링크**: {page_url}\n\n"
                f"💡 이제 해당 문서에 내용을 작성해보세요!"
            )

            await self._discord_service.send_thread_message(
                thread_info.thread_id, document_notification
            )

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                title="문서 생성 완료",
                content=f"📄 문서 '{unique_title}'이 생성되었습니다!\n🔗 <#{thread_info.thread_id}>",
                is_embed=True,
                is_ephemeral=True,
            )

        except Exception as document_error:
            logger.error(f"❌ 문서 생성 워크플로우 실패: {document_error}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 문서 생성 실패: {str(document_error)}",
                is_ephemeral=True,
            )

    async def _fetch_page_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """노션 페이지 내용 가져오기 워크플로우"""
        try:
            page_id = request.parameters.get("page_id")
            channel_id = request.parameters.get("channel_id")

            # 페이지 정보 변수 초기화
            recent_page = None
            page_title = None
            page_type = None

            # page_id가 없으면 사용자의 최근 생성 페이지를 가져옴
            if not page_id:
                logger.info(
                    f"📖 사용자 {request.user.username}의 최근 페이지 조회 중..."
                )
                recent_page = await get_recent_notion_page_by_user(
                    str(request.user.user_id)
                )

                if not recent_page:
                    return DiscordMessageResponseDTO(
                        message_type=MessageType.ERROR_NOTIFICATION,
                        content="❌ 최근에 생성한 노션 페이지를 찾을 수 없습니다.\n💡 `/task` 또는 `/meeting` 명령어로 페이지를 먼저 생성하거나, 직접 page_id를 입력해주세요.",
                        is_ephemeral=True,
                    )

                page_id = recent_page["page_id"]
                page_title = recent_page.get("title", "제목 없음")
                page_type = recent_page.get("page_type", "unknown")
                logger.info(
                    f"📄 최근 페이지 사용: {page_title} ({page_type}) (ID: {page_id})"
                )

            # 1. 기존 Notion 서비스를 통한 페이지 내용 추출
            with logger_manager.performance_logger("notion_page_extraction"):
                page_text = await self._notion_service.extract_page_text(page_id)

            # 2. 원본 텍스트를 Discord 메시지 형태로 포맷팅 및 분할
            if channel_id:
                # channel_id를 int로 변환 (실제로는 thread_id)
                thread_id_int = int(channel_id)
                logger.info(
                    f"🔧 fetch 워크플로우: 전달받은 ID={channel_id} -> {thread_id_int}"
                )
                logger.info(f"📋 이 ID는 기존에 생성된 스레드 ID로 추정됨")

                # 스레드 정보 구성 (기존 스레드 사용)
                from types import SimpleNamespace

                thread_info = SimpleNamespace(thread_id=thread_id_int)
                logger.info(f"✅ 기존 스레드 사용: thread_id={thread_info.thread_id}")

                if page_text.strip():
                    # 헤더 메시지 먼저 전송
                    header_message = (
                        f"📝 **노션 페이지 내용** (페이지 ID: `{page_id}`)\n"
                    )
                    await self._discord_service.send_thread_message(
                        thread_info.thread_id, header_message
                    )

                    # 긴 내용을 설정된 크기로 분할해서 전송
                    max_length = settings.discord_message_chunk_size
                    text_parts = []

                    if len(page_text) <= max_length:
                        text_parts = [page_text]
                    else:
                        # 줄 단위로 분할하여 자연스럽게 나누기
                        lines = page_text.split("\n")
                        current_part = ""

                        for line in lines:
                            if len(current_part + line + "\n") <= max_length:
                                current_part += line + "\n"
                            else:
                                if current_part:
                                    text_parts.append(current_part.rstrip())
                                current_part = line + "\n"

                        if current_part:
                            text_parts.append(current_part.rstrip())

                    # 각 부분을 순차적으로 전송
                    for i, part in enumerate(text_parts):
                        if len(text_parts) > 1:
                            part_message = f"**[{i+1}/{len(text_parts)}]**\n{part}"
                        else:
                            part_message = part

                        await self._discord_service.send_thread_message(
                            thread_info.thread_id, part_message
                        )
                else:
                    # 빈 페이지 처리
                    empty_message = (
                        "📝 **노션 페이지 내용**\n\n*(페이지 내용이 비어있습니다)*"
                    )
                    await self._discord_service.send_thread_message(
                        thread_info.thread_id, empty_message
                    )

                # 사용된 페이지 정보 추가
                page_info = ""
                if recent_page and page_title:
                    page_info = f"\n📄 **페이지**: {page_title} ({page_type})"
                elif page_id:
                    page_info = f"\n📄 **페이지 ID**: {page_id}"

                return DiscordMessageResponseDTO(
                    message_type=MessageType.SUCCESS_NOTIFICATION,
                    content=f"✅ 노션 페이지 내용을 스레드로 전송했습니다.{page_info}",
                    is_ephemeral=True,
                )
            else:
                # channel_id가 없는 경우, 응답으로 직접 전송 (길이 제한 적용)
                if page_text.strip():
                    formatted_message = f"📝 **노션 페이지 내용**\n\n{page_text}"

                    # Discord 응답 길이 제한 (4000자) 처리
                    if len(formatted_message) > 3800:
                        formatted_message = (
                            formatted_message[:3800]
                            + "\n\n... *(내용이 길어서 일부만 표시됩니다. 전체 내용은 스레드를 확인하세요)*"
                        )
                else:
                    formatted_message = (
                        "📝 **노션 페이지 내용**\n\n*(페이지 내용이 비어있습니다)*"
                    )

                return DiscordMessageResponseDTO(
                    message_type=MessageType.SUCCESS_NOTIFICATION,
                    content=formatted_message,
                    is_ephemeral=False,
                )

        except Exception as fetch_error:
            logger.error(f"❌ 노션 페이지 가져오기 실패: {fetch_error}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 페이지 가져오기 실패: {str(fetch_error)}",
                is_ephemeral=True,
            )

    async def _help_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """명령어 도움말 워크플로우"""
        help_content = (
            "🤖 **노션봇 사용 가이드**\n\n"
            "**📝 태스크 관리**\n"
            "> `/task person:[담당자] name:[제목] priority:[우선순위]`\n"
            "> • **담당자**: 소현, 정빈, 동훈 중 선택 (필수)\n"
            "> • **제목**: 태스크 제목 (필수)\n"
            "> • **우선순위**: High, Medium, Low 중 선택 (선택사항)\n"
            "> • **예시**: `/task person:정빈 name:버그수정 priority:High`\n\n"
            "**📋 회의록 관리**\n"
            "> `/meeting title:[제목] participants:[참석자]`\n"
            "> • **제목**: 회의록 제목 (필수)\n"
            "> • **참석자**: 소현, 정빈, 동훈 중 선택 (필수)\n"
            "> • **예시**: `/meeting title:주간회의 participants:정빈,소현`\n\n"
            "**📄 문서 생성**\n"
            "> `/document title:[제목] doc_type:[문서타입]`\n"
            "> • **문서타입**: 개발 문서, 기획안, 개발 규칙, 회의록\n"
            "> • **예시**: `/document title:API설계서 doc_type:개발 문서`\n\n"
            "**📄 페이지 내용 가져오기**\n"
            "> `/fetch page_id:[노션페이지ID]`\n"
            "> • 노션 페이지의 원본 내용을 스레드로 가져옵니다\n"
            "> • page_id 미입력 시 최근 생성된 페이지 자동 선택\n"
            "> • **예시**: `/fetch` 또는 `/fetch page_id:abc123def456...`\n\n"
            "**🔍 페이지 검색**\n"
            "> `/search query:[키워드] page_type:[타입] user:[사용자] days:[일수]`\n"
            "> • **타입**: task, meeting, document, all (기본값: all)\n"
            "> • **연관 검색어, 인기 검색어 자동 제안**\n"
            "> • **예시**: `/search query:API page_type:document`\n\n"
            "**📊 통계 조회**\n"
            "> `/daily_stats [user:사용자]` - 일별 통계 (차트 포함)\n"
            "> `/weekly_stats [user:사용자]` - 주별 통계 (차트 포함)\n"
            "> `/monthly_stats [user:사용자]` - 월별 통계 (차트 포함)\n"
            "> `/user_stats user:사용자` - 사용자별 생산성 통계\n"
            "> `/team_stats` - 팀 전체 통계 및 협업 분석\n"
            "> `/trends [days:일수]` - 활동 트렌드 분석 (기본 14일)\n"
            "> `/task_stats [user:사용자] [status:상태]` - 태스크 완료율 통계\n\n"
            "**👁️ 페이지 감시**\n"
            "> `/watch page_id:[노션페이지ID] interval:[간격]`\n"
            "> • 노션 페이지 변경사항을 주기적으로 확인 (개발 중)\n"
            "> • **간격**: 분 단위 (기본 30분)\n\n"
            "**🔧 시스템 정보**\n"
            "> `/status` - 봇과 시스템 상태 확인\n"
            "> `/help` - 이 도움말 표시\n\n"
            "**💡 팁**\n"
            "> • 모든 알림은 당일 스레드에 자동으로 전송됩니다\n"
            "> • 페이지 생성 시 페이지 ID가 자동으로 제공됩니다\n"
            "> • 검색 시 연관 검색어와 인기 검색어가 자동 제안됩니다\n"
            "> • 통계는 차트 이미지로 시각화되어 제공됩니다\n\n"
            "**📊 데이터베이스**\n"
            "> • **Factory Tracker**: 태스크 관리\n"
            "> • **Board**: 회의록 및 문서 관리"
        )

        return DiscordMessageResponseDTO(
            message_type=MessageType.SUCCESS_NOTIFICATION,
            content=help_content,
            is_embed=True,
            is_ephemeral=True,
            title="노션봇 명령어 가이드",
        )

    async def _status_check_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """시스템 상태 확인 워크플로우"""
        try:
            # 실시간 대시보드 데이터 생성
            dashboard_data = (
                await get_mongodb_analysis_service().generate_realtime_dashboard_data()
            )

            # 명령어 통계 요약
            command_stats = dashboard_data.get("command_stats", {})
            total_commands = command_stats.get("total_commands", 0)
            average_success_rate = command_stats.get("average_success_rate", 0)

            # 응답 시간 통계 요약
            response_time_analysis = dashboard_data.get("response_time_analysis", {})
            average_response_time = response_time_analysis.get(
                "overall_average_response_time", 0
            )

            # 캐시 성능 요약
            cache_performance = dashboard_data.get("cache_performance", {})
            schema_cache_count = cache_performance.get("schema_cache", {}).get(
                "total_cache_count", 0
            )
            thread_cache_count = cache_performance.get("thread_cache", {}).get(
                "total_thread_count", 0
            )

            status_message = (
                f"🤖 **DinoBot 시스템 상태**\n\n"
                f"📊 **최근 1시간 통계**\n"
                f"• 명령어 실행: `{total_commands}회`\n"
                f"• 평균 성공률: `{average_success_rate:.1f}%`\n"
                f"• 평균 응답시간: `{average_response_time:.3f}초`\n\n"
                f"💾 **캐시 현황**\n"
                f"• 스키마 캐시: `{schema_cache_count}개`\n"
                f"• 스레드 캐시: `{thread_cache_count}개`\n\n"
                f"⚡ **서비스 상태**\n"
                f"• MongoDB: `{'✅ 정상' if mongodb_connection.connection_status else '❌ 오류'}`\n"
                f"• Discord Bot: `{'✅ 정상' if self._discord_service.ready else '❌ 오류'}`\n"
                f"• MCP 시스템: `❌ 비활성`\n"
                f"• 폴백 횟수: `0회`"
            )

            return DiscordMessageResponseDTO(
                message_type=MessageType.SYSTEM_STATUS,
                title="시스템 상태 대시보드",
                content=status_message,
                is_embed=True,
                is_ephemeral=True,
            )

        except Exception as status_error:
            logger.error(f"❌ 상태 확인 워크플로우 실패: {status_error}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 시스템 상태 확인 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    def _generate_meeting_guide_message(
        self, title: str, URL: str, page_id: str = None
    ) -> str:
        """회의록 생성 안내 메시지 템플릿"""
        base_message = (
            f"📌 **회의록 페이지 생성 완료**\n"
            f"🔗 **링크**: {URL}\n"
            f"📝 **title**: {title}\n"
        )

        if page_id:
            base_message += f"💡 **페이지 ID**: `{page_id}`\n"
            base_message += f"📋 **내용 확인**: `/fetch page_id:{page_id}`\n"

        base_message += (
            f"\n**📋 작성 가이드**\n"
            f"> • **Agenda**: 회의 주제 및 목표\n"
            f"> • **Discussion**: 주요 논의 content\n"
            f"> • **Decisions**: 확정된 결정 사항들\n"
            f"> • **Action Items**: assignee별 할 일과 due_date\n\n"
            f"✨ 작성 완료 후 `/fetch` 명령어로 내용을 이 스레드로 가져올 수 있습니다!"
        )

        return base_message

    # ===== FastAPI 라우트 설정 =====

    def _setup_web_routes(self):
        """FastAPI 웹 라우트들을 설정"""

        # 설정 관리 API 추가
        try:
            from src.api.config_api import router as config_router

            self.web_application.include_router(config_router)
            logger.info("✅ 설정 관리 API 라우트 등록 완료")
        except ImportError as e:
            logger.warning(f"⚠️ 설정 관리 API 라우트 등록 실패: {e}")

        @self.web_application.post("/notion/webhook")
        async def notion_webhook_handler(
            request: Request, x_webhook_secret: str = Header(default="")
        ):
            """노션 웹훅 request 처리"""
            # 웹훅 시크릿 검증
            if x_webhook_secret != settings.webhook_secret:
                logger.warning(
                    f"🔒 웹훅 인증 실패: {request.client.host if request.client else 'Unknown'}"
                )
                raise HTTPException(
                    status_code=401, detail="Unauthorized webhook secret"
                )

            start_time = datetime.now()

            try:
                # request 본문 파싱
                webhook_data = await request.json()
                webhook_request = NotionWebhookRequestDTO(
                    page_id=webhook_data.get("page_id"),
                    channel_id=int(
                        webhook_data.get("channel_id")
                        or settings.default_discord_channel_id
                        or 0
                    ),
                    mode=webhook_data.get("mode", "meeting"),
                    custom_message=webhook_data.get("custom_message"),
                    request_ip=request.client.host if request.client else None,
                )

                if not webhook_request.page_id or not webhook_request.channel_id:
                    raise UserInputException("페이지 ID 또는 채널 ID가 누락되었습니다")

                # 웹훅 처리 워크플로우 실행
                process_result = await self._webhook_summary_workflow(
                    webhook_request, start_time
                )

                return JSONResponse(
                    {
                        "success": process_result.success,
                        "page_id": process_result.page_id,
                        "text_length": process_result.text_length,
                        "discord_sent": process_result.discord_message_sent,
                        "thread_id": process_result.thread_id,
                        "processing_time_ms": process_result.processing_time_ms,
                        "error_code": process_result.error_code,
                    }
                )

            except Exception as webhook_error:
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.error(f"❌ 웹훅 처리 실패: {webhook_error}")
                return JSONResponse(
                    {
                        "success": False,
                        "error": str(webhook_error),
                        "processing_time_ms": processing_time * 1000,
                    },
                    status_code=500,
                )

        @self.web_application.get("/health")
        async def health_check():
            """서비스 상태 확인 엔드포인트"""
            status_info = await self.check_service_status()
            return {
                "status": status_info.status,
                "uptime_seconds": status_info.uptime_seconds,
                "services": {
                    name: service.model_dump()
                    for name, service in status_info.services.items()
                },
                "mongodb": (
                    status_info.mongodb.model_dump() if status_info.mongodb else None
                ),
                "mcp": {"mcp_enabled": False, "fallback_count": 0},
            }

        @self.web_application.post("/mcp/reset")
        async def reset_mcp():
            """MCP 재활성화 엔드포인트 (비활성화됨)"""
            return {"success": False, "message": "MCP 시스템이 비활성화되어 있습니다"}

        @self.web_application.get("/metrics/dashboard")
        async def realtime_dashboard():
            """실시간 성능 대시보드 데이터"""
            try:
                dashboard_data = (
                    await get_mongodb_analysis_service().generate_realtime_dashboard_data()
                )
                return dashboard_data
            except Exception as dashboard_error:
                return JSONResponse(
                    {"error": f"대시보드 데이터 생성 실패: {dashboard_error}"},
                    status_code=500,
                )

        @self.web_application.get("/sync/status")
        async def sync_status():
            """Notion 동기화 상태 확인"""
            try:
                sync_service = self._service_manager.get_service("sync")
                status = await sync_service.get_sync_status()
                return status
            except Exception as sync_error:
                return JSONResponse(
                    {"error": f"동기화 상태 조회 실패: {sync_error}"},
                    status_code=500,
                )

        @self.web_application.post("/sync/manual")
        async def manual_sync():
            """수동 동기화 실행"""
            try:
                sync_service = self._service_manager.get_service("sync")
                result = await sync_service.manual_sync()
                return result
            except Exception as sync_error:
                return JSONResponse(
                    {"error": f"수동 동기화 실패: {sync_error}"},
                    status_code=500,
                )

        # ── CareerOS daily digest webhook ────────────────────────────

        @self.web_application.post("/careeros/jobs/daily")
        async def careeros_digest_webhook(
            request: Request,
            x_webhook_secret: str = Header(default=""),
        ):
            """CareerOS에서 발송하는 일일 공고 다이제스트 수신 엔드포인트."""
            if x_webhook_secret != settings.careeros_webhook_secret:
                logger.warning("CareerOS digest webhook: invalid secret from %s",
                               request.client.host if request.client else "unknown")
                raise HTTPException(status_code=401, detail="Unauthorized")

            try:
                from src.dto.careeros.careeros_dtos import CareerOsJobDigestPayload
                from src.embeds.careeros_embed import build_digest_embeds_from_payload

                raw = await request.json()
                payload = CareerOsJobDigestPayload.from_dict(raw)
                embed_map = build_digest_embeds_from_payload(payload)

                channel_id = settings.digest_channel_id
                if not channel_id:
                    logger.warning("DIGEST_CHANNEL_ID not configured; skipping Discord send")
                    return {"success": True, "sent": 0}

                discord_svc = self.discord_service
                sent = 0
                if discord_svc and discord_svc.is_bot_ready:
                    channel = discord_svc.bot.get_channel(channel_id)
                    if channel:
                        for embeds in embed_map.values():
                            for embed in embeds:
                                await channel.send(embed=embed)
                            sent += 1
                    else:
                        logger.warning("Digest channel %s not found", channel_id)

                logger.info("Digest sent for %d users (date=%s)", sent, payload.digest_date)
                return {"success": True, "sent": sent, "date": payload.digest_date}

            except Exception as exc:
                logger.error("CareerOS digest webhook error: %s", exc)
                return JSONResponse({"success": False, "error": str(exc)}, status_code=500)

        # ── CareerOS MCP tools ────────────────────────────────────────

        try:
            from mcp_server.careeros_tools import careeros_mcp_router
            self.web_application.include_router(careeros_mcp_router)
            logger.info("✅ CareerOS MCP 라우트 등록 완료")
        except ImportError as e:
            logger.warning("⚠️ CareerOS MCP 라우트 등록 실패: %s", e)

    # ── CareerOS 온보딩 워크플로우 ────────────────────────────────────

    async def _careeros_onboard_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """커리어OS 온보딩 시작 워크플로우"""
        try:
            from src.conversation.onboarding_handler import onboarding_handler
            from src.conversation.state import ChannelType

            discord_user_id = request.parameters.get("discord_user_id", "")
            reply = await onboarding_handler.start(
                channel_user_id=discord_user_id,
                channel_type=ChannelType.DISCORD,
            )
            return DiscordMessageResponseDTO(
                message_type=MessageType.SUCCESS_NOTIFICATION,
                content=reply,
                is_ephemeral=False,
            )
        except Exception as exc:
            logger.error("CareerOS onboard workflow error: %s", exc)
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 온보딩 시작 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def _careeros_status_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """커리어OS CandidateGraph 상태 조회 워크플로우"""
        try:
            from src.service.careeros import careeros_client
            from src.conversation.onboarding_handler import onboarding_handler
            from src.conversation.state import ChannelType

            discord_user_id = request.parameters.get("discord_user_id", "")
            session = await onboarding_handler.get_session(discord_user_id, ChannelType.DISCORD)

            if not session or not session.careeros_user_id:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 온보딩이 완료되지 않았습니다. `/onboard` 를 먼저 실행하세요.",
                    is_ephemeral=True,
                )

            graph = await careeros_client.get_candidate_graph(session.careeros_user_id)
            status = graph.get("status", "UNKNOWN")
            content = (
                f"**커리어OS 프로필 현황**\n\n"
                f"• 상태: `{status}`\n"
                f"• GitHub: `{session.github_username or '미입력'}`\n"
                f"• 이력서: `{'업로드됨' if session.resume_id else '미업로드'}`"
            )
            return DiscordMessageResponseDTO(
                message_type=MessageType.SUCCESS_NOTIFICATION,
                content=content,
                is_embed=True,
                is_ephemeral=True,
            )
        except Exception as exc:
            logger.error("CareerOS status workflow error: %s", exc)
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 프로필 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def _careeros_restart_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """온보딩 세션 초기화 후 재시작 워크플로우"""
        try:
            from src.conversation.onboarding_handler import onboarding_handler
            from src.conversation.state import ChannelType

            discord_user_id = request.parameters.get("discord_user_id", "")
            await onboarding_handler.delete_session(discord_user_id, ChannelType.DISCORD)
            reply = await onboarding_handler.start(
                channel_user_id=discord_user_id,
                channel_type=ChannelType.DISCORD,
            )
            return DiscordMessageResponseDTO(
                message_type=MessageType.SUCCESS_NOTIFICATION,
                content=f"🔄 온보딩 세션을 초기화했습니다.\n\n{reply}",
                is_ephemeral=False,
            )
        except Exception as exc:
            logger.error("CareerOS restart workflow error: %s", exc)
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 온보딩 재시작 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def _watch_page_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """페이지 감시 워크플로우"""
        try:
            page_id = request.parameters.get("page_id")
            interval = request.parameters.get("interval", 30)  # 기본 30분
            channel_id = request.parameters.get("channel_id")

            if not page_id:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 감시할 페이지 ID가 필요합니다.",
                    is_ephemeral=True,
                )

            # 간단한 감시 시작 알림
            return DiscordMessageResponseDTO(
                message_type=MessageType.SUCCESS_NOTIFICATION,
                content=f"👀 페이지 감시 시작: `{page_id}` (간격: {interval}분)\n"
                f"⚠️ 현재는 기본 알림만 지원됩니다.",
                is_ephemeral=True,
            )

        except Exception as e:
            logger.error(f"❌ 페이지 감시 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 페이지 감시 실패: {str(e)}",
                is_ephemeral=True,
            )

    async def _webhook_summary_workflow(
        self, request: NotionWebhookRequestDTO, start_time: datetime
    ) -> WebhookProcessResultDTO:
        """웹훅 요약 전체 워크플로우"""
        try:
            # 1. 기존 Notion 서비스를 통한 페이지 내용 추출
            with logger_manager.performance_logger("notion_page_extraction"):
                page_text = await self._notion_service.extract_page_text(
                    request.page_id
                )

            # 2. 원본 텍스트를 Discord 메시지 형태로 포맷팅 및 분할
            thread_info = await self._discord_service.get_or_create_daily_thread(
                request.channel_id, title="캐시 통계"
            )

            if page_text.strip():
                # 헤더 메시지 먼저 전송
                header_message = "📝 **노션 페이지 내용**\n"
                await self._discord_service.send_thread_message(
                    thread_info.thread_id, header_message
                )

                # 긴 내용을 설정된 크기로 분할해서 전송
                max_length = settings.discord_message_chunk_size
                text_parts = []

                if len(page_text) <= max_length:
                    text_parts = [page_text]
                else:
                    # 줄 단위로 분할하여 자연스럽게 나누기
                    lines = page_text.split("\n")
                    current_part = ""

                    for line in lines:
                        if len(current_part + line + "\n") <= max_length:
                            current_part += line + "\n"
                        else:
                            if current_part:
                                text_parts.append(current_part.rstrip())
                            current_part = line + "\n"

                    if current_part:
                        text_parts.append(current_part.rstrip())

                # 각 부분을 순차적으로 전송
                message_send_success = True
                for i, part in enumerate(text_parts):
                    if len(text_parts) > 1:
                        part_message = f"**[{i+1}/{len(text_parts)}]**\n{part}"
                    else:
                        part_message = part

                    success = await self._discord_service.send_thread_message(
                        thread_info.thread_id, part_message
                    )
                    if not success:
                        message_send_success = False
                        break
            else:
                # 빈 페이지 처리
                empty_message = (
                    "📝 **노션 페이지 내용**\n\n*(페이지 내용이 비어있습니다)*"
                )
                message_send_success = await self._discord_service.send_thread_message(
                    thread_info.thread_id, empty_message
                )

            if not message_send_success:
                raise Exception("디스코드 메시지 전송 실패")

            # 4. 처리 결과 생성
            processing_time = (datetime.now() - start_time).total_seconds()

            return WebhookProcessResultDTO(
                success=True,
                page_id=request.page_id,
                extracted_text=page_text[:500],  # 처음 500자만 저장
                text_length=len(page_text),
                discord_message_sent=True,
                thread_id=thread_info.thread_id,
                processing_time_ms=processing_time * 1000,  # 초를 밀리초로 변환
            )

        except Exception as workflow_error:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ 웹훅 요약 워크플로우 실패: {workflow_error}")

            return WebhookProcessResultDTO(
                success=False,
                page_id=request.page_id,
                extracted_text=None,
                text_length=0,
                discord_message_sent=False,
                thread_id=None,
                error_code="WEBHOOK_PROCESSING_ERROR",
                processing_time_ms=processing_time * 1000,  # 초를 밀리초로 변환
            )

    def _setup_exception_handlers(self):
        """FastAPI 글로벌 예외 핸들러 설정"""

        @self.web_application.exception_handler(Exception)
        async def global_exception_handler_wrapper(request: Request, exc: Exception):
            """모든 예외를 글로벌 핸들러로 전달"""
            return await global_exception_handler.handle_fastapi_exception(request, exc)

    async def _start_auto_tasks(self):
        """백그라운드 자동 작업들을 시작"""
        # 일일 데이터 정리 작업 (매일 새벽 2시)
        daily_cleanup_task = asyncio.create_task(self._daily_cleanup_scheduler())
        self.auto_tasks.append(daily_cleanup_task)

        # 주간 백업 작업 (매주 일요일 새벽 3시)
        weekly_backup_task = asyncio.create_task(self._weekly_backup_scheduler())
        self.auto_tasks.append(weekly_backup_task)

        # 백그라운드 자동 작업 시작 완료 (로그 제거)

    async def _daily_cleanup_scheduler(self):
        """일일 데이터 정리 스케줄러"""
        while True:
            try:
                # 24시간마다 실행
                await asyncio.sleep(24 * 60 * 60)
                await daily_auto_cleanup_task()
            except asyncio.CancelledError:
                break
            except Exception as cleanup_error:
                logger.error(f"❌ 일일 정리 스케줄러 오류: {cleanup_error}")

    async def _weekly_backup_scheduler(self):
        """주간 백업 스케줄러"""
        while True:
            try:
                # 7일마다 실행
                await asyncio.sleep(7 * 24 * 60 * 60)
                await weekly_backup_task()
            except asyncio.CancelledError:
                break
            except Exception as backup_error:
                logger.error(f"❌ 주간 백업 스케줄러 오류: {backup_error}")

    async def run_service(self):
        """Discord 봇과 FastAPI server를 동시에 실행"""
        try:
            # Discord 봇을 백그라운드 태스크로 실행 (discord 서비스가 있는 경우에만)
            bot_task = None
            if self.discord_service:
                bot_task = asyncio.create_task(
                    self.discord_service.bot.start(settings.discord_token)
                )

            # FastAPI server 실행 (메인 스레드)
            config = uvicorn.Config(
                app=self.web_application,
                host=settings.host,
                port=settings.port,
                log_config=None,  # 우리의 logger 시스템 사용
                log_level="warning",  # uvicorn 로그 레벨을 warning으로 설정
                access_log=False,  # 액세스 로그 비활성화 (너무 많은 로그 방지)
            )
            server = uvicorn.Server(config)

            logger.info(f"🌐 FastAPI server 시작: {settings.host}:{settings.port}")

            # 서버 시작 진행률 표시
            logger.info("🔄 [░░░░░░░░░░░░░░░░░░░░] 0% 서버 초기화 중...")
            await asyncio.sleep(0.1)
            logger.info("🔄 [██░░░░░░░░░░░░░░░░░░] 10% 서버 설정 완료...")
            await asyncio.sleep(0.1)
            logger.info("🔄 [████░░░░░░░░░░░░░░░░] 20% 라우트 등록 중...")
            await asyncio.sleep(0.1)
            logger.info("🔄 [██████░░░░░░░░░░░░░░] 30% 미들웨어 설정 중...")
            await asyncio.sleep(0.1)
            logger.info("🔄 [████████░░░░░░░░░░░░] 40% 서버 바인딩 중...")
            await asyncio.sleep(0.1)
            logger.info("🔄 [██████████░░░░░░░░░░] 50% 서버 준비 중...")
            await asyncio.sleep(0.1)
            logger.info("🔄 [████████████░░░░░░░░] 60% 서버 시작 중...")
            await asyncio.sleep(0.1)
            logger.info("🔄 [██████████████░░░░░░] 70% 서버 활성화 중...")
            await asyncio.sleep(0.1)
            logger.info("🔄 [████████████████░░░░] 80% 서버 대기 중...")
            await asyncio.sleep(0.1)
            logger.info("🔄 [██████████████████░░] 90% 서버 준비 완료...")
            await asyncio.sleep(0.1)
            logger.info("✅ [████████████████████] 100% DinoBot 서비스 실행 중...")

            # server 실행
            await server.serve()

        except Exception as execution_error:
            logger.error(f"❌ 서비스 실행 실패: {execution_error}")
            raise

    # ===== 통계 관련 워크플로우들 =====

    async def _daily_stats_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """일별 통계 워크플로우 (차트 포함)"""
        try:
            date_param = request.parameters.get("date")
            chart_enabled = request.parameters.get(
                "chart", True
            )  # 기본적으로 차트 생성
            target_date = datetime.now()

            if date_param:
                try:
                    target_date = datetime.strptime(date_param, "%Y-%m-%d")
                except ValueError:
                    return DiscordMessageResponseDTO(
                        message_type=MessageType.ERROR_NOTIFICATION,
                        content="❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.",
                        is_ephemeral=True,
                    )

            if chart_enabled:
                # 기존 분석 서비스를 통한 통계 생성 (차트 포함)
                analytics_service = self._service_manager.get_service("analytics")
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

                    await self._discord_service.send_thread_message(
                        thread_info.thread_id,
                        result["text_message"],
                        result["chart_path"],
                    )

                    return DiscordMessageResponseDTO(
                        message_type=MessageType.COMMAND_RESPONSE,
                        content=f"📊 일별 통계 차트가 스레드에 전송되었습니다!\n🔗 <#{thread_info.thread_id}>",
                        is_ephemeral=True,
                    )
                else:
                    # 차트 생성 실패 시 텍스트만
                    return DiscordMessageResponseDTO(
                        message_type=MessageType.COMMAND_RESPONSE,
                        content=result["text_message"]
                        + "\n\n⚠️ 차트 생성에 실패했습니다.",
                        is_ephemeral=True,
                    )
            else:
                # 기존 분석 서비스를 통한 텍스트 통계 생성
                analytics_service = self._service_manager.get_service("analytics")
                result = await analytics_service.get_daily_stats(target_date)

                if result.get("success"):
                    stats = result.get("stats", {})
                    message = result.get("message", "")
                else:
                    raise Exception(f"통계 생성 실패: {result.get('error')}")

                return DiscordMessageResponseDTO(
                    message_type=MessageType.COMMAND_RESPONSE,
                    content=message,
                    is_ephemeral=True,
                )

        except Exception as e:
            logger.error(f"❌ 일별 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def _weekly_stats_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """주별 통계 워크플로우"""
        try:
            # 기존 분석 서비스를 통한 주별 통계 생성
            analytics_service = self._service_manager.get_service("analytics")
            result = await analytics_service.get_weekly_stats()

            if result.get("success"):
                stats = result.get("stats", {})
                message = result.get("message", "")
            else:
                raise Exception(f"주별 통계 생성 실패: {result.get('error')}")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )

        except Exception as e:
            logger.error(f"❌ 주별 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def _monthly_stats_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """월별 통계 워크플로우"""
        try:
            year = request.parameters.get("year")
            month = request.parameters.get("month")

            # 기존 분석 서비스를 통한 월별 통계 생성
            analytics_service = self._service_manager.get_service("analytics")
            result = await analytics_service.get_monthly_stats(year, month)

            if result.get("success"):
                stats = result.get("stats", {})
                message = result.get("message", "")
            else:
                raise Exception(f"월별 통계 생성 실패: {result.get('error')}")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )

        except Exception as e:
            logger.error(f"❌ 월별 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def _user_stats_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """개인 통계 워크플로우"""
        try:
            days = request.parameters.get("days", 30)
            user_id = str(request.user.user_id)

            # 기존 분석 서비스를 통한 사용자 생산성 통계 생성
            analytics_service = self._service_manager.get_service("analytics")
            result = await analytics_service.get_user_productivity_stats(user_id, days)

            if result.get("success"):
                stats = result.get("stats", {})
                message = result.get("message", "")
            else:
                raise Exception(f"사용자 생산성 통계 생성 실패: {result.get('error')}")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )

        except Exception as e:
            logger.error(f"❌ 개인 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def _team_stats_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """팀 통계 워크플로우"""
        try:
            days = request.parameters.get("days", 30)

            # 기존 분석 서비스를 통한 팀 비교 통계 생성
            analytics_service = self._service_manager.get_service("analytics")
            result = await analytics_service.get_team_comparison_stats(days)

            if result.get("success"):
                stats = result.get("stats", {})
                message = result.get("message", "")
            else:
                raise Exception(f"팀 비교 통계 생성 실패: {result.get('error')}")

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

    async def _trends_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """트렌드 통계 워크플로우"""
        try:
            days = request.parameters.get("days", 14)

            # 기존 분석 서비스를 통한 활동 트렌드 통계 생성
            analytics_service = self._service_manager.get_service("analytics")
            result = await analytics_service.get_activity_trends_stats(days)

            if result.get("success"):
                stats = result.get("stats", {})
                message = result.get("message", "")
            else:
                raise Exception(f"활동 트렌드 통계 생성 실패: {result.get('error')}")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )

        except Exception as e:
            logger.error(f"❌ 트렌드 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def _task_stats_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """Task 완료 통계 워크플로우"""
        try:
            days = request.parameters.get("days", 30)

            # 기존 분석 서비스를 통한 태스크 완료 통계 생성
            analytics_service = self._service_manager.get_service("analytics")
            result = await analytics_service.get_task_completion_stats(days)

            if result.get("success"):
                stats = result.get("stats", {})
                message = result.get("message", "")
            else:
                raise Exception(f"태스크 완료 통계 생성 실패: {result.get('error')}")

            return DiscordMessageResponseDTO(
                message_type=MessageType.COMMAND_RESPONSE,
                content=message,
                is_ephemeral=True,
            )

        except Exception as e:
            logger.error(f"❌ Task 통계 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content="❌ Task 통계 조회 중 오류가 발생했습니다.",
                is_ephemeral=True,
            )

    async def _search_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """검색 워크플로우"""
        try:
            query = request.parameters.get("query")
            page_type = request.parameters.get("page_type")
            user_filter = request.parameters.get("user_filter")
            days = request.parameters.get("days", 90)

            if not query or len(query.strip()) < 2:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 검색어는 2글자 이상 입력해주세요.",
                    is_ephemeral=True,
                )

            # 기존 검색 서비스를 통한 검색 실행
            search_service = self._service_manager.get_service("search")
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

    async def _update_task_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """태스크 업데이트 워크플로우"""
        try:
            page_id = request.parameters.get("page_id")
            if not page_id:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 페이지 ID가 필요합니다.",
                    is_ephemeral=True,
                )

            notion_service = self._service_manager.get_service("notion")

            # 파라미터 추출
            title = request.parameters.get("title")
            priority = request.parameters.get("priority")
            assignee = request.parameters.get("person")
            status = request.parameters.get("status")

            # 업데이트 실행
            result = await notion_service.update_task_page(
                page_id=page_id,
                title=title,
                priority=priority,
                assignee=assignee,
                status=status
            )

            if result:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.COMMAND_RESPONSE,
                    title="태스크 업데이트 완료",
                    content=f"✅ 태스크 페이지가 성공적으로 업데이트되었습니다.\n🔗 페이지 ID: {page_id}",
                    is_embed=True,
                    is_ephemeral=True,
                )
            else:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 태스크 업데이트에 실패했습니다.",
                    is_ephemeral=True,
                )
        except Exception as e:
            logger.error(f"❌ 태스크 업데이트 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 태스크 업데이트 실패: {str(e)}",
                is_ephemeral=True,
            )

    async def _update_meeting_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """회의록 업데이트 워크플로우"""
        try:
            page_id = request.parameters.get("page_id")
            if not page_id:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 페이지 ID가 필요합니다.",
                    is_ephemeral=True,
                )

            notion_service = self._service_manager.get_service("notion")

            # 파라미터 추출
            title = request.parameters.get("title")
            participants = request.parameters.get("participants", [])
            meeting_type = request.parameters.get("meeting_type")
            status = request.parameters.get("status")

            # 업데이트 실행
            result = await notion_service.update_meeting_page(
                page_id=page_id,
                title=title,
                participants=participants,
                meeting_type=meeting_type,
                status=status
            )

            if result:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.COMMAND_RESPONSE,
                    title="회의록 업데이트 완료",
                    content=f"✅ 회의록 페이지가 성공적으로 업데이트되었습니다.\n🔗 페이지 ID: {page_id}",
                    is_embed=True,
                    is_ephemeral=True,
                )
            else:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 회의록 업데이트에 실패했습니다.",
                    is_ephemeral=True,
                )
        except Exception as e:
            logger.error(f"❌ 회의록 업데이트 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 회의록 업데이트 실패: {str(e)}",
                is_ephemeral=True,
            )

    async def _update_document_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """문서 업데이트 워크플로우"""
        try:
            page_id = request.parameters.get("page_id")
            if not page_id:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 페이지 ID가 필요합니다.",
                    is_ephemeral=True,
                )

            notion_service = self._service_manager.get_service("notion")

            # 파라미터 추출
            title = request.parameters.get("title")
            doc_type = request.parameters.get("doc_type")
            status = request.parameters.get("status")

            # 업데이트 실행
            result = await notion_service.update_document_page(
                page_id=page_id,
                title=title,
                doc_type=doc_type,
                status=status
            )

            if result:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.COMMAND_RESPONSE,
                    title="문서 업데이트 완료",
                    content=f"✅ 문서 페이지가 성공적으로 업데이트되었습니다.\n🔗 페이지 ID: {page_id}",
                    is_embed=True,
                    is_ephemeral=True,
                )
            else:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 문서 업데이트에 실패했습니다.",
                    is_ephemeral=True,
                )
        except Exception as e:
            logger.error(f"❌ 문서 업데이트 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 문서 업데이트 실패: {str(e)}",
                is_ephemeral=True,
            )

    async def _archive_page_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """페이지 아카이브 워크플로우"""
        try:
            page_id = request.parameters.get("page_id")
            if not page_id:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 페이지 ID가 필요합니다.",
                    is_ephemeral=True,
                )

            notion_service = self._service_manager.get_service("notion")
            success = await notion_service.archive_page(page_id)

            if success:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.COMMAND_RESPONSE,
                    title="페이지 아카이브 완료",
                    content=f"🗑️ 페이지가 성공적으로 아카이브되었습니다.\n📝 페이지 ID: {page_id}\n💡 `/restore {page_id}` 명령어로 복구할 수 있습니다.",
                    is_embed=True,
                    is_ephemeral=True,
                )
            else:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 페이지 아카이브에 실패했습니다.",
                    is_ephemeral=True,
                )
        except Exception as e:
            logger.error(f"❌ 페이지 아카이브 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 페이지 아카이브 실패: {str(e)}",
                is_ephemeral=True,
            )

    async def _restore_page_workflow(
        self, request: DiscordCommandRequestDTO
    ) -> DiscordMessageResponseDTO:
        """페이지 복구 워크플로우"""
        try:
            page_id = request.parameters.get("page_id")
            if not page_id:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 페이지 ID가 필요합니다.",
                    is_ephemeral=True,
                )

            notion_service = self._service_manager.get_service("notion")
            success = await notion_service.restore_page(page_id)

            if success:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.COMMAND_RESPONSE,
                    title="페이지 복구 완료",
                    content=f"🔄 페이지가 성공적으로 복구되었습니다.\n📝 페이지 ID: {page_id}",
                    is_embed=True,
                    is_ephemeral=True,
                )
            else:
                return DiscordMessageResponseDTO(
                    message_type=MessageType.ERROR_NOTIFICATION,
                    content="❌ 페이지 복구에 실패했습니다.",
                    is_ephemeral=True,
                )
        except Exception as e:
            logger.error(f"❌ 페이지 복구 워크플로우 실패: {e}")
            return DiscordMessageResponseDTO(
                message_type=MessageType.ERROR_NOTIFICATION,
                content=f"❌ 페이지 복구 실패: {str(e)}",
                is_ephemeral=True,
            )

    async def _initialize_full_services(self):
        """전체 서비스 초기화 (설정 완료 시)"""
        try:
            # 서비스 매니저 초기화
            await self._service_manager.initialize()

            # 동적 설정 시스템 초기화
            await self._initialize_dynamic_config()

            logger.info("✅ 전체 서비스 초기화 완료")

        except Exception as e:
            logger.error(f"❌ 전체 서비스 초기화 실패: {e}")
            raise

    async def _initialize_config_only(self):
        """설정 웹 UI만 초기화 (설정 미완료 시)"""
        try:
            # FastAPI 웹 서버만 시작 (설정 관리용)
            logger.info("🔧 설정 관리 모드로 시작합니다")

            # 웹 라우트 설정
            self._setup_web_routes()

            # FastAPI 서버 시작
            config = uvicorn.Config(
                self.web_application,
                host="0.0.0.0",
                port=settings.port,
                log_level="warning",
                access_log=False,
            )
            server = uvicorn.Server(config)

            # 서버를 계속 실행 (설정 모드에서는 메인 루프)
            logger.info(
                f"🌐 설정 관리 웹 UI 시작: http://localhost:{settings.port}/config"
            )
            logger.info("💡 설정을 완료한 후 애플리케이션을 재시작하면 전체 서비스가 시작됩니다.")
            
            # 서버를 계속 실행
            await server.serve()

        except Exception as e:
            logger.error(f"❌ 설정 모드 초기화 실패: {e}")
            raise

    async def _initialize_dynamic_config(self):
        """동적 설정 시스템 초기화"""
        try:
            # Notion 서비스 가져오기
            notion_service = self._service_manager.get_service("notion")
            if not notion_service:
                logger.warning(
                    "⚠️ Notion 서비스를 찾을 수 없어 동적 설정 초기화를 건너뜁니다"
                )
                return

            # Discord 서비스 가져오기
            discord_service = self._service_manager.get_service("discord")
            if not discord_service:
                logger.warning(
                    "⚠️ Discord 서비스를 찾을 수 없어 동적 명령어 서비스 초기화를 건너뜁니다"
                )
                return

            # 동적 설정 관리자 초기화
            await dynamic_config_manager.initialize(notion_service)
            logger.info("✅ 동적 설정 관리자 초기화 완료")

            # 동적 명령어 서비스 초기화
            await dynamic_command_service.initialize(notion_service, discord_service)
            logger.info("✅ 동적 명령어 서비스 초기화 완료")

        except Exception as e:
            logger.error(f"❌ 동적 설정 시스템 초기화 실패: {e}")

    async def initialize_all_services(self) -> bool:
        """모든 서비스 초기화 (abstract 메서드 구현)"""
        return await self.initialize_system()

    async def shutdown_all_services(self) -> bool:
        """모든 서비스 종료 (abstract 메서드 구현)"""
        return await self.shutdown_system()


# 전역 애플리케이션 인스턴스
app = ServiceManager()


async def main():
    """메인 진입점"""
    # 로깅 시스템 초기화
    initialize_logging_system("INFO")

    # 메트릭 수집기 초기화
    metrics_collector = get_metrics_collector()
    metrics_collector.start_metrics_server(port=9090)

    # 전역 애플리케이션 인스턴스 사용
    try:
        await app.initialize_system()
        await app.run_service()
    except KeyboardInterrupt:
        logger.info("⌨️ 사용자 중단 request")
    except Exception as main_error:
        logger.error(f"💥 치명적 에러: {main_error}")
        raise
    finally:
        await app.shutdown_system()


if __name__ == "__main__":
    # 프로그램 시작점
    asyncio.run(main())
