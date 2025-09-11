"""글로벌 예외 처리 시스템 - 모든 예외를 중앙에서 일관성 있게 처리"""

import traceback
from typing import Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime

import discord
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .logger import get_logger


class ErrorCategory(Enum):
    """Categorize errors to determine appropriate handling methods"""

    DISCORD_API_ERROR = "discord_api_error"  # Discord API related errors
    NOTION_API_ERROR = "notion_api_error"  # Notion API related errors
    DATABASE_CONNECTION_ERROR = "database_connection_error"  # MongoDB connection errors
    DATABASE_OPERATION_ERROR = "database_operation_error"  # MongoDB operation errors
    CONFIGURATION_ERROR = (
        "configuration_error"  # Environment variables, configuration errors
    )
    AUTHENTICATION_ERROR = "authentication_error"  # Authentication/permission errors
    USER_INPUT_ERROR = "user_input_error"  # User input validation errors
    EXTERNAL_SERVICE_ERROR = (
        "external_service_error"  # External service communication errors
    )
    SYSTEM_ERROR = "system_error"  # System level errors
    UNKNOWN_ERROR = "unknown_error"  # Uncategorized errors


class CustomException(Exception):
    """
    애플리케이션 전용 기본 예외 클래스
    - 에러 category와 상세 정보를 포함
    - 사용자에게 보여줄 message와 내부 로그용 message 분리
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        Args:
            message: 내부 로깅용 상세 message
            category: 에러 분류 category
            user_message: 사용자에게 표시할 친화적 message
            details: 추가 디버깅 정보
            original_exception: 원본 예외 객체 (체이닝용)
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.user_message = user_message or self._generate_default_user_message()
        self.details = details or {}
        self.original_exception = original_exception
        self.occurrence_time = datetime.now()

    def _generate_default_user_message(self) -> str:
        """category별 기본 사용자 message 생성"""
        message_map = {
            ErrorCategory.DISCORD_API_ERROR: "디스코드 연결에 문제가 있습니다. 잠시 후 다시 시도해주세요.",
            ErrorCategory.NOTION_API_ERROR: "노션 연결에 문제가 있습니다. 잠시 후 다시 시도해주세요.",
            ErrorCategory.DATABASE_CONNECTION_ERROR: "데이터베이스 연결에 문제가 있습니다.",
            ErrorCategory.DATABASE_OPERATION_ERROR: "데이터 처리 중 문제가 발생했습니다.",
            ErrorCategory.CONFIGURATION_ERROR: "시스템 설정에 문제가 있습니다.",
            ErrorCategory.AUTHENTICATION_ERROR: "접근 권한이 없습니다.",
            ErrorCategory.USER_INPUT_ERROR: "입력값을 확인해주세요.",
            ErrorCategory.EXTERNAL_SERVICE_ERROR: "외부 서비스 연결에 문제가 있습니다.",
            ErrorCategory.SYSTEM_ERROR: "시스템 오류가 발생했습니다.",
            ErrorCategory.UNKNOWN_ERROR: "알 수 없는 오류가 발생했습니다.",
        }
        return message_map.get(self.category, "오류가 발생했습니다.")

    def to_dict(self) -> Dict[str, Any]:
        """예외 정보를 딕셔너리로 변환 (로깅/API 응답용)"""
        return {
            "category": self.category.value,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
            "occurrence_time": self.occurrence_time.isoformat(),
            "original_exception": (
                str(self.original_exception) if self.original_exception else None
            ),
        }


# 특정 category별 예외 클래스들
class DiscordAPIException(CustomException):
    """디스코드 API 관련 예외"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.DISCORD_API_ERROR, **kwargs)


class NotionAPIException(CustomException):
    """노션 API 관련 예외"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.NOTION_API_ERROR, **kwargs)


class DatabaseConnectionException(CustomException):
    """MongoDB 연결 관련 예외"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, category=ErrorCategory.DATABASE_CONNECTION_ERROR, **kwargs
        )


class DatabaseOperationException(CustomException):
    """MongoDB 작업 관련 예외"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, category=ErrorCategory.DATABASE_OPERATION_ERROR, **kwargs
        )


class UserInputException(CustomException):
    """사용자 입력 검증 관련 예외"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.USER_INPUT_ERROR, **kwargs)


class GlobalExceptionHandler:
    """
    전역 예외 처리기 - 모든 예외를 중앙에서 일관성 있게 처리
    - Discord 명령어 예외 처리
    - FastAPI HTTP 예외 처리
    - 일반 Python 예외 처리
    - 로깅과 사용자 알림을 자동화
    """

    def __init__(self):
        self.logger = get_logger("exceptions")
        self.exception_stats = {}  # 예외 발생 통계 수집

    async def handle_discord_command_exception(
        self, interaction: discord.Interaction, exception: Exception
    ):
        """
        디스코드 슬래시 명령어에서 발생한 예외 처리

        Args:
            interaction: 디스코드 인터랙션 객체
            exception: 발생한 예외
        """
        error_info = self._analyze_exception(exception)

        # 로깅
        self.logger.error(
            f"💬 디스코드 명령어 예외 발생\n"
            f"   명령어: {interaction.command.name if interaction.command else 'Unknown'}\n"
            f"   사용자: {interaction.user} (ID: {interaction.user.id})\n"
            f"   길드: {interaction.guild} (ID: {interaction.guild_id})\n"
            f"   category: {error_info['category']}\n"
            f"   message: {error_info['message']}"
        )

        # 사용자에게 응답
        user_message = f"❌ {error_info['user_message']}"

        try:
            if interaction.response.is_done():
                await interaction.followup.send(user_message, ephemeral=True)
            else:
                await interaction.response.send_message(user_message, ephemeral=True)
        except Exception as response_error:
            self.logger.error(f"디스코드 응답 전송 실패: {response_error}")

        # 통계 업데이트
        self._update_exception_stats(error_info["category"])

    async def handle_fastapi_exception(
        self, request: Request, exception: Exception
    ) -> JSONResponse:
        """
        FastAPI 웹훅 요청에서 발생한 예외 처리

        Args:
            request: FastAPI 요청 객체
            exception: 발생한 예외

        Returns:
            JSONResponse: 클라이언트에 반환할 응답
        """
        error_info = self._analyze_exception(exception)

        # 로깅
        self.logger.error(
            f"🌐 웹API 예외 발생\n"
            f"   경로: {request.url.path}\n"
            f"   메서드: {request.method}\n"
            f"   클라이언트 IP: {request.client.host if request.client else 'Unknown'}\n"
            f"   category: {error_info['category']}\n"
            f"   message: {error_info['message']}"
        )

        # HTTP 상태 코드 결정
        status_code = self._determine_http_status_code(error_info["category"])

        # 응답 생성
        response_data = {
            "success": False,
            "error": {
                "message": error_info["user_message"],
                "category": error_info["category"],
                "timestamp": datetime.now().isoformat(),
            },
        }

        # 통계 업데이트
        self._update_exception_stats(error_info["category"])

        return JSONResponse(status_code=status_code, content=response_data)

    def _analyze_exception(self, exception: Exception) -> Dict[str, Any]:
        """
        예외를 분석하여 category와 message 추출

        Args:
            exception: 분석할 예외 객체

        Returns:
            Dict: 분석 결과 (category, message, user_message 등)
        """
        if isinstance(exception, CustomException):
            # 이미 분류된 사용자 정의 예외
            return {
                "category": exception.category.value,
                "message": exception.message,
                "user_message": exception.user_message,
                "details": exception.details,
            }

        # 외부 라이브러리 예외들을 category별로 분류
        exception_type_name = type(exception).__name__
        exception_message = str(exception)

        if isinstance(exception, discord.DiscordException):
            category = ErrorCategory.DISCORD_API_ERROR.value
            user_message = "디스코드 연결에 문제가 있습니다."
        elif (
            "notion" in exception_type_name.lower()
            or "notion" in exception_message.lower()
        ):
            category = ErrorCategory.NOTION_API_ERROR.value
            user_message = "노션 연결에 문제가 있습니다."
        elif (
            "mongo" in exception_type_name.lower()
            or "motor" in exception_type_name.lower()
        ):
            category = ErrorCategory.DATABASE_OPERATION_ERROR.value
            user_message = "데이터베이스 처리 중 문제가 발생했습니다."
        elif isinstance(exception, (ValueError, TypeError)):
            category = ErrorCategory.USER_INPUT_ERROR.value
            user_message = "입력값을 확인해주세요."
        elif isinstance(exception, (ConnectionError, TimeoutError)):
            category = ErrorCategory.EXTERNAL_SERVICE_ERROR.value
            user_message = "외부 서비스 연결에 문제가 있습니다."
        else:
            category = ErrorCategory.SYSTEM_ERROR.value
            user_message = "시스템 오류가 발생했습니다."

        return {
            "category": category,
            "message": f"{exception_type_name}: {exception_message}",
            "user_message": user_message,
            "details": {
                "exception_type": exception_type_name,
                "stack_trace": traceback.format_exc(),
            },
        }

    def _determine_http_status_code(self, category: str) -> int:
        """에러 category에 따른 HTTP 상태 코드 결정"""
        code_map = {
            ErrorCategory.AUTHENTICATION_ERROR.value: 401,
            ErrorCategory.USER_INPUT_ERROR.value: 400,
            ErrorCategory.EXTERNAL_SERVICE_ERROR.value: 502,
            ErrorCategory.DATABASE_CONNECTION_ERROR.value: 503,
            ErrorCategory.NOTION_API_ERROR.value: 502,
            ErrorCategory.DISCORD_API_ERROR.value: 502,
        }
        return code_map.get(category, 500)  # 기본값: 500 Internal Server Error

    def _update_exception_stats(self, category: str):
        """예외 발생 통계 업데이트"""
        if category not in self.exception_stats:
            self.exception_stats[category] = 0
        self.exception_stats[category] += 1

        # 10회마다 통계 로깅
        if self.exception_stats[category] % 10 == 0:
            self.logger.warning(
                f"📊 예외 통계 알림: '{category}' category {self.exception_stats[category]}회 발생"
            )

    def get_exception_stats(self) -> Dict[str, int]:
        """현재까지의 예외 발생 통계 반환"""
        return self.exception_stats.copy()


# Global exception handler instance
global_exception_handler = GlobalExceptionHandler()


def safe_execution(function_name: str = ""):
    """
    데코레이터: 함수 실행을 안전하게 감싸고 예외 발생 시 로깅

    Usage:
        @safe_execution("노션_페이지_생성")
        async def create_notion_page():
            # 위험할 수 있는 코드
            pass
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger = get_logger("safe_execution")
                logger.error(
                    f"🛡️  안전한 실행 실패 - {function_name or func.__name__}: {e}"
                )
                raise CustomException(
                    f"함수 실행 중 예외 발생: {function_name or func.__name__}",
                    original_exception=e,
                )

        return wrapper

    return decorator
