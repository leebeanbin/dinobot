"""
요청 관련 DTO classes
"""

from datetime import datetime
from typing import Optional, List
from pydantic import Field

from src.dto.common.base_dto import BaseDTO


class TaskCreateRequestDTO(BaseDTO):
    """Task 생성 요청 DTO"""

    title: str = Field(..., description="Task 제목")
    priority: str = Field(default="Medium", description="우선순위 (High/Medium/Low)")
    assignee: Optional[str] = Field(default=None, description="담당자")
    due_date: Optional[datetime] = Field(default=None, description="마감일")
    description: Optional[str] = Field(default=None, description="상세 설명")
    labels: Optional[List[str]] = Field(default_factory=list, description="태그 리스트")
    
    # 추가 메타데이터
    estimated_hours: Optional[float] = Field(default=None, description="예상 작업 시간")
    project: Optional[str] = Field(default=None, description="프로젝트명")


class MeetingCreateRequestDTO(BaseDTO):
    """Meeting 생성 요청 DTO"""

    title: str = Field(..., description="회의 제목")
    meeting_type: str = Field(default="정기회의", description="회의 유형")
    attendees: List[str] = Field(default_factory=list, description="참석자 리스트")
    meeting_date: Optional[datetime] = Field(default=None, description="회의 일시")
    duration: Optional[int] = Field(default=60, description="회의 시간 (분)")
    location: Optional[str] = Field(default=None, description="회의 장소")
    agenda: Optional[str] = Field(default=None, description="회의 안건")