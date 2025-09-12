"""
DinoBot 설정 관리 시스템
- Claude Code 스타일의 동적 설정 관리
- 설정 추가/수정/삭제 기능
- 설정 검증 및 마이그레이션
"""

import os
import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigType(Enum):
    """설정 타입 정의"""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    LIST = "list"
    DICT = "dict"
    SECRET = "secret"  # 민감한 정보 (마스킹됨)


@dataclass
class ConfigSchema:
    """설정 스키마 정의"""

    key: str
    name: str
    description: str
    type: ConfigType
    required: bool = False
    default_value: Any = None
    validation_rules: Optional[Dict[str, Any]] = None
    category: str = "general"
    sensitive: bool = False


@dataclass
class ConfigValue:
    """설정 값 정의"""

    key: str
    value: Any
    source: str  # 'env', 'file', 'database', 'user_input'
    last_updated: Optional[str] = None
    validated: bool = False


class ConfigManager:
    """설정 관리자 클래스"""

    def __init__(self):
        # MongoDB 기반 설정 저장 (파일 시스템 사용 안함)
        self.client = None
        self.db = None
        self.collection = None

        # 설정 스키마와 값들
        self.schemas: Dict[str, ConfigSchema] = {}
        self.values: Dict[str, ConfigValue] = {}

        # 초기화
        self._load_default_schemas()
        self._load_schemas()
        self._load_values()
        self._sync_with_env()

    def _load_default_schemas(self):
        """기본 설정 스키마 로드"""
        default_schemas = [
            # Discord 설정
            ConfigSchema(
                key="DISCORD_TOKEN",
                name="Discord Bot Token",
                description="Discord 봇 토큰 (필수)",
                type=ConfigType.SECRET,
                required=True,
                category="discord",
            ),
            ConfigSchema(
                key="DISCORD_APP_ID",
                name="Discord Application ID",
                description="Discord 애플리케이션 ID (필수)",
                type=ConfigType.STRING,
                required=True,
                category="discord",
            ),
            ConfigSchema(
                key="DISCORD_GUILD_ID",
                name="Discord Guild ID",
                description="Discord 서버 ID (필수)",
                type=ConfigType.STRING,
                required=True,
                category="discord",
            ),
            ConfigSchema(
                key="DEFAULT_DISCORD_CHANNEL_ID",
                name="Default Discord Channel ID",
                description="기본 Discord 채널 ID",
                type=ConfigType.STRING,
                required=False,
                category="discord",
            ),
            # Notion 설정
            ConfigSchema(
                key="NOTION_TOKEN",
                name="Notion Integration Token",
                description="Notion 통합 토큰 (필수)",
                type=ConfigType.SECRET,
                required=True,
                category="notion",
            ),
            ConfigSchema(
                key="FACTORY_TRACKER_DB_ID",
                name="Factory Tracker Database ID",
                description="Factory Tracker 데이터베이스 ID (필수)",
                type=ConfigType.STRING,
                required=True,
                category="notion",
            ),
            ConfigSchema(
                key="BOARD_DB_ID",
                name="Board Database ID",
                description="Board 데이터베이스 ID (필수)",
                type=ConfigType.STRING,
                required=True,
                category="notion",
            ),
            # 보안 설정
            ConfigSchema(
                key="WEBHOOK_SECRET",
                name="Webhook Secret Key",
                description="웹훅 보안을 위한 시크릿 키 (필수)",
                type=ConfigType.SECRET,
                required=True,
                category="security",
            ),
            # 서버 설정
            ConfigSchema(
                key="HOST",
                name="Server Host",
                description="서버 호스트 주소",
                type=ConfigType.STRING,
                default_value="0.0.0.0",
                category="server",
            ),
            ConfigSchema(
                key="PORT",
                name="Server Port",
                description="서버 포트 번호",
                type=ConfigType.INTEGER,
                default_value=8889,
                validation_rules={"min": 1000, "max": 65535},
                category="server",
            ),
            ConfigSchema(
                key="LOG_LEVEL",
                name="Log Level",
                description="로그 레벨",
                type=ConfigType.STRING,
                default_value="INFO",
                validation_rules={"choices": ["DEBUG", "INFO", "WARNING", "ERROR"]},
                category="server",
            ),
            ConfigSchema(
                key="TIMEZONE",
                name="Timezone",
                description="시간대 설정",
                type=ConfigType.STRING,
                default_value="Asia/Seoul",
                category="server",
            ),
            # 데이터베이스 설정
            ConfigSchema(
                key="MONGODB_URL",
                name="MongoDB URL",
                description="MongoDB 연결 URL",
                type=ConfigType.STRING,
                default_value="mongodb://localhost:27017",
                category="database",
            ),
            ConfigSchema(
                key="MONGODB_DB_NAME",
                name="MongoDB Database Name",
                description="MongoDB 데이터베이스 이름",
                type=ConfigType.STRING,
                default_value="dinobot",
                category="database",
            ),
            # 모니터링 설정
            ConfigSchema(
                key="PROMETHEUS_PORT",
                name="Prometheus Port",
                description="Prometheus 메트릭 포트",
                type=ConfigType.INTEGER,
                default_value=9090,
                validation_rules={"min": 1000, "max": 65535},
                category="monitoring",
            ),
        ]

        for schema in default_schemas:
            self.schemas[schema.key] = schema

    async def initialize(self):
        """MongoDB 연결 및 초기화"""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            from src.core.config import settings

            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.db = self.client[settings.mongodb_db_name]
            self.collection = self.db["configurations"]

            # 인덱스 생성
            await self.collection.create_index("key", unique=True)

            # MongoDB에서 설정 로드
            await self._load_from_mongodb()
            
            # 환경변수와 동기화
            self._sync_with_env()
            
            # 토큰 암호화 시스템 초기화
            webhook_secret = await self.get("WEBHOOK_SECRET")
            if webhook_secret:
                from src.utils.encryption import initialize_token_encryption
                initialize_token_encryption(webhook_secret)

            logger.info("✅ MongoDB 기반 설정 관리자 초기화 완료")

        except Exception as e:
            logger.error(f"❌ 설정 관리자 초기화 실패: {e}")
            raise

    async def _load_from_mongodb(self):
        """MongoDB에서 설정 로드"""
        try:
            # 설정 값들 로드
            async for doc in self.collection.find({}):
                key = doc["key"]
                value = doc.get("value")
                source = doc.get("source", "unknown")
                updated_at = doc.get("updated_at")

                self.values[key] = ConfigValue(
                    key=key, value=value, source=source, updated_at=updated_at
                )

            logger.info(f"📊 MongoDB에서 설정 로드 완료: {len(self.values)}개")

        except Exception as e:
            logger.error(f"❌ MongoDB 설정 로드 실패: {e}")

    def _load_schemas(self):
        """기본 스키마만 로드 (MongoDB는 initialize에서 처리)"""
        pass

    def _load_values(self):
        """기본 값만 로드 (MongoDB는 initialize에서 처리)"""
        pass

    def _sync_with_env(self):
        """환경변수와 동기화 (dotenv 파일 포함)"""
        # .env 파일 로드
        load_dotenv()
        
        env_loaded_count = 0
        for key, schema in self.schemas.items():
            env_value = os.getenv(key)
            if env_value is not None:
                # 환경변수에서 값이 있으면 항상 우선순위 높음 (강제 덮어쓰기)
                self.values[key] = ConfigValue(
                    key=key,
                    value=self._convert_value(env_value, schema.type),
                    source="env",
                    validated=self._validate_value(env_value, schema),
                )
                env_loaded_count += 1
                logger.info(f"✅ 환경변수에서 설정 로드: {key}")
        
        logger.info(f"📋 환경변수 동기화 완료: {env_loaded_count}개 설정 로드")

    def _convert_value(self, value: str, config_type: ConfigType) -> Any:
        """문자열 값을 적절한 타입으로 변환"""
        try:
            if config_type == ConfigType.STRING:
                return str(value)
            elif config_type == ConfigType.INTEGER:
                return int(value)
            elif config_type == ConfigType.BOOLEAN:
                return value.lower() in ("true", "1", "yes", "on")
            elif config_type == ConfigType.FLOAT:
                return float(value)
            elif config_type == ConfigType.LIST:
                return json.loads(value) if value.startswith("[") else value.split(",")
            elif config_type == ConfigType.DICT:
                return json.loads(value) if value.startswith("{") else {}
            elif config_type == ConfigType.SECRET:
                return str(value)
            else:
                return value
        except Exception as e:
            logger.warning(f"값 변환 실패: {value} -> {config_type}: {e}")
            return value

    def _validate_value(self, value: Any, schema: ConfigSchema) -> bool:
        """값 검증"""
        try:
            # 타입 검증
            converted_value = self._convert_value(str(value), schema.type)

            # 추가 검증 규칙
            if schema.validation_rules:
                if "min" in schema.validation_rules and isinstance(
                    converted_value, (int, float)
                ):
                    if converted_value < schema.validation_rules["min"]:
                        return False
                if "max" in schema.validation_rules and isinstance(
                    converted_value, (int, float)
                ):
                    if converted_value > schema.validation_rules["max"]:
                        return False
                if "choices" in schema.validation_rules:
                    if converted_value not in schema.validation_rules["choices"]:
                        return False

            return True
        except Exception:
            return False

    async def get(self, key: str, default: Any = None) -> Any:
        """설정 값 가져오기 (MongoDB에서)"""
        try:
            doc = await self.collection.find_one({"key": key})
            if doc:
                return doc.get("value", default)
            elif key in self.schemas and self.schemas[key].default_value is not None:
                return self.schemas[key].default_value
            else:
                return default
        except Exception as e:
            logger.error(f"설정 조회 실패: {key}, {e}")
            return default

    async def set(self, key: str, value: Any, source: str = "user_input") -> bool:
        """설정 값 설정 (MongoDB에 저장)"""
        try:
            if key not in self.schemas:
                logger.warning(f"알 수 없는 설정 키: {key}")
                return False

            schema = self.schemas[key]

            # 값 검증
            if not self._validate_value(value, schema):
                logger.error(f"설정 값 검증 실패: {key} = {value}")
                return False

            # 값 변환
            converted_value = self._convert_value(str(value), schema.type)

            # MongoDB에 저장
            await self.collection.update_one(
                {"key": key},
                {
                    "$set": {
                        "key": key,
                        "value": converted_value,
                        "source": source,
                        "updated_at": datetime.now()
                    }
                },
                upsert=True
            )

            # 로컬 캐시 업데이트
            self.values[key] = ConfigValue(
                key=key, value=converted_value, source=source, validated=True
            )

            logger.info(f"✅ 설정 업데이트 완료: {key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 설정 저장 실패: {key}, {e}")
            return False

    def add_schema(self, schema: ConfigSchema) -> bool:
        """새로운 설정 스키마 추가"""
        try:
            self.schemas[schema.key] = schema
            self._save_schemas()
            logger.info(f"새 설정 스키마 추가: {schema.key}")
            return True
        except Exception as e:
            logger.error(f"스키마 추가 실패: {e}")
            return False

    def remove_schema(self, key: str) -> bool:
        """설정 스키마 제거"""
        try:
            if key in self.schemas:
                del self.schemas[key]
            if key in self.values:
                del self.values[key]
            self._save_schemas()
            self._save_values()
            logger.info(f"설정 스키마 제거: {key}")
            return True
        except Exception as e:
            logger.error(f"스키마 제거 실패: {e}")
            return False

    async def get_all_configs(self) -> Dict[str, Any]:
        """모든 설정 반환 (민감한 정보 마스킹)"""
        result = {}
        for key, schema in self.schemas.items():
            value = await self.get(key)
            if schema.sensitive and value:
                result[key] = "***MASKED***"
            else:
                result[key] = value
        return result

    def is_fully_configured(self) -> bool:
        """필수 설정이 모두 완료되었는지 확인"""
        required_configs = [
            "DISCORD_TOKEN",
            "DISCORD_APP_ID",
            "DISCORD_GUILD_ID",
            "NOTION_TOKEN",
            "FACTORY_TRACKER_DB_ID",
            "BOARD_DB_ID",
            "WEBHOOK_SECRET",
        ]

        for key in required_configs:
            if key not in self.values or not self.values[key].value:
                return False
        return True

    def get_missing_configs(self) -> List[str]:
        """누락된 필수 설정 목록 반환"""
        required_configs = [
            "DISCORD_TOKEN",
            "DISCORD_APP_ID",
            "DISCORD_GUILD_ID",
            "NOTION_TOKEN",
            "FACTORY_TRACKER_DB_ID",
            "BOARD_DB_ID",
            "WEBHOOK_SECRET",
        ]

        missing = []
        for key in required_configs:
            if key not in self.values or not self.values[key].value:
                missing.append(key)
        return missing

    def get_configs_by_category(self, category: str) -> Dict[str, Any]:
        """카테고리별 설정 반환"""
        result = {}
        for key, schema in self.schemas.items():
            if schema.category == category:
                value = self.get(key)
                if schema.sensitive and value:
                    result[key] = "***MASKED***"
                else:
                    result[key] = value
        return result

    def get_missing_required_configs(self) -> List[str]:
        """필수 설정 중 누락된 것들 반환"""
        missing = []
        for key, schema in self.schemas.items():
            if schema.required and key not in self.values:
                missing.append(key)
        return missing

    def export_to_env(self, file_path: Optional[str] = None) -> bool:
        """설정을 .env 파일로 내보내기"""
        try:
            env_file = Path(file_path) if file_path else self.env_file

            with open(env_file, "w", encoding="utf-8") as f:
                f.write("# DinoBot Configuration\n")
                f.write("# Generated by ConfigManager\n\n")

                # 카테고리별로 그룹화
                categories = {}
                for key, schema in self.schemas.items():
                    if schema.category not in categories:
                        categories[schema.category] = []
                    categories[schema.category].append((key, schema))

                for category, configs in categories.items():
                    f.write(f"# {category.upper()} SETTINGS\n")
                    for key, schema in configs:
                        value = self.get(key)
                        if value is not None:
                            f.write(f"{key}={value}\n")
                    f.write("\n")

            logger.info(f"설정을 .env 파일로 내보내기 완료: {env_file}")
            return True
        except Exception as e:
            logger.error(f".env 파일 내보내기 실패: {e}")
            return False

    def _save_schemas(self):
        """스키마 파일 저장"""
        try:
            data = {"schemas": [asdict(schema) for schema in self.schemas.values()]}
            with open(self.schema_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"스키마 저장 실패: {e}")

    def _save_values(self):
        """값 파일 저장"""
        try:
            data = {"values": [asdict(value) for value in self.values.values()]}
            with open(self.values_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"값 저장 실패: {e}")

    def save_all(self):
        """모든 설정 저장"""
        self._save_schemas()
        self._save_values()
        self.export_to_env()


# 전역 설정 관리자 인스턴스
config_manager = ConfigManager()
