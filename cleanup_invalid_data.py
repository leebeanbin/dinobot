#!/usr/bin/env python3
"""
데이터베이스 정리 스크립트
잘못된 페이지 ID를 가진 항목들을 정리합니다.
"""

import asyncio
from core.database import mongodb_connection, get_meetup_collection
from core.logger import get_logger

logger = get_logger("cleanup")

async def cleanup_invalid_entries():
    """잘못된 데이터베이스 항목 정리"""
    try:
        # MongoDB 연결
        await mongodb_connection.connect_database()
        logger.info("📊 MongoDB 연결 완료")
        
        collection = get_meetup_collection("notion_pages")
        
        # 현재 데이터 확인
        all_entries = await collection.find({}).to_list(None)
        logger.info(f"📋 총 데이터베이스 항목: {len(all_entries)}개")
        
        # 각 항목의 페이지 ID 상태 확인
        valid_entries = []
        invalid_entries = []
        
        for entry in all_entries:
            page_id = entry.get("page_id")
            title = entry.get("title", "제목 없음")
            
            if not page_id or not str(page_id).strip():
                invalid_entries.append({
                    "title": title,
                    "page_id": page_id,
                    "_id": entry.get("_id")
                })
            else:
                valid_entries.append(entry)
        
        logger.info(f"✅ 유효한 항목: {len(valid_entries)}개")
        logger.info(f"❌ 잘못된 항목: {len(invalid_entries)}개")
        
        if invalid_entries:
            logger.info("🔍 잘못된 항목들:")
            for entry in invalid_entries:
                logger.info(f"  - {entry['title']} (page_id: '{entry['page_id']}')")
            
            # 잘못된 항목들 삭제 (자동)
            result = await collection.delete_many({
                "$or": [
                    {"page_id": {"$exists": False}},
                    {"page_id": ""},
                    {"page_id": None},
                    {"page_id": {"$regex": "^\\s*$"}}
                ]
            })
            
            logger.info(f"🧹 {result.deleted_count}개 항목 자동 삭제 완료")
        else:
            logger.info("✅ 모든 항목이 유효합니다!")
    
    except Exception as e:
        logger.error(f"❌ 정리 중 오류 발생: {e}")
    
    finally:
        if mongodb_connection.mongo_client:
            mongodb_connection.mongo_client.close()
            logger.info("📊 MongoDB 연결 종료")

if __name__ == "__main__":
    print("🧹 데이터베이스 정리 스크립트 시작")
    asyncio.run(cleanup_invalid_entries())
    print("✅ 정리 완료")