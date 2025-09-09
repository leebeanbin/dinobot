"""
전역 오류 처리 및 로깅 시스템
- 모든 예외를 중앙에서 처리
- 터미널에 간결한 오류 메시지 표시
- 상세 로그는 파일에 기록
"""

import sys
import traceback
import asyncio
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum

from core.logger import get_logger
from core.config import settings

logger = get_logger("core.global_error_handler")


class ErrorSeverity(Enum):
    """오류 심각도 레벨"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GlobalErrorHandler:
    """전역 오류 처리기"""

    def __init__(self):
        self.error_counts = {}
        self.last_error_time = {}
        self.error_threshold = 10  # 같은 오류가 10번 발생하면 경고
        self.time_window = 300  # 5분 윈도우

    def handle_exception(
        self,
        exception: Exception,
        context: str = "",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        show_traceback: bool = False,
    ) -> None:
        """예외 처리 및 로깅"""
        try:
            # 오류 정보 수집
            error_info = self._collect_error_info(exception, context, severity)

            # 오류 카운트 업데이트
            self._update_error_counts(error_info)

            # 터미널에 간결한 오류 메시지 표시
            self._display_terminal_error(error_info, show_traceback)

            # 상세 로그 기록
            self._log_detailed_error(error_info)

            # 심각한 오류인 경우 추가 처리
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                self._handle_critical_error(error_info)

        except Exception as handler_error:
            # 오류 처리기 자체에서 오류가 발생한 경우
            print(f"❌ 오류 처리기 오류: {handler_error}")
            logger.critical(f"Error handler failed: {handler_error}")

    def _collect_error_info(
        self, exception: Exception, context: str, severity: ErrorSeverity
    ) -> Dict[str, Any]:
        """오류 정보 수집"""
        error_type = type(exception).__name__
        error_message = str(exception)
        timestamp = datetime.now()

        return {
            "exception": exception,
            "error_type": error_type,
            "error_message": error_message,
            "context": context,
            "severity": severity,
            "timestamp": timestamp,
            "traceback": traceback.format_exc(),
            "error_key": f"{error_type}:{context}",
        }

    def _update_error_counts(self, error_info: Dict[str, Any]) -> None:
        """오류 발생 횟수 업데이트"""
        error_key = error_info["error_key"]
        current_time = error_info["timestamp"]

        # 오래된 오류 카운트 정리
        self._cleanup_old_errors(current_time)

        # 현재 오류 카운트 증가
        if error_key not in self.error_counts:
            self.error_counts[error_key] = 0
        self.error_counts[error_key] += 1
        self.last_error_time[error_key] = current_time

    def _cleanup_old_errors(self, current_time: datetime) -> None:
        """오래된 오류 카운트 정리"""
        cutoff_time = current_time.timestamp() - self.time_window
        keys_to_remove = []

        for error_key, last_time in self.last_error_time.items():
            if last_time.timestamp() < cutoff_time:
                keys_to_remove.append(error_key)

        for key in keys_to_remove:
            self.error_counts.pop(key, None)
            self.last_error_time.pop(key, None)

    def _display_terminal_error(
        self, error_info: Dict[str, Any], show_traceback: bool
    ) -> None:
        """터미널에 간결한 오류 메시지 표시"""
        error_type = error_info["error_type"]
        error_message = error_info["error_message"]
        context = error_info["context"]
        severity = error_info["severity"]
        error_key = error_info["error_key"]
        count = self.error_counts.get(error_key, 1)

        # 심각도에 따른 이모지 선택
        severity_emoji = {
            ErrorSeverity.LOW: "⚠️",
            ErrorSeverity.MEDIUM: "❌",
            ErrorSeverity.HIGH: "🚨",
            ErrorSeverity.CRITICAL: "💥",
        }

        emoji = severity_emoji.get(severity, "❌")

        # 간결한 오류 메시지 구성
        if context:
            message = (
                f"{emoji} [{severity.value}] {context}: {error_type} - {error_message}"
            )
        else:
            message = f"{emoji} [{severity.value}] {error_type}: {error_message}"

        # 반복 발생한 오류인 경우 카운트 표시
        if count > 1:
            message += f" (x{count})"

        # 터미널에 출력
        print(message, file=sys.stderr)

        # 심각한 오류이거나 traceback을 요청한 경우 상세 정보 표시
        if show_traceback or severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            traceback_lines = error_info["traceback"].split("\n")
            location = traceback_lines[-2] if len(traceback_lines) > 1 else "Unknown"
            print(f"📍 위치: {location}", file=sys.stderr)

    def _log_detailed_error(self, error_info: Dict[str, Any]) -> None:
        """상세 오류 로그 기록"""
        severity = error_info["severity"]
        context = error_info["context"]
        error_type = error_info["error_type"]
        error_message = error_info["error_message"]
        traceback_str = error_info["traceback"]

        # 로그 레벨 결정
        log_level = {
            ErrorSeverity.LOW: "warning",
            ErrorSeverity.MEDIUM: "error",
            ErrorSeverity.HIGH: "critical",
            ErrorSeverity.CRITICAL: "critical",
        }.get(severity, "error")

        # 상세 로그 메시지
        log_message = f"Exception in {context}: {error_type}: {error_message}"

        if log_level == "critical":
            logger.critical(log_message)
            logger.critical(f"Traceback: {traceback_str}")
        elif log_level == "error":
            logger.error(log_message)
            logger.error(f"Traceback: {traceback_str}")
        else:
            logger.warning(log_message)
            logger.warning(f"Traceback: {traceback_str}")

    def _handle_critical_error(self, error_info: Dict[str, Any]) -> None:
        """심각한 오류 처리"""
        error_key = error_info["error_key"]
        count = self.error_counts.get(error_key, 1)

        # 같은 오류가 임계값을 초과한 경우
        if count >= self.error_threshold:
            print(
                f"🚨 경고: '{error_info['context']}'에서 같은 오류가 {count}번 발생했습니다!",
                file=sys.stderr,
            )
            logger.critical(
                f"Error threshold exceeded for {error_key}: {count} occurrences"
            )

    def get_error_summary(self) -> Dict[str, Any]:
        """오류 요약 정보 반환"""
        current_time = datetime.now()
        self._cleanup_old_errors(current_time)

        return {
            "total_unique_errors": len(self.error_counts),
            "error_counts": dict(self.error_counts),
            "high_frequency_errors": {
                key: count
                for key, count in self.error_counts.items()
                if count >= self.error_threshold
            },
        }


# 전역 오류 처리기 인스턴스
global_error_handler = GlobalErrorHandler()


def handle_exception(
    exception: Exception,
    context: str = "",
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    show_traceback: bool = False,
) -> None:
    """전역 예외 처리 함수"""
    global_error_handler.handle_exception(exception, context, severity, show_traceback)


def handle_async_exception(
    exception: Exception,
    context: str = "",
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    show_traceback: bool = False,
) -> None:
    """비동기 예외 처리 함수"""
    # 비동기 컨텍스트에서도 안전하게 처리
    try:
        handle_exception(exception, context, severity, show_traceback)
    except Exception as e:
        print(f"❌ 비동기 오류 처리 실패: {e}", file=sys.stderr)


def safe_execute(
    func: Callable,
    context: str = "",
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    default_return: Any = None,
) -> Any:
    """안전한 함수 실행 데코레이터"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            handle_exception(e, context, severity)
            return default_return

    return wrapper


def safe_async_execute(
    func: Callable,
    context: str = "",
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    default_return: Any = None,
) -> Any:
    """안전한 비동기 함수 실행 데코레이터"""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            handle_async_exception(e, context, severity)
            return default_return

    return wrapper


# 예외 처리기 설정
def setup_global_exception_handlers():
    """전역 예외 처리기 설정"""

    # Python 기본 예외 처리기 설정
    def exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        handle_exception(
            exc_value,
            "Unhandled Exception",
            ErrorSeverity.CRITICAL,
            show_traceback=True,
        )

    sys.excepthook = exception_handler

    # asyncio 예외 처리기 설정
    def asyncio_exception_handler(loop, context):
        exception = context.get("exception")
        if exception:
            handle_async_exception(
                exception,
                f"AsyncIO: {context.get('message', 'Unknown')}",
                ErrorSeverity.HIGH,
            )
        else:
            logger.warning(f"AsyncIO context: {context}")

    # 현재 이벤트 루프가 있으면 설정
    try:
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(asyncio_exception_handler)
    except RuntimeError:
        # 이벤트 루프가 없는 경우, 나중에 설정
        pass


# 모듈 로드 시 자동 설정
setup_global_exception_handlers()
