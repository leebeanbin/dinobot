# Notion Integration

dinobot은 `NotionService` (`src/service/notion/notion_service.py`)를 통해 Notion API와 통신하고, MongoDB를 캐시 레이어로 사용한다.

---

## NotionService 역할

- Notion Database에서 페이지를 읽고 Discord 스레드에 전달한다.
- Discord 슬래시 커맨드로 task/meeting/document 페이지를 생성한다.
- 페이지 내용을 텍스트로 추출하여 검색 인덱스를 구성한다.
- 페이지 존재 여부를 확인하여 삭제된 항목을 감지한다.

---

## 지원 DB 타입

| 타입 | Notion DB | 슬래시 커맨드 | 설명 |
|------|-----------|---------------|------|
| `task` | Factory Tracker DB | `/task` | 할 일/업무 트래킹 |
| `meeting` | Board DB | `/meeting` | 회의록 생성 |
| `document` | (설정 가능) | `/document` | 문서/노트 저장 |

DB ID는 환경변수 `FACTORY_TRACKER_DB_ID`, `BOARD_DB_ID`로 설정한다.

---

## SyncService 동기화 패턴

`src/service/sync/sync_service.py`의 `SyncService`는 asyncio 백그라운드 루프로 동작한다.

**동기화 주기:** 기본 600초 (10분). `synchronization_interval_seconds` 설정으로 변경 가능.

**동기화 알고리즘:**
1. MongoDB `notion_pages` 컬렉션에서 모든 페이지 로드
2. 페이지가 없으면 Notion DB에서 초기 임포트 실행
3. 각 페이지에 대해:
   - 최근 2시간 내 동기화된 페이지 → 존재 여부만 확인 (빠른 패스)
   - 이전 페이지 → `extract_page_text()` 호출하여 내용 비교
   - 내용 변경 시 MongoDB 업데이트
   - 404 응답 → 삭제된 페이지로 간주하여 MongoDB에서 제거 + Discord 알림
4. 동시 처리: `asyncio.Semaphore(5)` 기반 배치 병렬 처리
5. 1시간마다 잘못된 페이지 ID 정리 (`clean_invalid_database_entries`)

---

## MongoDB 캐시 구조

컬렉션: `notion_pages`

| 필드 | 설명 |
|------|------|
| `page_id` | Notion 페이지 UUID (인덱스 키) |
| `database_id` | 소속 Notion DB ID |
| `title` | 페이지 제목 |
| `content` | 추출된 텍스트 내용 |
| `content_length` | 내용 바이트 수 |
| `page_type` | `task` / `meeting` / `document` |
| `database_type` | `factory_tracker` / `board` |
| `created_time` | Notion 원본 생성 시각 |
| `last_edited_time` | Notion 원본 수정 시각 |
| `created_by` | Notion 작성자 ID |
| `thread_id` | 연결된 Discord 스레드 ID |
| `last_synced` | Unix timestamp (동기화 완료 시각) |
| `search_text` | `title + content` (전문 검색용) |

---

## 수동 동기화

```bash
# 동기화 상태 확인
GET /sync/status

# 즉시 동기화 실행
POST /sync/manual
```

응답 예시 (`/sync/status`):
```json
{
  "is_running": true,
  "total_pages": 42,
  "recent_sync": 38,
  "type_distribution": { "task": 30, "meeting": 12 },
  "sync_interval": 600,
  "last_check": "2026-06-26T08:00:00"
}
```
