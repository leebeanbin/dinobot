"""
DB 스키마 확인 스크립트
- Notion API를 통해 실제 DB 스키마 조회
- 정확한 프로퍼티명과 타입 확인
"""

import asyncio
from services.notion import NotionService
from core.config import settings

async def check_database_schemas():
    """데이터베이스 스키마 확인"""
    notion_service = NotionService()
    
    print("=" * 60)
    print("📊 NOTION DATABASE SCHEMA CHECK")
    print("=" * 60)
    
    # Factory Tracker DB 스키마 확인
    print("\n🏭 FACTORY TRACKER DB SCHEMA")
    print("-" * 40)
    try:
        factory_schema = await notion_service.get_database_schema(settings.factory_tracker_db_id)
        print(f"Title Property: {factory_schema['title_prop']}")
        print("\nProperties:")
        for prop_name, prop_info in factory_schema['props'].items():
            prop_type = prop_info.get('type', 'unknown')
            print(f"  - {prop_name}: {prop_type}")
            if prop_type in ['select', 'multi_select', 'status']:
                options = prop_info.get(prop_type, {}).get('options', [])
                if options:
                    option_names = [opt.get('name', '') for opt in options]
                    print(f"    Options: {', '.join(option_names)}")
    except Exception as e:
        print(f"❌ Factory Tracker DB 스키마 조회 실패: {e}")
    
    # Board DB 스키마 확인
    print("\n📋 BOARD DB SCHEMA")
    print("-" * 40)
    try:
        board_schema = await notion_service.get_database_schema(settings.board_db_id)
        print(f"Title Property: {board_schema['title_prop']}")
        print("\nProperties:")
        for prop_name, prop_info in board_schema['props'].items():
            prop_type = prop_info.get('type', 'unknown')
            print(f"  - {prop_name}: {prop_type}")
            if prop_type in ['select', 'multi_select', 'status']:
                options = prop_info.get(prop_type, {}).get('options', [])
                if options:
                    option_names = [opt.get('name', '') for opt in options]
                    print(f"    Options: {', '.join(option_names)}")
    except Exception as e:
        print(f"❌ Board DB 스키마 조회 실패: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 스키마 확인 완료")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(check_database_schemas())
