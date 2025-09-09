// MongoDB 초기화 스크립트
db = db.getSiblingDB('meetuploader');

// 컬렉션 생성 및 인덱스 설정
db.createCollection('notion_pages');
db.createCollection('discord_threads');
db.createCollection('system_events');

// 인덱스 생성
db.notion_pages.createIndex({ "page_id": 1 }, { unique: true });
db.notion_pages.createIndex({ "title": "text", "content": "text" });
db.notion_pages.createIndex({ "created_time": 1 });
db.notion_pages.createIndex({ "database_type": 1 });

db.discord_threads.createIndex({ "thread_id": 1 }, { unique: true });
db.discord_threads.createIndex({ "page_id": 1 });
db.discord_threads.createIndex({ "created_time": 1 });

db.system_events.createIndex({ "timestamp": 1 });
db.system_events.createIndex({ "event_type": 1 });

print('MongoDB 초기화 완료');
