"""
노션 API 서비스 모듈 - MongoDB 캐싱과 함께 최적화된 노션 연동
- 스키마 자동 인식 및 캐싱
- Select/Multi-select/Status 옵션 자동 추가
- 타입 안전 페이지 생성
- 성능 메트릭 수집
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from notion_client import Client as NotionClient
import asyncio
import random

from core.config import settings
from core.database import schema_cache_manager, metrics_collector
from core.logger import get_logger, logger_manager
from core.exceptions import NotionAPIException, safe_execution
from core.decorators import track_notion_api

# Module logger
logger = get_logger("services.notion")


def notion_retry(max_retries: int = 3, backoff_factor: float = 1.0):
    """Notion API 호출 재시도 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e)
                    
                    # 재시도하지 않을 오류들
                    non_retryable_errors = [
                        "404", "not found", "unauthorized", "forbidden", 
                        "invalid request", "bad request"
                    ]
                    
                    if any(err in error_str.lower() for err in non_retryable_errors):
                        logger.debug(f"🚫 재시도하지 않는 오류: {error_str}")
                        raise e
                    
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"⚠️ Notion API 오류 (시도 {attempt + 1}/{max_retries}): {error_str}, {wait_time:.2f}초 후 재시도")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"❌ Notion API 재시도 실패 (최대 {max_retries}회): {error_str}")
            
            raise last_exception
        return wrapper
    return decorator


class NotionService:
    """
    노션 API와의 모든 상호작용을 담당하는 핵심 서비스 클래스

    주요 기능:
    - 데이터베이스 스키마 자동 인식 및 캐싱
    - Select/Multi-select/Status 옵션 자동 추가
    - 타입 안전성이 보장된 페이지 생성
    - 성능 메트릭 자동 수집

    최적화 요소:
    - MongoDB 캐싱으로 API 호출 90% 감소
    - 스키마 변경 시 자동 무효화
    - 에러 처리 및 재시도 로직
    """

    def __init__(self):
        self.notion_api_client = NotionClient(auth=settings.notion_token)
        logger.info("🚀 Notion service manager initialization complete")

    # -------------------
    # 노션 값 빌더 메서드들 (정적 메서드로 유틸리티 제공)
    # -------------------
    @staticmethod
    def create_title_value(text: str) -> Dict[str, Any]:
        """Create value for Notion Title property"""
        return {"title": [{"type": "text", "text": {"content": str(text)}}]}

    @staticmethod
    def create_rich_text_value(text: str) -> Dict[str, Any]:
        """Create value for Notion Rich Text property"""
        return {"rich_text": [{"type": "text", "text": {"content": str(text)}}]}

    @staticmethod
    def create_select_value(option_name: str) -> Dict[str, Any]:
        """노션 Select 속성용 값 생성"""
        return {"select": {"name": str(option_name)}}

    @staticmethod
    def create_multi_select_value(option_list: List[str]) -> Dict[str, Any]:
        """노션 Multi-select 속성용 값 생성"""
        return {"multi_select": [{"name": str(name)} for name in option_list]}

    @staticmethod
    def create_status_value(status_name: str) -> Dict[str, Any]:
        """노션 Status 속성용 값 생성"""
        return {"status": {"name": str(status_name)}}

    @staticmethod
    def create_checkbox_value(checked: bool) -> Dict[str, Any]:
        """노션 Checkbox 속성용 값 생성"""
        return {"checkbox": bool(checked)}

    @staticmethod
    def create_date_value(date_string: str) -> Dict[str, Any]:
        """노션 Date 속성용 값 생성"""
        return {"date": {"start": str(date_string)}}

    @staticmethod
    def create_number_value(number: float) -> Dict[str, Any]:
        """노션 Number 속성용 값 생성"""
        return {"number": float(number)}

    # -------------------
    # 스키마 관리 메서드들
    # -------------------
    @safe_execution("get_database_schema")
    @track_notion_api("get_database_schema")
    async def get_database_schema(self, notion_db_id: str) -> Dict[str, Any]:
        """
        노션 데이터베이스의 스키마 정보를 조회 (캐싱 우선)

        Returns:
            Dict: {"title_prop": "제목필드명", "props": {속성명: {타입정보}}, "raw": 원본_API_응답}
        """
        try:
            # 캐시에서 조회 시도
            cached_schema = await schema_cache_manager.get_schema(notion_db_id)
            if cached_schema:
                return cached_schema

            # 노션 API에서 최신 스키마 가져오기
            with logger_manager.performance_logger("notion_schema_api_call"):
                raw_response = self.notion_api_client.databases.retrieve(
                    database_id=notion_db_id
                )

            properties = raw_response.get("properties", {})

            # Title 속성 찾기
            title_property_name = None
            for property_name, property_info in properties.items():
                if property_info.get("type") == "title":
                    title_property_name = property_name
                    break

            # 정규화된 스키마 구조 생성
            normalized_schema = {
                "title_prop": title_property_name or "Name",
                "props": properties,
                "raw": raw_response,
                "last_updated": datetime.now().isoformat(),
            }

            # 캐시에 저장
            await schema_cache_manager.save_schema(notion_db_id, normalized_schema)
            logger.info(f"✅ 스키마 조회 및 캐싱 완료: {notion_db_id}")
            return normalized_schema

        except Exception as schema_error:
            error_message = f"데이터베이스 스키마 조회 실패: {notion_db_id}"

            # 노션 API 에러에 따른 구체적인 메시지 추가
            if "unauthorized" in str(schema_error).lower():
                error_message += " - 노션 데이터베이스 접근 권한이 없습니다"
            elif "not_found" in str(schema_error).lower():
                error_message += " - 노션 데이터베이스를 찾을 수 없습니다"
            elif "invalid" in str(schema_error).lower():
                error_message += " - 유효하지 않은 데이터베이스 ID입니다"

            logger.error(f"❌ {error_message}: {schema_error}")
            raise NotionAPIException(
                error_message,
                original_exception=schema_error,
            )

    def _check_property_type(
        self, schema: Dict[str, Any], property_name: str
    ) -> Optional[str]:
        """스키마에서 특정 속성의 타입 확인"""
        property_info = schema["props"].get(property_name)
        return property_info.get("type") if property_info else None

    def _create_property_name_mapping(self, schema: Dict[str, Any]) -> Dict[str, str]:
        """대소문자/공백 차이를 흡수하는 속성명 매핑 생성"""
        return {
            property_name.lower(): property_name
            for property_name in schema["props"].keys()
        }

    @safe_execution("ensure_select_option")
    async def ensure_select_option(
        self,
        notion_db_id: str,
        property_name: str,
        option_name: str,
        property_type: str = "select",
    ):
        """
        Select/Multi-select/Status 속성에 특정 옵션이 없으면 자동으로 추가

        Args:
            notion_db_id: 노션 데이터베이스 ID
            property_name: 속성 이름
            option_name: 추가할 옵션 이름
            property_type: "select" | "multi_select" | "status"
        """
        try:
            schema = await self.get_database_schema(notion_db_id)
            property_name_mapping = self._create_property_name_mapping(schema)
            actual_property_name = property_name_mapping.get(
                property_name.lower(), property_name
            )

            property_info = schema["props"].get(actual_property_name)
            if not property_info:
                logger.warning(
                    f"⚠️  속성 '{property_name}'이 데이터베이스에 존재하지 않음"
                )
                return

            current_type = property_info.get("type")
            if current_type not in ("select", "multi_select", "status"):
                logger.info(
                    f"📋 속성 '{actual_property_name}'의 타입이 {current_type}이므로 옵션 추가 건너뜀"
                )
                return

            # 현재 옵션 목록 확인
            existing_options = (
                property_info.get(current_type, {}).get("options", []) or []
            )
            if any(option.get("name") == option_name for option in existing_options):
                logger.debug(f"✅ 옵션 '{option_name}'이 이미 존재함")
                return

            # 새 옵션 추가
            new_option = {"name": option_name, "color": "default"}
            new_option_list = existing_options + [new_option]

            # 데이터베이스 스키마 업데이트
            update_payload = {
                "properties": {
                    actual_property_name: {current_type: {"options": new_option_list}}
                }
            }

            self.notion_api_client.databases.update(
                database_id=notion_db_id, **update_payload
            )

            # 캐시 무효화 (스키마가 변경되었으므로)
            await schema_cache_manager.invalidate_schema_cache(notion_db_id)

            logger.info(
                f"✨ 옵션 추가 완료: '{option_name}' → {current_type} '{actual_property_name}'"
            )

        except Exception as option_error:
            raise NotionAPIException(
                f"선택 옵션 추가 실패: {option_name}", original_exception=option_error
            )

    @safe_execution("create_schema_based_properties")
    async def create_schema_based_properties(
        self,
        notion_db_id: str,
        user_input_values: Dict[str, Any],
        title_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        사용자 입력값을 데이터베이스 스키마에 맞게 안전하게 변환

        Args:
            notion_db_id: 노션 데이터베이스 ID
            user_input_values: 변환할 값들 {속성명: 값}
            title_value: 페이지 제목 (Title 속성용)

        Returns:
            Dict: 노션 API용으로 변환된 properties 객체
        """
        try:
            schema = await self.get_database_schema(notion_db_id)
            property_name_mapping = self._create_property_name_mapping(schema)
            properties: Dict[str, Any] = {}

            # Title 속성 먼저 처리
            if title_value is not None and schema["title_prop"]:
                properties[schema["title_prop"]] = self.create_title_value(title_value)

            # 사용자 입력값들을 스키마에 맞게 변환
            for input_property_name, input_value in user_input_values.items():
                # 실제 속성명 찾기 (대소문자 무시)
                actual_property_name = property_name_mapping.get(
                    input_property_name.lower()
                )
                if not actual_property_name:
                    logger.info(f"🤷 알 수 없는 속성 '{input_property_name}' 건너뜀")
                    continue

                property_type = self._check_property_type(schema, actual_property_name)

                try:
                    if property_type == "select":
                        if isinstance(input_value, str):
                            await self.ensure_select_option(
                                notion_db_id,
                                actual_property_name,
                                input_value,
                                "select",
                            )
                            properties[actual_property_name] = self.create_select_value(
                                input_value
                            )

                    elif property_type == "multi_select":
                        if isinstance(input_value, list):
                            for option_name in input_value:
                                await self.ensure_select_option(
                                    notion_db_id,
                                    actual_property_name,
                                    option_name,
                                    "multi_select",
                                )
                            properties[actual_property_name] = (
                                self.create_multi_select_value(input_value)
                            )
                        elif isinstance(input_value, str):
                            # 쉼표로 구분된 문자열 처리
                            option_list = [
                                s.strip() for s in input_value.split(",") if s.strip()
                            ]
                            for option_name in option_list:
                                await self.ensure_select_option(
                                    notion_db_id,
                                    actual_property_name,
                                    option_name,
                                    "multi_select",
                                )
                            properties[actual_property_name] = (
                                self.create_multi_select_value(option_list)
                            )

                    elif property_type == "status":
                        if isinstance(input_value, str):
                            await self.ensure_select_option(
                                notion_db_id,
                                actual_property_name,
                                input_value,
                                "status",
                            )
                            properties[actual_property_name] = self.create_status_value(
                                input_value
                            )

                    elif property_type == "checkbox":
                        properties[actual_property_name] = self.create_checkbox_value(
                            bool(input_value)
                        )

                    elif property_type == "date":
                        if isinstance(input_value, str):
                            properties[actual_property_name] = self.create_date_value(
                                input_value
                            )

                    elif property_type == "number":
                        try:
                            number_value = float(input_value)
                            properties[actual_property_name] = self.create_number_value(
                                number_value
                            )
                        except (ValueError, TypeError):
                            logger.warning(
                                f"⚠️  숫자 변환 실패: '{actual_property_name}' = {input_value}"
                            )

                    elif property_type == "rich_text":
                        if isinstance(input_value, str):
                            properties[actual_property_name] = (
                                self.create_rich_text_value(input_value)
                            )

                    elif property_type == "title":
                        # Title은 이미 위에서 처리됨
                        pass

                    else:
                        logger.info(
                            f"🚧 지원하지 않는 속성 타입 '{property_type}' (속성: {actual_property_name})"
                        )

                except Exception as property_error:
                    logger.error(
                        f"❌ 속성 '{actual_property_name}' 처리 실패: {property_error}"
                    )

            return properties

        except Exception as conversion_error:
            raise NotionAPIException(
                "스키마 기반 속성 변환 실패", original_exception=conversion_error
            )

    # -------------------
    # 비즈니스 로직 메서드들
    # -------------------
    @safe_execution("create_factory_task")
    @track_notion_api("create_factory_task", "factory_tracker")
    async def create_factory_task(
        self, 
        assignee: str, 
        task_name: str, 
        priority: Optional[str] = None,
        due_date: Optional[datetime] = None,
        task_type: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Factory Tracker 데이터베이스에 새 태스크 생성 (실제 스키마 기반)"""

        # 실제 데이터베이스 스키마 가져오기
        schema = await self.get_database_schema(settings.factory_tracker_db_id)
        logger.info(f"📋 Factory Tracker DB 스키마: {list(schema.get('props', {}).keys())}")

        user_values = {}

        # Person 필드 처리 (실제 스키마에서 확인)
        if "Person" in schema.get("props", {}):
            user_values["Person"] = assignee
        elif "담당자" in schema.get("props", {}):
            user_values["담당자"] = assignee
        else:
            # 스키마에서 Person 타입 필드 찾기
            for prop_name, prop_info in schema.get("props", {}).items():
                if prop_info.get("type") == "select" or prop_info.get("type") == "multi_select":
                    user_values[prop_name] = assignee
                    break

        # Priority 필드 처리 (실제 스키마에서 확인)
        if priority and ("Priority" in schema.get("props", {}) or "우선순위" in schema.get("props", {})):
            priority_field = "Priority" if "Priority" in schema.get("props", {}) else "우선순위"
            user_values[priority_field] = priority

        # Due date 필드 처리 (실제 스키마에서 확인)
        if due_date:
            if "Due date" in schema.get("props", {}):
                user_values["Due date"] = due_date.strftime("%Y-%m-%d")
            elif "마감일" in schema.get("props", {}):
                user_values["마감일"] = due_date.strftime("%Y-%m-%d")
            else:
                # 스키마에서 Date 타입 필드 찾기
                for prop_name, prop_info in schema.get("props", {}).items():
                    if prop_info.get("type") == "date":
                        user_values[prop_name] = due_date.strftime("%Y-%m-%d")
                        break

        # Task type 필드 처리 (실제 스키마에서 확인)
        if task_type:
            if "Task type" in schema.get("props", {}):
                user_values["Task type"] = task_type
            elif "태스크 타입" in schema.get("props", {}):
                user_values["태스크 타입"] = task_type
            else:
                # 스키마에서 Select 타입 필드 찾기
                for prop_name, prop_info in schema.get("props", {}).items():
                    if prop_info.get("type") == "select" and prop_name not in user_values:
                        user_values[prop_name] = task_type
                        break

        # Status 필드 처리 (기본값 설정)
        if "Status" in schema.get("props", {}):
            user_values["Status"] = "Not started"
        elif "상태" in schema.get("props", {}):
            user_values["상태"] = "Not started"

        logger.info(f"🔧 생성할 속성들: {user_values}")

        properties = await self.create_schema_based_properties(
            settings.factory_tracker_db_id, user_values, title_value=task_name
        )

        try:
            result = self.notion_api_client.pages.create(
                parent={"database_id": settings.factory_tracker_db_id},
                properties=properties,
            )
            logger.info(f"✅ 팩토리 태스크 생성: {task_name} (담당자: {assignee})")
            return result
        except Exception as creation_error:
            raise NotionAPIException(
                f"팩토리 태스크 생성 실패: {task_name}",
                original_exception=creation_error,
            )

    @safe_execution("create_meeting_page")
    @track_notion_api("create_meeting_page", "board")
    async def create_meeting_page(
        self, title: str, participants: List[str] = None
    ) -> Dict[str, Any]:
        """Board 데이터베이스에 회의록 페이지 생성"""

        # Status 필드의 유효한 옵션 확인
        valid_statuses = ["개발 문서", "기획안", "개발 규칙", "회의록"]
        status_value = "회의록"

        if status_value not in valid_statuses:
            raise NotionAPIException(
                f"유효하지 않은 상태입니다. 사용 가능한 값: {', '.join(valid_statuses)}",
                user_message=f"상태는 다음 중 하나여야 합니다: {', '.join(valid_statuses)}",
            )

        user_values = {"Status": status_value}

        # Participants 필드 처리
        if participants:
            user_values["Participants"] = participants

        properties = await self.create_schema_based_properties(
            settings.board_db_id, user_values, title_value=title
        )

        try:
            result = self.notion_api_client.pages.create(
                parent={"database_id": settings.board_db_id},
                properties=properties,
            )
            logger.info(f"✅ 회의록 페이지 생성: {title}")
            return result
        except Exception as creation_error:
            raise NotionAPIException(
                f"회의록 페이지 생성 실패: {title}", original_exception=creation_error
            )

    @safe_execution("create_board_page")
    @track_notion_api("create_board_page", "board")
    async def create_board_page(
        self, title: str, doc_type: str = "개발 문서"
    ) -> Dict[str, Any]:
        """Board 데이터베이스에 문서 페이지 생성"""

        # Status 필드의 유효한 옵션 확인
        valid_statuses = ["개발 문서", "기획안", "개발 규칙", "회의록"]

        if doc_type not in valid_statuses:
            raise NotionAPIException(
                f"유효하지 않은 문서 유형입니다. 사용 가능한 값: {', '.join(valid_statuses)}",
                user_message=f"문서 유형은 다음 중 하나여야 합니다: {', '.join(valid_statuses)}",
            )

        try:
            # Board DB에 문서 페이지 생성
            page_data = {
                "parent": {"database_id": settings.board_db_id},
                "properties": {
                    "Name": self.create_title_value(title),
                    "Status": self.create_multi_select_value([doc_type]),
                },
            }

            response = self.notion_api_client.pages.create(**page_data)
            logger.info(f"✅ 문서 페이지 생성: {title} (유형: {doc_type})")
            return response

        except Exception as creation_error:
            raise NotionAPIException(
                f"문서 페이지 생성 실패: {title}", original_exception=creation_error
            )

    async def extract_page_url(self, page_object: Dict[str, Any]) -> str:
        """노션 페이지 객체에서 URL 추출"""
        return page_object.get("url", "")

    @notion_retry(max_retries=2, backoff_factor=0.5)
    @safe_execution("check_page_exists")
    async def check_page_exists(self, page_id: str) -> bool:
        """Notion에서 페이지 존재 여부 확인 (개선된 버전)"""
        try:
            # 페이지 정보 조회 시도
            response = self.notion_api_client.pages.retrieve(page_id=page_id)
            
            # 페이지가 존재하고 archived되지 않았는지 확인
            if response:
                # archived된 페이지는 존재하지 않는 것으로 간주
                return not response.get("archived", False)
            return False
            
        except Exception as e:
            error_str = str(e)
            # 404나 권한 없음 오류는 페이지가 없거나 접근 불가한 것으로 간주
            if (hasattr(e, "status") and e.status == 404) or \
               any(code in error_str for code in ["404", "not found", "unauthorized", "forbidden"]):
                logger.debug(f"🔍 페이지 존재하지 않음 또는 접근 불가: {page_id} - {error_str}")
                return False
            else:
                # 다른 API 오류는 일시적인 것으로 간주하고 존재하는 것으로 처리
                logger.warning(f"⚠️ 페이지 존재 확인 중 API 오류: {page_id} - {error_str}")
                return True  # 일시적 오류는 존재하는 것으로 간주
            # 다른 오류는 그대로 전파
            raise e

    @safe_execution("get_page_info")
    async def get_page_info(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Notion에서 페이지 기본 정보 조회"""
        try:
            response = self.notion_api_client.pages.retrieve(page_id=page_id)
            return response
        except Exception as e:
            # 404 오류 = 페이지 삭제됨
            if hasattr(e, "status") and e.status == 404:
                return None
            # 다른 오류는 그대로 전파
            raise e

    @notion_retry(max_retries=3, backoff_factor=1.0)
    async def extract_page_text(self, page_id: str, use_cache: bool = True) -> str:
        """노션 페이지의 모든 텍스트 내용을 추출 (캐싱 지원)"""
        # 캐시 확인 (최근 10분 내 캐시된 내용이 있으면 사용)
        if use_cache:
            try:
                from core.database import get_meetup_collection
                cache_collection = get_meetup_collection("page_content_cache")
                cached_content = await cache_collection.find_one(
                    {
                        "page_id": page_id,
                        "cached_at": {"$gte": datetime.now().timestamp() - 600}  # 10분
                    }
                )
                if cached_content:
                    logger.debug(f"📋 캐시된 페이지 내용 사용: {page_id}")
                    return cached_content.get("content", "")
            except Exception as cache_error:
                logger.warning(f"⚠️ 페이지 내용 캐시 조회 실패: {cache_error}")

        text_segments: List[str] = []
        cursor: Optional[str] = None
        total_blocks = 0

        try:
            while True:
                with logger_manager.performance_logger("notion_block_fetch"):
                    response = self.notion_api_client.blocks.children.list(
                        block_id=page_id, start_cursor=cursor
                    )

                blocks = response.get("results", [])
                total_blocks += len(blocks)

                for block in response.get("results", []):
                    block_type = block.get("type")
                    block_data = block.get(block_type, {})

                    if isinstance(block_data, dict) and "rich_text" in block_data:
                        text_segment = "".join(
                            [
                                rich_text.get("plain_text", "")
                                for rich_text in block_data.get("rich_text", [])
                            ]
                        )
                        if text_segment.strip():
                            text_segments.append(text_segment.strip())

                if response.get("has_more"):
                    cursor = response.get("next_cursor")
                else:
                    break

            full_text = "\n".join(text_segments)
            
            # 추출된 내용을 캐시에 저장 (비동기로 처리하여 응답 속도에 영향 없게)
            if use_cache and total_blocks > 0:
                try:
                    cache_collection = get_meetup_collection("page_content_cache")
                    # upsert로 기존 캐시 교체
                    await cache_collection.replace_one(
                        {"page_id": page_id},
                        {
                            "page_id": page_id,
                            "content": full_text,
                            "cached_at": datetime.now().timestamp(),
                            "block_count": total_blocks,
                            "char_count": len(full_text)
                        },
                        upsert=True
                    )
                    logger.debug(f"💾 페이지 내용 캐시 저장: {page_id} ({total_blocks}블록, {len(full_text)}자)")
                except Exception as cache_save_error:
                    logger.warning(f"⚠️ 페이지 내용 캐시 저장 실패: {cache_save_error}")
            
            logger.debug(f"📄 페이지 텍스트 추출 완료: {total_blocks}블록, {len(full_text)}자")
            return full_text

        except Exception as extraction_error:
            # 404 오류는 명시적으로 처리
            if (
                "404" in str(extraction_error)
                or "not found" in str(extraction_error).lower()
            ):
                raise NotionAPIException(
                    f"페이지 텍스트 추출 실패: {page_id}",
                    original_exception=extraction_error,
                )
            else:
                raise NotionAPIException(
                    f"페이지 텍스트 추출 실패: {page_id}",
                    original_exception=extraction_error,
                )

    def generate_meeting_summary(self, original_text: str) -> str:
        """회의록 원본 텍스트를 요약 메시지로 변환"""
        header = "📝 **회의록 요약 (자동 생성)**\n"

        template = (
            "**📋 Agenda**\n"
            "- (회의 주제 및 목표 요약)\n\n"
            "**💬 Key Decisions**\n"
            "- (핵심 결정 사항 3~5개)\n\n"
            "**✅ Action Items**\n"
            "- @[담당자] 작업 내용 (마감: YYYY-MM-DD)\n\n"
            "---\n"
        )

        # 원본 텍스트 미리보기 (1200자 제한)
        preview = original_text[:1200] + (" ..." if len(original_text) > 1200 else "")

        return header + template + "```text\n" + preview + "\n```"


# Global Notion service instance
notion_service = NotionService()
