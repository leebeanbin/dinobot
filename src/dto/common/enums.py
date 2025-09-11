"""
Enumeration classes for DTOs
"""

from enum import Enum


class CommandType(str, Enum):
    """Discord command type enumeration"""

    TASK = "task"  # Factory Tracker DB에 Task 생성
    MEETING = "meeting"  # Board DB에 회의록 생성
    DOCUMENT = "document"  # Board DB에 문서 생성 (개발 문서, 기획안, 개발 규칙)
    STATUS = "status"
    HELP = "help"
    FETCH_PAGE = "fetch_page"
    WATCH_PAGE = "watch_page"

    # 통계 관련 명령어들
    DAILY_STATS = "daily_stats"
    WEEKLY_STATS = "weekly_stats"
    MONTHLY_STATS = "monthly_stats"
    USER_STATS = "user_stats"
    TEAM_STATS = "team_stats"
    TRENDS = "trends"
    TASK_STATS = "task_stats"
    SEARCH = "search"


class NotionPropertyType(str, Enum):
    """Notion property type enumeration"""

    TITLE = "title"
    RICH_TEXT = "rich_text"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    STATUS = "status"
    CHECKBOX = "checkbox"
    DATE = "date"
    NUMBER = "number"
    PERSON = "person"
    RELATION = "relation"


class MessageType(str, Enum):
    """Message type classification"""

    COMMAND_RESPONSE = "command_response"
    WEBHOOK_SUMMARY = "webhook_summary"
    ERROR_NOTIFICATION = "error_notification"
    SUCCESS_NOTIFICATION = "success_notification"
    SYSTEM_STATUS = "system_status"