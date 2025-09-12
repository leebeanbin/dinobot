"""
DinoBot 동적 설정 시스템
- DB 프로퍼티를 동적으로 읽어서 설정
- 스키마 기반 자동 설정 생성
- 명령어별 동적 프로퍼티 매핑
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json

from src.core.config_manager import config_manager, ConfigSchema, ConfigType
from src.service.notion.notion_service import NotionService

logger = logging.getLogger(__name__)


class PropertyType(Enum):
    """Notion 프로퍼티 타입"""

    TITLE = "title"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    PEOPLE = "people"
    FILES = "files"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    FORMULA = "formula"
    RELATION = "relation"
    ROLLUP = "rollup"
    CREATED_TIME = "created_time"
    CREATED_BY = "created_by"
    LAST_EDIT_TIME = "last_edited_time"
    LAST_EDIT_BY = "last_edited_by"
    STATUS = "status"


@dataclass
class DatabaseProperty:
    """데이터베이스 프로퍼티 정보"""

    name: str
    type: PropertyType
    description: str
    required: bool = False
    options: Optional[List[Dict[str, Any]]] = None
    default_value: Any = None
    validation_rules: Optional[Dict[str, Any]] = None


@dataclass
class DatabaseSchema:
    """데이터베이스 스키마 정보"""

    database_id: str
    database_name: str
    title_property: str
    properties: Dict[str, DatabaseProperty]
    categories: Dict[str, List[str]]  # 카테고리별 프로퍼티 그룹핑


@dataclass
class CommandMapping:
    """명령어별 프로퍼티 매핑"""

    command: str
    database_id: str
    required_properties: List[str]
    optional_properties: List[str]
    auto_set_properties: Dict[str, Any]  # 자동으로 설정될 프로퍼티들
    validation_rules: Dict[str, Dict[str, Any]]


class DynamicConfigManager:
    """동적 설정 관리자"""

    def __init__(self):
        self.notion_service: Optional[NotionService] = None
        self.database_schemas: Dict[str, DatabaseSchema] = {}
        self.command_mappings: Dict[str, CommandMapping] = {}

        # 기본 명령어 매핑 정의
        self._initialize_default_mappings()

    def _initialize_default_mappings(self):
        """기본 명령어 매핑 초기화"""
        # Meeting 명령어 매핑
        self.command_mappings["meeting"] = CommandMapping(
            command="meeting",
            database_id="BOARD_DB_ID",
            required_properties=["Name"],  # 제목은 필수
            optional_properties=["Participants", "Status", "Created time"],
            auto_set_properties={
                "Status": "회의록",  # 자동으로 회의록으로 설정
                "Created time": "now",  # 현재 시간으로 설정
            },
            validation_rules={
                "Name": {"min_length": 1, "max_length": 100},
                "Participants": {"type": "multi_select"},
                "Status": {
                    "allowed_values": ["개발 문서", "기획안", "개발 규칙", "회의록"]
                },
            },
        )

        # Board 명령어 매핑
        self.command_mappings["board"] = CommandMapping(
            command="board",
            database_id="BOARD_DB_ID",
            required_properties=["Name"],
            optional_properties=["Status", "Participants", "Created time"],
            auto_set_properties={
                "Status": "개발 문서",  # 기본값
                "Created time": "now",
            },
            validation_rules={
                "Name": {"min_length": 1, "max_length": 100},
                "Status": {
                    "allowed_values": ["개발 문서", "기획안", "개발 규칙", "회의록"]
                },
            },
        )

        # Factory 명령어 매핑
        self.command_mappings["factory"] = CommandMapping(
            command="factory",
            database_id="FACTORY_TRACKER_DB_ID",
            required_properties=["Task name"],
            optional_properties=[
                "Person",
                "Priority",
                "Status",
                "Due date",
                "Task type",
            ],
            auto_set_properties={"Status": "Not started", "Created time": "now"},
            validation_rules={
                "Task name": {"min_length": 1, "max_length": 200},
                "Priority": {"allowed_values": ["High", "Medium", "Low"]},
                "Status": {"allowed_values": ["Not started", "In progress", "Done"]},
            },
        )

    async def initialize(self, notion_service: NotionService):
        """동적 설정 관리자 초기화"""
        self.notion_service = notion_service
        await self._load_database_schemas()
        await self._sync_with_config_manager()

    async def _load_database_schemas(self):
        """데이터베이스 스키마 로드"""
        try:
            # Board DB 스키마 로드
            board_db_id = await config_manager.get("BOARD_DB_ID")
            if board_db_id:
                board_schema = await self._get_database_schema(
                    board_db_id, "Board Database"
                )
                self.database_schemas["board"] = board_schema

            # Factory Tracker DB 스키마 로드
            factory_db_id = await config_manager.get("FACTORY_TRACKER_DB_ID")
            if factory_db_id:
                factory_schema = await self._get_database_schema(
                    factory_db_id, "Factory Tracker Database"
                )
                self.database_schemas["factory"] = factory_schema

            logger.info(
                f"데이터베이스 스키마 로드 완료: {len(self.database_schemas)}개"
            )

        except Exception as e:
            logger.error(f"데이터베이스 스키마 로드 실패: {e}")

    async def _get_database_schema(
        self, database_id: str, database_name: str
    ) -> DatabaseSchema:
        """특정 데이터베이스의 스키마 정보 가져오기"""
        try:
            # Notion 서비스를 통해 스키마 정보 가져오기
            schema_data = await self.notion_service.get_database_schema(database_id)

            properties = {}
            title_property = None

            # 프로퍼티 파싱
            for prop_name, prop_info in schema_data.get("props", {}).items():
                prop_type = PropertyType(prop_info.get("type", "rich_text"))

                # 옵션 정보 추출
                options = None
                if prop_type in [
                    PropertyType.SELECT,
                    PropertyType.MULTI_SELECT,
                    PropertyType.STATUS,
                ]:
                    options = prop_info.get(prop_type.value, {}).get("options", [])

                # 제목 프로퍼티 찾기
                if prop_type == PropertyType.TITLE:
                    title_property = prop_name

                properties[prop_name] = DatabaseProperty(
                    name=prop_name,
                    type=prop_type,
                    description=f"{prop_name} 프로퍼티",
                    options=options,
                )

            # 카테고리별 프로퍼티 그룹핑
            categories = self._categorize_properties(properties)

            return DatabaseSchema(
                database_id=database_id,
                database_name=database_name,
                title_property=title_property or "Name",
                properties=properties,
                categories=categories,
            )

        except Exception as e:
            logger.error(f"데이터베이스 스키마 조회 실패 {database_id}: {e}")
            raise

    def _categorize_properties(
        self, properties: Dict[str, DatabaseProperty]
    ) -> Dict[str, List[str]]:
        """프로퍼티를 카테고리별로 그룹핑"""
        categories = {
            "basic": [],  # 기본 정보
            "metadata": [],  # 메타데이터
            "status": [],  # 상태 관련
            "people": [],  # 사람 관련
            "dates": [],  # 날짜 관련
            "content": [],  # 내용 관련
        }

        for prop_name, prop_info in properties.items():
            prop_type = prop_info.type

            if prop_type == PropertyType.TITLE:
                categories["basic"].append(prop_name)
            elif prop_type in [
                PropertyType.SELECT,
                PropertyType.MULTI_SELECT,
                PropertyType.STATUS,
            ]:
                categories["status"].append(prop_name)
            elif prop_type == PropertyType.PEOPLE:
                categories["people"].append(prop_name)
            elif prop_type in [
                PropertyType.DATE,
                PropertyType.CREATED_TIME,
                PropertyType.LAST_EDIT_TIME,
            ]:
                categories["dates"].append(prop_name)
            elif prop_type in [
                PropertyType.RICH_TEXT,
                PropertyType.NUMBER,
                PropertyType.CHECKBOX,
            ]:
                categories["content"].append(prop_name)
            else:
                categories["metadata"].append(prop_name)

        return categories

    async def _sync_with_config_manager(self):
        """설정 관리자와 동기화"""
        try:
            # 데이터베이스별 동적 설정 스키마 추가
            for db_name, schema in self.database_schemas.items():
                await self._add_database_config_schemas(db_name, schema)

            logger.info("동적 설정 스키마 동기화 완료")

        except Exception as e:
            logger.error(f"설정 관리자 동기화 실패: {e}")

    async def _add_database_config_schemas(self, db_name: str, schema: DatabaseSchema):
        """데이터베이스별 설정 스키마 추가"""
        # 데이터베이스 ID 설정 스키마
        db_id_key = f"{db_name.upper()}_DB_ID"
        if db_id_key not in config_manager.schemas:
            config_manager.add_schema(
                ConfigSchema(
                    key=db_id_key,
                    name=f"{schema.database_name} ID",
                    description=f"{schema.database_name}의 데이터베이스 ID",
                    type=ConfigType.STRING,
                    required=True,
                    category="database",
                )
            )

        # 프로퍼티별 설정 스키마 추가
        for prop_name, prop_info in schema.properties.items():
            config_key = f"{db_name.upper()}_{prop_name.upper().replace(' ', '_')}"

            # 설정 타입 매핑
            config_type = self._map_property_type_to_config_type(prop_info.type)

            if config_key not in config_manager.schemas:
                config_manager.add_schema(
                    ConfigSchema(
                        key=config_key,
                        name=f"{schema.database_name} - {prop_name}",
                        description=f"{schema.database_name}의 {prop_name} 프로퍼티 설정",
                        type=config_type,
                        required=False,
                        default_value=prop_info.default_value,
                        category=f"{db_name}_properties",
                    )
                )

    def _map_property_type_to_config_type(
        self, property_type: PropertyType
    ) -> ConfigType:
        """Notion 프로퍼티 타입을 설정 타입으로 매핑"""
        mapping = {
            PropertyType.TITLE: ConfigType.STRING,
            PropertyType.RICH_TEXT: ConfigType.STRING,
            PropertyType.NUMBER: ConfigType.FLOAT,
            PropertyType.SELECT: ConfigType.STRING,
            PropertyType.MULTI_SELECT: ConfigType.LIST,
            PropertyType.DATE: ConfigType.STRING,
            PropertyType.PEOPLE: ConfigType.LIST,
            PropertyType.CHECKBOX: ConfigType.BOOLEAN,
            PropertyType.URL: ConfigType.STRING,
            PropertyType.EMAIL: ConfigType.STRING,
            PropertyType.PHONE_NUMBER: ConfigType.STRING,
            PropertyType.CREATED_TIME: ConfigType.STRING,
            PropertyType.LAST_EDIT_TIME: ConfigType.STRING,
            PropertyType.STATUS: ConfigType.STRING,
        }
        return mapping.get(property_type, ConfigType.STRING)

    def get_command_mapping(self, command: str) -> Optional[CommandMapping]:
        """명령어별 매핑 정보 가져오기"""
        return self.command_mappings.get(command)

    def get_database_schema(self, database_name: str) -> Optional[DatabaseSchema]:
        """데이터베이스 스키마 가져오기"""
        return self.database_schemas.get(database_name)

    def get_property_options(self, database_name: str, property_name: str) -> List[str]:
        """프로퍼티 옵션 가져오기"""
        schema = self.database_schemas.get(database_name)
        if schema and property_name in schema.properties:
            prop_info = schema.properties[property_name]
            if prop_info.options:
                return [option.get("name", "") for option in prop_info.options]
        return []

    def validate_command_input(
        self, command: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """명령어 입력 검증"""
        mapping = self.get_command_mapping(command)
        if not mapping:
            return {"valid": False, "error": f"알 수 없는 명령어: {command}"}

        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "processed_data": {},
        }

        # 필수 프로퍼티 검증
        for required_prop in mapping.required_properties:
            if required_prop not in input_data or not input_data[required_prop]:
                validation_result["errors"].append(
                    f"필수 프로퍼티 '{required_prop}'가 누락되었습니다."
                )
                validation_result["valid"] = False

        # 프로퍼티 값 검증
        for prop_name, value in input_data.items():
            if prop_name in mapping.validation_rules:
                rules = mapping.validation_rules[prop_name]

                # 길이 검증
                if "min_length" in rules and len(str(value)) < rules["min_length"]:
                    validation_result["errors"].append(
                        f"'{prop_name}'은 최소 {rules['min_length']}자 이상이어야 합니다."
                    )
                    validation_result["valid"] = False

                if "max_length" in rules and len(str(value)) > rules["max_length"]:
                    validation_result["errors"].append(
                        f"'{prop_name}'은 최대 {rules['max_length']}자까지 가능합니다."
                    )
                    validation_result["valid"] = False

                # 허용된 값 검증
                if "allowed_values" in rules and value not in rules["allowed_values"]:
                    validation_result["errors"].append(
                        f"'{prop_name}'은 다음 값 중 하나여야 합니다: {', '.join(rules['allowed_values'])}"
                    )
                    validation_result["valid"] = False

        # 자동 설정 프로퍼티 추가
        processed_data = input_data.copy()
        for auto_prop, auto_value in mapping.auto_set_properties.items():
            if auto_value == "now":
                from datetime import datetime

                processed_data[auto_prop] = datetime.now().isoformat()
            else:
                processed_data[auto_prop] = auto_value

        validation_result["processed_data"] = processed_data

        return validation_result

    async def get_command_help(self, command: str) -> Dict[str, Any]:
        """명령어 도움말 생성"""
        mapping = self.get_command_mapping(command)
        if not mapping:
            return {"error": f"알 수 없는 명령어: {command}"}

        # 데이터베이스 스키마 가져오기
        db_id_key = mapping.database_id
        db_id = await config_manager.get(db_id_key)

        schema = None
        for db_name, db_schema in self.database_schemas.items():
            if db_schema.database_id == db_id:
                schema = db_schema
                break

        help_info = {
            "command": command,
            "database": schema.database_name if schema else "Unknown",
            "required_properties": [],
            "optional_properties": [],
            "auto_set_properties": mapping.auto_set_properties,
            "examples": [],
        }

        # 필수 프로퍼티 정보
        for prop_name in mapping.required_properties:
            prop_info = schema.properties.get(prop_name) if schema else None
            help_info["required_properties"].append(
                {
                    "name": prop_name,
                    "type": prop_info.type.value if prop_info else "unknown",
                    "description": prop_info.description if prop_info else "",
                    "options": prop_info.options if prop_info else [],
                }
            )

        # 선택적 프로퍼티 정보
        for prop_name in mapping.optional_properties:
            prop_info = schema.properties.get(prop_name) if schema else None
            help_info["optional_properties"].append(
                {
                    "name": prop_name,
                    "type": prop_info.type.value if prop_info else "unknown",
                    "description": prop_info.description if prop_info else "",
                    "options": prop_info.options if prop_info else [],
                }
            )

        # 예시 생성
        if command == "meeting":
            help_info["examples"].append(
                {
                    "description": "회의록 생성",
                    "usage": "/meeting title:프로젝트 회의 meeting_time:오늘 14:00 participants:정빈,소현",
                    "result": "Board Database에 회의록 페이지 생성, Status 자동 설정",
                }
            )
        elif command == "board":
            help_info["examples"].append(
                {
                    "description": "문서 생성",
                    "usage": "/board title:API 설계서 doc_type:개발 문서",
                    "result": "Board Database에 문서 페이지 생성",
                }
            )
        elif command == "factory":
            help_info["examples"].append(
                {
                    "description": "작업 생성",
                    "usage": "/factory title:버그 수정 priority:High assignee:정빈",
                    "result": "Factory Tracker Database에 작업 페이지 생성",
                }
            )

        return help_info


# 전역 동적 설정 관리자 인스턴스
dynamic_config_manager = DynamicConfigManager()
