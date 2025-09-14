"""
DinoBot 시스템 상수 및 설정값 중앙 관리
하드코딩된 값들을 한 곳에서 관리하여 유지보수성 향상
"""

from enum import Enum
from typing import List, Dict, Any


class NotionConstants:
    """Notion 관련 상수들"""

    # 문서 타입
    DOCUMENT_TYPES = ["개발 문서", "기획안", "개발 규칙", "회의록"]
    DEFAULT_DOCUMENT_TYPE = "개발 문서"

    # 우선순위
    PRIORITY_LEVELS = ["High", "Medium", "Low", "Critical"]
    DEFAULT_PRIORITY = "Medium"

    # 상태
    TASK_STATUSES = ["Not started", "In progress", "Done", "Cancelled"]
    DEFAULT_TASK_STATUS = "Not started"

    # 회의 타입
    MEETING_TYPES = ["정기회의", "프로젝트 회의", "브레인스토밍", "리뷰 회의", "기획 회의"]
    DEFAULT_MEETING_TYPE = "정기회의"


class UserConstants:
    """사용자 관련 상수들"""

    # 유효한 참석자/담당자 목록
    VALID_PERSONS = ["소현", "정빈", "동훈"]

    # 테스트 사용자
    TEST_USER_NAMES = ["테스트봇", "CRUD테스터", "시스템테스트"]


class TestConstants:
    """테스트 관련 상수들"""

    # 테스트 데이터 식별자
    TEST_TITLE_PREFIX = "TEST_"
    TEST_TITLE_PATTERNS = [
        "테스트",
        "CRUD 테스트",
        "종합 테스트",
        "시스템 테스트"
    ]

    # 테스트 우선순위
    TEST_PRIORITIES = ["High", "Medium", "Low"]

    # 테스트 상태
    TEST_STATUSES = ["Not started", "In progress", "Done"]


class SystemConstants:
    """시스템 관련 상수들"""

    # 기본 타임아웃 (초)
    DEFAULT_TIMEOUT = 120

    # 재시도 횟수
    DEFAULT_RETRY_COUNT = 3

    # 페이징 크기
    DEFAULT_PAGE_SIZE = 50

    # 최대 검색 결과
    MAX_SEARCH_RESULTS = 100


class MessageConstants:
    """메시지 관련 상수들"""

    # 성공 메시지
    SUCCESS_MESSAGES = {
        "task_created": "✅ **태스크 생성 완료**",
        "meeting_created": "✅ **회의록 생성 완료**",
        "document_created": "✅ **문서 생성 완료**",
        "page_updated": "✅ **페이지 업데이트 완료**",
        "page_archived": "🗑️ **페이지 아카이브 완료**",
        "page_restored": "🔄 **페이지 복구 완료**"
    }

    # 에러 메시지
    ERROR_MESSAGES = {
        "missing_title": "❌ 제목이 필요합니다.",
        "missing_page_id": "❌ 페이지 ID가 필요합니다.",
        "invalid_document_type": "❌ 올바른 문서 유형을 선택해주세요.",
        "invalid_priority": "❌ 올바른 우선순위를 선택해주세요.",
        "invalid_person": "❌ 올바른 담당자를 선택해주세요.",
        "service_not_initialized": "❌ 서비스가 초기화되지 않았습니다.",
        "notion_api_error": "❌ Notion API 오류가 발생했습니다."
    }

    # 도움말 메시지
    HELP_MESSAGES = {
        "valid_persons": f"사용 가능한 담당자: {', '.join(UserConstants.VALID_PERSONS)}",
        "valid_document_types": f"사용 가능한 문서 타입: {', '.join(NotionConstants.DOCUMENT_TYPES)}",
        "valid_priorities": f"사용 가능한 우선순위: {', '.join(NotionConstants.PRIORITY_LEVELS)}"
    }


class ValidationRules:
    """검증 규칙 상수들"""

    # 제목 길이 제한
    MIN_TITLE_LENGTH = 1
    MAX_TITLE_LENGTH = 200

    # 검색어 길이 제한
    MIN_SEARCH_QUERY_LENGTH = 2
    MAX_SEARCH_QUERY_LENGTH = 100

    # 페이지 ID 형식 (Notion UUID 형식)
    PAGE_ID_LENGTH = 32
    PAGE_ID_PATTERN = r"^[a-f0-9]{32}$"


class DatabaseConstants:
    """데이터베이스 관련 상수들"""

    # 페이지 타입
    PAGE_TYPES = ["task", "meeting", "document"]

    # 데이터베이스 이름 매핑
    DB_TYPE_MAPPING = {
        "task": "Factory Tracker",
        "meeting": "Board",
        "document": "Board"
    }


# 설정 값들을 쉽게 가져올 수 있는 헬퍼 함수들
class ConfigHelper:
    """설정값 조회 헬퍼"""

    @staticmethod
    def get_valid_document_types() -> List[str]:
        """유효한 문서 타입 목록 반환"""
        return NotionConstants.DOCUMENT_TYPES.copy()

    @staticmethod
    def get_valid_priorities() -> List[str]:
        """유효한 우선순위 목록 반환"""
        return NotionConstants.PRIORITY_LEVELS.copy()

    @staticmethod
    def get_valid_persons() -> List[str]:
        """유효한 담당자 목록 반환"""
        return UserConstants.VALID_PERSONS.copy()

    @staticmethod
    def get_valid_meeting_types() -> List[str]:
        """유효한 회의 타입 목록 반환"""
        return NotionConstants.MEETING_TYPES.copy()

    @staticmethod
    def is_valid_document_type(doc_type: str) -> bool:
        """문서 타입 유효성 검증"""
        return doc_type in NotionConstants.DOCUMENT_TYPES

    @staticmethod
    def is_valid_priority(priority: str) -> bool:
        """우선순위 유효성 검증"""
        return priority in NotionConstants.PRIORITY_LEVELS

    @staticmethod
    def is_valid_person(person: str) -> bool:
        """담당자 유효성 검증"""
        return person in UserConstants.VALID_PERSONS

    @staticmethod
    def is_test_data(title: str) -> bool:
        """테스트 데이터인지 검증"""
        title_lower = title.lower()
        return any(pattern.lower() in title_lower for pattern in TestConstants.TEST_TITLE_PATTERNS)

    @staticmethod
    def format_error_message(error_type: str, **kwargs) -> str:
        """에러 메시지 포맷팅"""
        message = MessageConstants.ERROR_MESSAGES.get(error_type, "❌ 알 수 없는 오류가 발생했습니다.")
        try:
            return message.format(**kwargs)
        except KeyError:
            return message

    @staticmethod
    def format_success_message(success_type: str, **kwargs) -> str:
        """성공 메시지 포맷팅"""
        message = MessageConstants.SUCCESS_MESSAGES.get(success_type, "✅ 작업이 완료되었습니다.")
        try:
            return message.format(**kwargs)
        except KeyError:
            return message


# 환경별 설정 (개발/프로덕션)
class EnvironmentConfig:
    """환경별 설정"""

    DEVELOPMENT = {
        "test_mode": True,
        "cleanup_test_data": True,
        "verbose_logging": True,
        "test_title_prefix": TestConstants.TEST_TITLE_PREFIX
    }

    PRODUCTION = {
        "test_mode": False,
        "cleanup_test_data": False,
        "verbose_logging": False,
        "test_title_prefix": None
    }

    @classmethod
    def get_config(cls, env: str = "development") -> Dict[str, Any]:
        """환경별 설정 반환"""
        if env.lower() == "production":
            return cls.PRODUCTION.copy()
        return cls.DEVELOPMENT.copy()


# 전역 설정 인스턴스
config_helper = ConfigHelper()

# 자주 사용되는 상수들을 직접 접근 가능하게
VALID_PERSONS = UserConstants.VALID_PERSONS
VALID_DOCUMENT_TYPES = NotionConstants.DOCUMENT_TYPES
VALID_PRIORITIES = NotionConstants.PRIORITY_LEVELS
VALID_MEETING_TYPES = NotionConstants.MEETING_TYPES

DEFAULT_PRIORITY = NotionConstants.DEFAULT_PRIORITY
DEFAULT_DOCUMENT_TYPE = NotionConstants.DEFAULT_DOCUMENT_TYPE
DEFAULT_MEETING_TYPE = NotionConstants.DEFAULT_MEETING_TYPE