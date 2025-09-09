"""중앙집중식 로깅 시스템 - 모든 로그를 통합 관리하고 형식을 일관성 있게 유지"""

import logging
import sys
from typing import Optional
from datetime import datetime
from pathlib import Path

from .config import settings


class KoreanLoggerFormatter(logging.Formatter):
    """
    한국어 친화적 로그 포매터
    - 시간, 레벨, 모듈명, 메시지를 보기 좋게 정렬
    - 에러 레벨에 따라 색상 구분 (터미널에서 확인 가능)
    """

    # ANSI 색상 코드 정의 (터미널에서 컬러 출력용)
    color_codes = {
        "DEBUG": "\033[36m",  # 청록색 (디버그)
        "INFO": "\033[32m",  # 초록색 (정보)
        "WARNING": "\033[33m",  # 노란색 (경고)
        "ERROR": "\033[31m",  # 빨간색 (에러)
        "CRITICAL": "\033[35m",  # 자주색 (치명적)
        "RESET": "\033[0m",  # 색상 리셋
    }

    def format(self, record):
        """로그 레코드를 한국어 친화적 형식으로 변환"""
        # 시간 포맷: YYYY-MM-DD HH:MM:SS
        time_string = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # 모듈 경로를 짧게 변환 (예: meetuploader.services.notion -> services.notion)
        module_name = record.name
        if module_name.startswith("meetuploader."):
            module_name = module_name[12:]  # 'meetuploader.' 제거

        # 색상 적용 (터미널 환경에서만)
        level_color = self.color_codes.get(record.levelname, "")
        reset_color = self.color_codes["RESET"]

        # 로그 메시지 조합
        formatted_message = f"{time_string} | {level_color}{record.levelname:8}{reset_color} | {module_name:20} | {record.getMessage()}"

        # 예외 정보가 있으면 추가
        if record.exc_info:
            formatted_message += f"\n{self.formatException(record.exc_info)}"

        return formatted_message


class CentralLoggerManager:
    """
    애플리케이션 전체의 로깅을 중앙에서 관리
    - 파일과 콘솔에 동시 출력
    - 레벨별 필터링
    - 로그 파일 로테이션
    """

    def __init__(self):
        self.logger_instance = None
        self.log_file_path = None
        self.initialized = False

    def initialize_logger_system(
        self, log_level: str = "INFO", log_to_file: bool = True
    ):
        """
        로깅 시스템을 초기화하고 전역 설정 적용

        Args:
            로그_레벨: 최소 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: 파일에 로그 저장 여부
        """
        if self.initialized:
            return self.logger_instance

        # 루트 로거 가져오기 (모든 하위 로거의 부모)
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))

        # 기존 핸들러 제거 (중복 방지)
        root_logger.handlers.clear()

        # 한국어 포매터 생성
        formatter = KoreanLoggerFormatter()

        # 1. 콘솔 출력 핸들러 설정
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        root_logger.addHandler(console_handler)

        # 2. 파일 출력 핸들러 설정 (선택사항)
        if log_to_file:
            self._setup_file_handler(root_logger, formatter)

        self.logger_instance = root_logger
        self.initialized = True

        # 초기화 완료 로그
        self.logger_instance.info("🚀 중앙집중식 로거 시스템 초기화 완료")
        self.logger_instance.info(f"📊 로그 레벨: {log_level}")
        if log_to_file:
            self.logger_instance.info(f"📁 로그 파일: {self.log_file_path}")

        return self.logger_instance

    def _setup_file_handler(self, root_logger, formatter):
        """파일 출력을 위한 핸들러 설정"""
        # 로그 디렉토리 생성
        log_directory = Path("logs")
        log_directory.mkdir(exist_ok=True)

        # 로그 파일명에 날짜 포함
        today_date = datetime.now().strftime("%Y%m%d")
        self.log_file_path = log_directory / f"meetuploader_{today_date}.log"

        # 파일 핸들러 생성 (UTF-8 인코딩으로 한글 지원)
        file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # 파일에는 모든 레벨 저장
        root_logger.addHandler(file_handler)

    def create_module_logger(self, module_name: str):
        """
        특정 모듈을 위한 로거 생성

        Args:
            모듈명: 모듈명 또는 클래스명 (예: 'services.notion', 'discord_bot')

        Returns:
            logging.Logger: 설정된 로거 인스턴스
        """
        if not self.initialized:
            self.initialize_logger_system()

        # meetuploader 네임스페이스 하위에 로거 생성
        full_module_name = f"meetuploader.{module_name}"
        module_logger = logging.getLogger(full_module_name)

        return module_logger

    def performance_logger(self, task_name: str):
        """
        성능 측정용 컨텍스트 매니저

        Usage:
            with 로거_관리자.성능_측정_로거("노션_API_호출"):
                # 시간 측정 대상 코드
                result = await notion_service.create_task()
        """
        return PerformanceMeasurementContext(
            task_name, self.create_module_logger("performance")
        )


class PerformanceMeasurementContext:
    """성능 측정을 위한 컨텍스트 매니저"""

    def __init__(self, task_name: str, logger: logging.Logger):
        self.task_name = task_name
        self.logger = logger
        self.start_time = None

    def __enter__(self):
        """컨텍스트 시작 - 시간 측정 시작"""
        self.start_time = datetime.now()
        self.logger.debug(f"⏱️  {self.task_name} 시작")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 종료 - 실행 시간 계산 및 로깅"""
        if self.start_time:
            execution_time = (datetime.now() - self.start_time).total_seconds()

            if exc_type:
                self.logger.error(
                    f"❌ {self.task_name} 실패 (실행시간: {execution_time:.3f}초)"
                )
            else:
                self.logger.info(
                    f"✅ {self.task_name} 완료 (실행시간: {execution_time:.3f}초)"
                )


# Global logger manager instance
logger_manager = CentralLoggerManager()


def get_logger(module_name: str) -> logging.Logger:
    """
    간편한 로거 생성 함수

    Usage:
        from core.logger import 로거_가져오기
        logger = 로거_가져오기("services.notion")
        logger.info("노션 서비스 시작")

    Args:
        모듈명: 로거 이름

    Returns:
        logging.Logger: 설정된 로거
    """
    return logger_manager.create_module_logger(module_name)


def initialize_logging_system(log_level: str = "INFO"):
    """
    애플리케이션 시작 시 호출할 로깅 초기화 함수

    Args:
        로그_레벨: 로그 레벨 설정
    """
    return logger_manager.initialize_logger_system(log_level)
