"""
서비스 관리자 모듈
모든 서비스의 생성, 의존성 주입, 생명주기를 관리
"""

from typing import Optional, Dict, Any
import asyncio

from src.core.logger import get_logger, logger_manager
from src.core.config import settings

# 워크플로우 서비스들은 순환 import를 피하기 위해 함수 내부에서 import

logger = get_logger("service_manager")


class ServiceManager:
    """
    서비스 관리자 클래스
    - 모든 서비스의 생성 및 의존성 주입
    - 서비스 간 의존성 관리
    - 서비스 생명주기 관리
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized = False

    async def initialize(self):
        """서비스 매니저 초기화"""
        if self._initialized:
            return

        try:
            # 1. 기본 서비스들 초기화
            await self._initialize_core_services()

            # 2. 워크플로우 서비스들 초기화
            await self._initialize_workflow_services()

            # 3. 서비스간 의존성 설정
            await self._setup_service_dependencies()

            self._initialized = True

        except Exception as e:
            logger.error(f"❌ ServiceManager 초기화 실패: {e}")
            raise

    async def _initialize_core_services(self):
        """핵심 서비스들 초기화"""
        # NotionService 초기화
        from src.service.notion.notion_service import NotionService

        self._services["notion"] = NotionService()

        # DiscordService 초기화
        from src.service.discord.discord_service import DiscordService

        self._services["discord"] = DiscordService()

        # SearchService 초기화
        from src.service.search.search_service import SearchService

        self._services["search"] = SearchService()

        # AnalyticsService 초기화
        from src.service.analytics.analytics_service import SimpleStatsService

        self._services["analytics"] = SimpleStatsService()

        # SyncService 초기화
        from src.service.sync.sync_service import SyncService

        self._services["sync"] = SyncService()

    async def _initialize_workflow_services(self):
        """워크플로우 서비스들 초기화"""

        # 순환 import를 피하기 위해 함수 내부에서 import
        from src.service.workflow.meeting_workflow_service import MeetingWorkflowService
        from src.service.workflow.document_workflow_service import (
            DocumentWorkflowService,
        )
        from src.service.workflow.task_workflow_service import TaskWorkflowService
        from src.service.workflow.analytics_workflow_service import (
            AnalyticsWorkflowService,
        )
        from src.service.workflow.search_workflow_service import SearchWorkflowService
        from src.service.workflow.utility_workflow_service import UtilityWorkflowService

        notion_service = self._services["notion"]
        discord_service = self._services["discord"]

        # 워크플로우 서비스들 생성
        self._services["meeting_workflow"] = MeetingWorkflowService(
            notion_service=notion_service,
            discord_service=discord_service,
            logger_manager=logger_manager,
        )

        self._services["document_workflow"] = DocumentWorkflowService(
            notion_service=notion_service,
            discord_service=discord_service,
            logger_manager=logger_manager,
        )

        self._services["task_workflow"] = TaskWorkflowService(
            notion_service=notion_service,
            discord_service=discord_service,
            logger_manager=logger_manager,
        )

        self._services["analytics_workflow"] = AnalyticsWorkflowService(
            notion_service=notion_service,
            discord_service=discord_service,
            logger_manager=logger_manager,
        )

        self._services["search_workflow"] = SearchWorkflowService(
            notion_service=notion_service,
            discord_service=discord_service,
            logger_manager=logger_manager,
        )

        self._services["utility_workflow"] = UtilityWorkflowService(
            notion_service=notion_service,
            discord_service=discord_service,
            logger_manager=logger_manager,
        )

    async def _setup_service_dependencies(self):
        """서비스간 의존성 설정"""
        # Discord Service에 커맨드 콜백 설정 (discord 서비스가 있는 경우에만)
        if "discord" in self._services:
            discord_service = self._services["discord"]
            if hasattr(discord_service, "set_command_callback"):
                # 커맨드 처리를 위한 콜백 함수 설정
                discord_service.set_command_callback(self._handle_discord_command)

    async def _handle_discord_command(self, request):
        """Discord 커맨드 처리 콜백"""
        from src.dto.common.enums import CommandType

        try:
            # 커맨드 타입에 따라 적절한 워크플로우 서비스로 라우팅
            if request.command_type == CommandType.MEETING:
                return await self._services["meeting_workflow"].create_meeting(request)
            elif request.command_type == CommandType.DOCUMENT:
                return await self._services["document_workflow"].create_document(
                    request
                )
            elif request.command_type == CommandType.TASK:
                return await self._services["task_workflow"].create_task(request)
            else:
                # 기본적으로는 원래 로직 유지 (검색, 통계 등)
                return None

        except Exception as e:
            logger.error(f"❌ Discord 커맨드 처리 실패: {e}")
            raise

    def get_service(self, service_name: str):
        """서비스 인스턴스 반환"""
        if not self._initialized:
            raise RuntimeError("ServiceManager가 초기화되지 않았습니다.")

        service = self._services.get(service_name)
        if not service:
            raise KeyError(f"서비스 '{service_name}'을 찾을 수 없습니다.")

        return service

    def get_workflow_service(self, workflow_type: str):
        """워크플로우 서비스 반환"""
        workflow_service_map = {
            "meeting": "meeting_workflow",
            "document": "document_workflow",
            "task": "task_workflow",
            "analytics": "analytics_workflow",
            "search": "search_workflow",
            "utility": "utility_workflow",
        }

        service_name = workflow_service_map.get(workflow_type)
        if not service_name:
            raise KeyError(f"워크플로우 타입 '{workflow_type}'을 찾을 수 없습니다.")

        return self.get_service(service_name)

    async def shutdown(self):
        """서비스 매니저 종료"""
        if not self._initialized:
            return

        logger.info("🛑 ServiceManager 종료 시작")

        try:
            # 각 서비스들의 shutdown 메서드 호출
            for service_name, service in self._services.items():
                if hasattr(service, "shutdown"):
                    try:
                        await service.shutdown()
                        logger.debug(f"✅ {service_name} 서비스 종료 완료")
                    except Exception as e:
                        logger.warning(f"⚠️ {service_name} 서비스 종료 중 오류: {e}")

            self._services.clear()
            self._initialized = False

            logger.info("✅ ServiceManager 종료 완료")

        except Exception as e:
            logger.error(f"❌ ServiceManager 종료 중 오류: {e}")

    @property
    def is_initialized(self) -> bool:
        """초기화 상태 반환"""
        return self._initialized

    def get_service_status(self) -> Dict[str, Any]:
        """모든 서비스의 상태 정보 반환"""
        status = {"initialized": self._initialized, "services": {}}

        for service_name, service in self._services.items():
            service_status = {
                "available": service is not None,
                "type": type(service).__name__,
            }

            # 서비스별 상태 확인 메서드가 있으면 호출
            if hasattr(service, "get_status"):
                try:
                    service_status.update(service.get_status())
                except Exception as e:
                    service_status["status_error"] = str(e)

            status["services"][service_name] = service_status

        return status

    def list_available_services(self) -> list:
        """사용 가능한 서비스 목록 반환"""
        return list(self._services.keys())


# 전역 서비스 매니저 인스턴스
service_manager = ServiceManager()
