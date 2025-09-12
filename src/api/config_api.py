"""
DinoBot 설정 관리 API
- 웹 기반 설정 관리 인터페이스
- 설정 추가/수정/삭제 기능
- 설정 검증 및 미리보기
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime

# from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from src.core.config_manager import config_manager, ConfigSchema, ConfigType

logger = logging.getLogger(__name__)

# 라우터 설정
router = APIRouter(prefix="/config", tags=["Configuration Management"])

# 템플릿 설정
# templates = Jinja2Templates(directory="templates")


# Pydantic 모델들
class ConfigValueRequest(BaseModel):
    key: str = Field(..., description="설정 키")
    value: Any = Field(..., description="설정 값")
    source: str = Field(default="user_input", description="설정 소스")


class ConfigSchemaRequest(BaseModel):
    key: str = Field(..., description="설정 키")
    name: str = Field(..., description="설정 이름")
    description: str = Field(..., description="설정 설명")
    type: str = Field(..., description="설정 타입")
    required: bool = Field(default=False, description="필수 여부")
    default_value: Any = Field(default=None, description="기본값")
    category: str = Field(default="general", description="카테고리")
    sensitive: bool = Field(default=False, description="민감한 정보 여부")


class ConfigValidationResponse(BaseModel):
    valid: bool
    message: str
    converted_value: Any = None


# API 엔드포인트들
@router.get("/", response_class=HTMLResponse)
async def config_management_page(request: Request):
    """설정 관리 웹 페이지"""
    try:
        # 모든 설정 정보 가져오기
        all_configs = await config_manager.get_all_configs()
        missing_configs = config_manager.get_missing_required_configs()

        # 카테고리별 설정
        categories = {}
        for key, schema in config_manager.schemas.items():
            if schema.category not in categories:
                categories[schema.category] = []
            categories[schema.category].append(
                {
                    "key": key,
                    "name": schema.name,
                    "description": schema.description,
                    "type": schema.type.value,
                    "required": schema.required,
                    "value": all_configs.get(key),
                    "sensitive": schema.sensitive,
                }
            )

        # 수정된 스타일 HTML 템플릿 사용
        with open("templates/dinobot_setup_fixed.html", "r", encoding="utf-8") as f:
            html_content = f.read()

        # 설정 상태 확인
        discord_configured = bool(all_configs.get('DISCORD_TOKEN') and all_configs.get('DISCORD_APP_ID'))
        notion_configured = bool(all_configs.get('NOTION_TOKEN'))
        webhook_configured = bool(all_configs.get('WEBHOOK_SECRET'))
        
        # 주요 설정 카테고리별 완료 상태 확인
        required_categories = [
            discord_configured,  # Discord 연동
            notion_configured,   # Notion 연동  
            webhook_configured   # 보안 설정
        ]
        
        # 진행률 계산 (완료된 카테고리 / 전체 카테고리)
        configured_count = sum(required_categories)
        total_count = len(required_categories)
        progress_percentage = int((configured_count / total_count * 100) if total_count > 0 else 0)
        
        html_content = html_content.replace(
            "{{ configured_configs }}", str(configured_count)
        ).replace(
            "{{ total_configs }}", str(total_count)
        ).replace(
            "{{ config.discord_token }}", str(all_configs.get('DISCORD_TOKEN', ''))
        ).replace(
            "{{ config.discord_app_id }}", str(all_configs.get('DISCORD_APP_ID', ''))
        ).replace(
            "{{ config.discord_guild_id }}", str(all_configs.get('DISCORD_GUILD_ID', ''))
        ).replace(
            "{{ config.notion_token }}", str(all_configs.get('NOTION_TOKEN', ''))
        ).replace(
            "{{ config.factory_tracker_db_id }}", str(all_configs.get('FACTORY_TRACKER_DB_ID', ''))
        ).replace(
            "{{ config.board_db_id }}", str(all_configs.get('BOARD_DB_ID', ''))
        ).replace(
            "{{ config.webhook_secret }}", str(all_configs.get('WEBHOOK_SECRET', ''))
        ).replace(
            "{{ config.discord_token or '' }}", str(all_configs.get('DISCORD_TOKEN', ''))
        ).replace(
            "{{ config.discord_app_id or '' }}", str(all_configs.get('DISCORD_APP_ID', ''))
        ).replace(
            "{{ config.discord_guild_id or '' }}", str(all_configs.get('DISCORD_GUILD_ID', ''))
        ).replace(
            "{{ config.notion_token or '' }}", str(all_configs.get('NOTION_TOKEN', ''))
        ).replace(
            "{{ config.webhook_secret or '' }}", str(all_configs.get('WEBHOOK_SECRET', ''))
        )
        
        # 복잡한 진행률 템플릿 문법 처리
        html_content = html_content.replace(
            '{{ "%.0f"|format((configured_configs / total_configs * 100) if total_configs > 0 else 0) }}',
            str(progress_percentage)
        ).replace(
            'data-progress="{{ "%.0f"|format((configured_configs / total_configs * 100) if total_configs > 0 else 0) }}"',
            f'data-progress="{progress_percentage}"'
        )
        
        # Discord 상태 조건문 처리
        html_content = html_content.replace(
            "{% if config.discord_token and config.discord_app_id %}completed{% else %}required{% endif %}",
            "completed" if discord_configured else "required"
        ).replace(
            "{% if config.discord_token and config.discord_app_id %}완료{% else %}필수{% endif %}",
            "완료" if discord_configured else "필수"
        ).replace(
            "{% if config.discord_token and config.discord_app_id %}✓{% else %}○{% endif %}",
            "✓" if discord_configured else "○"
        ).replace(
            "{% if not (config.discord_token and config.discord_app_id) %}pending{% endif %}",
            "pending" if not discord_configured else ""
        )
        
        # Notion 상태 조건문 처리
        html_content = html_content.replace(
            "{% if config.notion_token %}completed{% else %}required{% endif %}",
            "completed" if notion_configured else "required"
        ).replace(
            "{% if config.notion_token %}완료{% else %}필수{% endif %}",
            "완료" if notion_configured else "필수"
        ).replace(
            "{% if config.notion_token %}✓{% else %}○{% endif %}",
            "✓" if notion_configured else "○"
        ).replace(
            "{% if not config.notion_token %}pending{% endif %}",
            "pending" if not notion_configured else ""
        )
        
        # Webhook 상태 조건문 처리
        html_content = html_content.replace(
            "{% if config.webhook_secret %}completed{% else %}required{% endif %}",
            "completed" if webhook_configured else "required"
        ).replace(
            "{% if config.webhook_secret %}완료{% else %}필수{% endif %}",
            "완료" if webhook_configured else "필수"
        ).replace(
            "{% if config.webhook_secret %}✓{% else %}○{% endif %}",
            "✓" if webhook_configured else "○"
        ).replace(
            "{% if not config.webhook_secret %}pending{% endif %}",
            "pending" if not webhook_configured else ""
        )

        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"설정 관리 페이지 로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/all")
async def get_all_configs():
    """모든 설정 조회"""
    try:
        return {
            "configs": await config_manager.get_all_configs(),
            "schemas": {
                k: {
                    "name": v.name,
                    "description": v.description,
                    "type": v.type.value,
                    "required": v.required,
                    "category": v.category,
                    "sensitive": v.sensitive,
                }
                for k, v in config_manager.schemas.items()
            },
            "missing_required": config_manager.get_missing_required_configs(),
        }
    except Exception as e:
        logger.error(f"설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/category/{category}")
async def get_configs_by_category(category: str):
    """카테고리별 설정 조회"""
    try:
        configs = config_manager.get_configs_by_category(category)
        return {"category": category, "configs": configs}
    except Exception as e:
        logger.error(f"카테고리별 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/set")
async def set_config(request: ConfigValueRequest):
    """설정 값 설정"""
    try:
        success = await config_manager.set(request.key, request.value, request.source)
        if success:
            return {"message": f"설정 '{request.key}' 업데이트 완료", "success": True}
        else:
            raise HTTPException(
                status_code=400, detail=f"설정 '{request.key}' 업데이트 실패"
            )
    except Exception as e:
        logger.error(f"설정 설정 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/validate")
async def validate_config(request: ConfigValueRequest):
    """설정 값 검증"""
    try:
        if request.key not in config_manager.schemas:
            return ConfigValidationResponse(
                valid=False, message=f"알 수 없는 설정 키: {request.key}"
            )

        schema = config_manager.schemas[request.key]
        valid = config_manager._validate_value(request.value, schema)

        if valid:
            converted_value = config_manager._convert_value(
                str(request.value), schema.type
            )
            return ConfigValidationResponse(
                valid=True,
                message="설정 값이 유효합니다",
                converted_value=converted_value,
            )
        else:
            return ConfigValidationResponse(
                valid=False, message="설정 값이 유효하지 않습니다"
            )
    except Exception as e:
        logger.error(f"설정 검증 실패: {e}")
        return ConfigValidationResponse(
            valid=False, message=f"검증 중 오류 발생: {str(e)}"
        )


@router.post("/api/schema")
async def add_config_schema(request: ConfigSchemaRequest):
    """새로운 설정 스키마 추가"""
    try:
        # ConfigType 변환
        try:
            config_type = ConfigType(request.type)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"유효하지 않은 설정 타입: {request.type}"
            )

        schema = ConfigSchema(
            key=request.key,
            name=request.name,
            description=request.description,
            type=config_type,
            required=request.required,
            default_value=request.default_value,
            category=request.category,
            sensitive=request.sensitive,
        )

        success = config_manager.add_schema(schema)
        if success:
            return {
                "message": f"설정 스키마 '{request.key}' 추가 완료",
                "success": True,
            }
        else:
            raise HTTPException(
                status_code=400, detail=f"설정 스키마 '{request.key}' 추가 실패"
            )
    except Exception as e:
        logger.error(f"설정 스키마 추가 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/schema/{key}")
async def remove_config_schema(key: str):
    """설정 스키마 제거"""
    try:
        success = config_manager.remove_schema(key)
        if success:
            return {"message": f"설정 스키마 '{key}' 제거 완료", "success": True}
        else:
            raise HTTPException(
                status_code=400, detail=f"설정 스키마 '{key}' 제거 실패"
            )
    except Exception as e:
        logger.error(f"설정 스키마 제거 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/export")
async def export_configs():
    """설정을 .env 파일로 내보내기"""
    try:
        success = config_manager.export_to_env()
        if success:
            return {"message": "설정을 .env 파일로 내보내기 완료", "success": True}
        else:
            raise HTTPException(status_code=500, detail="설정 내보내기 실패")
    except Exception as e:
        logger.error(f"설정 내보내기 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/save")
async def save_all_configs(request: Request):
    """모든 설정 저장 (동적 데이터베이스 포함)"""
    try:
        data = await request.json()
        
        # 기본 설정 저장
        configs_to_save = [
            ('DISCORD_TOKEN', data.get('discord_token')),
            ('DISCORD_APP_ID', data.get('discord_app_id')),
            ('DISCORD_GUILD_ID', data.get('discord_guild_id')),
            ('NOTION_TOKEN', data.get('notion_token')),
            ('WEBHOOK_SECRET', data.get('webhook_secret')),
        ]
        
        saved_count = 0
        for key, value in configs_to_save:
            if value:  # 값이 있을 때만 저장
                success = await config_manager.set(key, value, "user_input")
                if success:
                    saved_count += 1
        
        # 동적 데이터베이스 저장
        databases = data.get('databases', [])
        if databases:
            # 기존 데이터베이스 모두 삭제
            db = config_manager.db
            databases_collection = db["databases"]
            await databases_collection.delete_many({})
            
            # 새 데이터베이스들 저장
            for database in databases:
                if database.get('name') and database.get('id'):
                    database_doc = {
                        "name": database['name'],
                        "id": database['id'],
                        "description": database.get('description', ''),
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    }
                    await databases_collection.insert_one(database_doc)
            
            logger.info(f"✅ {len(databases)}개 데이터베이스 저장 완료")
        
        config_manager.save_all()
        total_saved = saved_count + len(databases)
        return {
            "message": f"{total_saved}개 항목이 성공적으로 저장되었습니다",
            "success": True,
            "saved_count": total_saved,
            "databases_count": len(databases)
        }
    except Exception as e:
        logger.error(f"설정 저장 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/status")
async def get_config_status():
    """설정 상태 조회"""
    try:
        all_configs = await config_manager.get_all_configs()
        missing_configs = config_manager.get_missing_required_configs()

        return {
            "total_schemas": len(config_manager.schemas),
            "configured_configs": len(
                [k for k, v in all_configs.items() if v is not None]
            ),
            "missing_required": len(missing_configs),
            "missing_configs": missing_configs,
            "categories": list(
                set(schema.category for schema in config_manager.schemas.values())
            ),
            "ready": len(missing_configs) == 0,
        }
    except Exception as e:
        logger.error(f"설정 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/databases")
async def get_databases():
    """데이터베이스 목록 조회"""
    try:
        # MongoDB에서 데이터베이스 목록 조회
        db = config_manager.db
        databases_collection = db["databases"]
        
        # 비동기 cursor를 list로 변환
        databases = []
        async for doc in databases_collection.find({}, {"_id": 0}):
            databases.append(doc)

        return {"success": True, "databases": databases}
    except Exception as e:
        logger.error(f"데이터베이스 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/databases")
async def add_database(request: Request):
    """데이터베이스 추가"""
    try:
        data = await request.json()
        name = data.get("name")
        db_id = data.get("id")
        description = data.get("description", "")

        if not name or not db_id:
            raise HTTPException(
                status_code=400, detail="데이터베이스 이름과 ID는 필수입니다."
            )

        # MongoDB에 데이터베이스 저장
        db = config_manager.db
        databases_collection = db["databases"]

        database_doc = {
            "name": name,
            "id": db_id,
            "description": description,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        result = databases_collection.insert_one(database_doc)

        if result.inserted_id:
            logger.info(f"✅ 데이터베이스 추가 완료: {name}")
            return {
                "success": True,
                "message": f"데이터베이스 '{name}'이 성공적으로 추가되었습니다.",
            }
        else:
            raise HTTPException(
                status_code=500, detail="데이터베이스 추가에 실패했습니다."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"데이터베이스 추가 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/databases")
async def delete_database(request: Request):
    """데이터베이스 삭제"""
    try:
        data = await request.json()
        index = data.get("index")

        if index is None:
            raise HTTPException(
                status_code=400, detail="삭제할 데이터베이스 인덱스가 필요합니다."
            )

        # MongoDB에서 데이터베이스 삭제
        db = config_manager.db
        databases_collection = db["databases"]

        databases = list(databases_collection.find({}, {"_id": 1}))
        if index >= len(databases):
            raise HTTPException(
                status_code=400, detail="유효하지 않은 데이터베이스 인덱스입니다."
            )

        database_id = databases[index]["_id"]
        result = databases_collection.delete_one({"_id": database_id})

        if result.deleted_count > 0:
            logger.info(f"✅ 데이터베이스 삭제 완료: 인덱스 {index}")
            return {
                "success": True,
                "message": "데이터베이스가 성공적으로 삭제되었습니다.",
            }
        else:
            raise HTTPException(
                status_code=500, detail="데이터베이스 삭제에 실패했습니다."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"데이터베이스 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/test-notion")
async def test_notion_connection(request: Request):
    """Notion 연결 테스트"""
    try:
        data = await request.json()
        token = data.get('token')
        
        if not token:
            raise HTTPException(status_code=400, detail="토큰이 필요합니다")
        
        # 간단한 Notion API 호출로 연결 테스트
        import httpx
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version': '2025-09-03',
            'Content-Type': 'application/json'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://api.notion.com/v1/users/me',
                headers=headers,
                timeout=10.0
            )
            
        if response.status_code == 200:
            user_data = response.json()
            return {
                "success": True,
                "message": "Notion 연결 성공!",
                "user_name": user_data.get('name', 'Unknown'),
                "workspace": user_data.get('type', 'person')
            }
        else:
            return {
                "success": False,
                "message": f"Notion 연결 실패: {response.status_code}",
                "error": response.text
            }
            
    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "연결 시간 초과",
            "error": "Notion API 연결 시간이 초과되었습니다"
        }
    except Exception as e:
        logger.error(f"Notion 연결 테스트 실패: {e}")
        return {
            "success": False,
            "message": "연결 테스트 중 오류 발생",
            "error": str(e)
        }


@router.post("/api/generate-webhook-secret")
async def generate_webhook_secret():
    """안전한 웹훅 시크릿 생성"""
    try:
        import secrets
        import string
        
        # 32자 길이의 안전한 랜덤 문자열 생성
        alphabet = string.ascii_letters + string.digits + '-_'
        secret = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        return {
            "success": True,
            "secret": secret,
            "message": "안전한 웹훅 시크릿이 생성되었습니다"
        }
    except Exception as e:
        logger.error(f"웹훅 시크릿 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/test-database")
async def test_database_connection(request: Request):
    """Notion 데이터베이스 연결 테스트"""
    try:
        data = await request.json()
        token = data.get('token')
        database_id = data.get('database_id')
        
        if not token:
            raise HTTPException(status_code=400, detail="토큰이 필요합니다")
        
        if not database_id:
            raise HTTPException(status_code=400, detail="데이터베이스 ID가 필요합니다")
        
        # Notion API로 데이터베이스 정보 조회
        import httpx
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version': '2025-09-03',
            'Content-Type': 'application/json'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'https://api.notion.com/v1/databases/{database_id}',
                headers=headers,
                timeout=10.0
            )
            
        if response.status_code == 200:
            db_data = response.json()
            return {
                "success": True,
                "message": "데이터베이스 연결 성공!",
                "database_name": db_data.get('title', [{}])[0].get('plain_text', 'Untitled'),
                "properties_count": len(db_data.get('properties', {}))
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "message": "데이터베이스를 찾을 수 없습니다. ID를 확인해주세요.",
                "error": "Database not found"
            }
        elif response.status_code == 403:
            return {
                "success": False,
                "message": "데이터베이스 접근 권한이 없습니다. Notion 통합에 데이터베이스 권한을 추가해주세요.",
                "error": "Access denied"
            }
        else:
            return {
                "success": False,
                "message": f"Notion API 오류: {response.status_code}",
                "error": response.text
            }
            
    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "연결 시간 초과",
            "error": "Notion API 연결 시간이 초과되었습니다"
        }
    except Exception as e:
        logger.error(f"데이터베이스 연결 테스트 실패: {e}")
        return {
            "success": False,
            "message": "연결 테스트 중 오류 발생",
            "error": str(e)
        }
