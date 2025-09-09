# 📖 API 문서

**MeetupLoader의 REST API 엔드포인트를 상세히 안내합니다.**

## 🔗 기본 정보

### Base URL
```
https://meetuploader.fly.dev
# 또는 로컬 개발 환경
http://localhost:8888
```

### 인증
- **웹훅**: `X-Webhook-Secret` 헤더 필요
- **일반 API**: 인증 불필요 (내부 네트워크 사용 권장)

### 응답 형식
모든 API는 JSON 형식으로 응답합니다.

## 📊 헬스체크

### GET /health
서비스 상태를 확인합니다.

**요청:**
```http
GET /health
```

**응답:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-09T13:00:00Z",
  "version": "1.0.0",
  "uptime": 3600,
  "services": {
    "discord": "connected",
    "notion": "connected",
    "mongodb": "connected"
  }
}
```

**상태 코드:**
- `200`: 정상
- `503`: 서비스 불가

## 📈 메트릭

### GET /metrics/dashboard
실시간 시스템 메트릭을 조회합니다.

**요청:**
```http
GET /metrics/dashboard
```

**응답:**
```json
{
  "total_commands": 150,
  "success_rate": 98.5,
  "active_users": 5,
  "pages_synced": 25,
  "uptime": 3600,
  "memory_usage": {
    "used": "512MB",
    "total": "1GB",
    "percentage": 51.2
  },
  "database_stats": {
    "total_pages": 25,
    "last_sync": "2025-09-09T12:57:00Z",
    "sync_errors": 0
  },
  "command_stats": {
    "task": 45,
    "meeting": 30,
    "document": 20,
    "search": 25,
    "stats": 30
  }
}
```

## 🔄 동기화

### GET /sync/status
동기화 서비스 상태를 확인합니다.

**요청:**
```http
GET /sync/status
```

**응답:**
```json
{
  "is_running": true,
  "last_sync": "2025-09-09T12:57:00Z",
  "total_pages": 9,
  "sync_interval": 180,
  "next_sync": "2025-09-09T13:00:00Z",
  "errors": 0,
  "last_error": null
}
```

### POST /sync/manual
수동으로 동기화를 실행합니다.

**요청:**
```http
POST /sync/manual
```

**응답:**
```json
{
  "success": true,
  "message": "동기화가 완료되었습니다.",
  "total_pages": 9,
  "new_pages": 0,
  "updated_pages": 2,
  "deleted_pages": 0,
  "timestamp": "2025-09-09T13:00:00Z",
  "duration": 15.5
}
```

**상태 코드:**
- `200`: 성공
- `500`: 동기화 실패

## 🔗 웹훅

### POST /notion/webhook
Notion에서 페이지 변경사항을 받습니다.

**요청:**
```http
POST /notion/webhook
Content-Type: application/json
X-Webhook-Secret: your_webhook_secret

{
  "page_id": "26832049-c4e2-814f-b672-c672b5540bae",
  "channel_id": 1234567890,
  "mode": "meeting",
  "action": "created",
  "timestamp": "2025-09-09T13:00:00Z"
}
```

**응답:**
```json
{
  "success": true,
  "message": "웹훅이 처리되었습니다.",
  "page_id": "26832049-c4e2-814f-b672-c672b5540bae",
  "thread_id": 9876543210
}
```

**상태 코드:**
- `200`: 성공
- `400`: 잘못된 요청
- `401`: 인증 실패
- `500`: 처리 실패

## 📊 통계 API

### GET /stats/daily
일별 통계를 조회합니다.

**요청:**
```http
GET /stats/daily?date=2025-09-09
```

**파라미터:**
- `date` (선택): 날짜 (YYYY-MM-DD), 기본값: 오늘

**응답:**
```json
{
  "date": "2025-09-09",
  "total_activities": 15,
  "by_type": {
    "task": 8,
    "meeting": 4,
    "document": 3
  },
  "by_user": {
    "홍길동": 6,
    "김영희": 5,
    "정빈": 4
  },
  "hourly_distribution": {
    "09": 2,
    "10": 3,
    "11": 4,
    "12": 3,
    "13": 2,
    "14": 1
  }
}
```

### GET /stats/weekly
주별 통계를 조회합니다.

**요청:**
```http
GET /stats/weekly?week=2025-W37
```

**파라미터:**
- `week` (선택): 주 (YYYY-W##), 기본값: 이번 주

**응답:**
```json
{
  "week": "2025-W37",
  "total_activities": 85,
  "by_day": {
    "Monday": 12,
    "Tuesday": 15,
    "Wednesday": 18,
    "Thursday": 14,
    "Friday": 16,
    "Saturday": 5,
    "Sunday": 5
  },
  "by_type": {
    "task": 45,
    "meeting": 25,
    "document": 15
  }
}
```

### GET /stats/monthly
월별 통계를 조회합니다.

**요청:**
```http
GET /stats/monthly?year=2025&month=9
```

**파라미터:**
- `year` (선택): 연도, 기본값: 올해
- `month` (선택): 월 (1-12), 기본값: 이번 달

**응답:**
```json
{
  "year": 2025,
  "month": 9,
  "total_activities": 350,
  "by_week": {
    "W35": 80,
    "W36": 85,
    "W37": 90,
    "W38": 95
  },
  "by_type": {
    "task": 180,
    "meeting": 100,
    "document": 70
  },
  "by_user": {
    "홍길동": 120,
    "김영희": 110,
    "정빈": 80,
    "소현": 40
  }
}
```

## 🔍 검색 API

### GET /search
페이지를 검색합니다.

**요청:**
```http
GET /search?q=API&type=task&user=홍길동&days=7&limit=10
```

**파라미터:**
- `q` (필수): 검색어
- `type` (선택): 타입 (task, meeting, document)
- `user` (선택): 사용자명
- `days` (선택): 기간 (일), 기본값: 90
- `limit` (선택): 결과 수, 기본값: 20

**응답:**
```json
{
  "query": "API",
  "total_results": 5,
  "results": [
    {
      "page_id": "26832049-c4e2-814f-b672-c672b5540bae",
      "title": "API 설계서",
      "type": "document",
      "user": "홍길동",
      "created_time": "2025-09-09T10:30:00Z",
      "url": "https://notion.so/26832049c4e2814fb672c672b5540bae",
      "snippet": "API 설계에 대한 상세한 문서입니다..."
    }
  ],
  "filters": {
    "type": "task",
    "user": "홍길동",
    "days": 7
  }
}
```

## 📋 Task API

### GET /tasks
Task 목록을 조회합니다.

**요청:**
```http
GET /tasks?user=홍길동&status=in_progress&limit=10
```

**파라미터:**
- `user` (선택): 사용자명
- `status` (선택): 상태 (not_started, in_progress, done)
- `priority` (선택): 우선순위 (high, medium, low)
- `limit` (선택): 결과 수, 기본값: 20

**응답:**
```json
{
  "total_tasks": 25,
  "tasks": [
    {
      "page_id": "26832049-c4e2-814f-b672-c672b5540bae",
      "title": "로그인 기능 개발",
      "user": "홍길동",
      "status": "in_progress",
      "priority": "high",
      "created_time": "2025-09-09T10:30:00Z",
      "due_date": "2025-09-15T23:59:59Z",
      "url": "https://notion.so/26832049c4e2814fb672c672b5540bae"
    }
  ]
}
```

### POST /tasks
새 Task를 생성합니다.

**요청:**
```http
POST /tasks
Content-Type: application/json

{
  "person": "홍길동",
  "name": "새로운 작업",
  "priority": "high",
  "deadline": "2025-09-15"
}
```

**응답:**
```json
{
  "success": true,
  "page_id": "26832049-c4e2-814f-b672-c672b5540bae",
  "title": "새로운 작업",
  "url": "https://notion.so/26832049c4e2814fb672c672b5540bae",
  "thread_id": 9876543210
}
```

## 📅 Meeting API

### GET /meetings
회의록 목록을 조회합니다.

**요청:**
```http
GET /meetings?participant=홍길동&days=7&limit=10
```

**파라미터:**
- `participant` (선택): 참석자명
- `days` (선택): 기간 (일), 기본값: 30
- `limit` (선택): 결과 수, 기본값: 20

**응답:**
```json
{
  "total_meetings": 15,
  "meetings": [
    {
      "page_id": "26832049-c4e2-814f-b672-c672b5540bae",
      "title": "주간 스프린트 회의",
      "participants": ["홍길동", "김영희"],
      "created_time": "2025-09-09T10:30:00Z",
      "url": "https://notion.so/26832049c4e2814fb672c672b5540bae"
    }
  ]
}
```

### POST /meetings
새 회의록을 생성합니다.

**요청:**
```http
POST /meetings
Content-Type: application/json

{
  "title": "새로운 회의",
  "participants": ["홍길동", "김영희", "정빈"]
}
```

**응답:**
```json
{
  "success": true,
  "page_id": "26832049-c4e2-814f-b672-c672b5540bae",
  "title": "새로운 회의",
  "url": "https://notion.so/26832049c4e2814fb672c672b5540bae",
  "thread_id": 9876543210
}
```

## 📄 Document API

### GET /documents
문서 목록을 조회합니다.

**요청:**
```http
GET /documents?type=개발문서&days=30&limit=10
```

**파라미터:**
- `type` (선택): 문서 유형 (개발문서, 기획안, 회의록, 개발규칙)
- `days` (선택): 기간 (일), 기본값: 90
- `limit` (선택): 결과 수, 기본값: 20

**응답:**
```json
{
  "total_documents": 20,
  "documents": [
    {
      "page_id": "26832049-c4e2-814f-b672-c672b5540bae",
      "title": "API 설계서",
      "type": "개발문서",
      "created_time": "2025-09-09T10:30:00Z",
      "url": "https://notion.so/26832049c4e2814fb672c672b5540bae"
    }
  ]
}
```

### POST /documents
새 문서를 생성합니다.

**요청:**
```http
POST /documents
Content-Type: application/json

{
  "title": "새로운 문서",
  "doc_type": "개발문서"
}
```

**응답:**
```json
{
  "success": true,
  "page_id": "26832049-c4e2-814f-b672-c672b5540bae",
  "title": "새로운 문서",
  "url": "https://notion.so/26832049c4e2814fb672c672b5540bae",
  "thread_id": 9876543210
}
```

## 🚨 에러 응답

### 에러 형식
```json
{
  "error": "ERROR_CODE",
  "message": "에러 메시지",
  "details": "상세 정보",
  "timestamp": "2025-09-09T13:00:00Z"
}
```

### 에러 코드

| 코드 | 상태 | 설명 |
|------|------|------|
| `INVALID_REQUEST` | 400 | 잘못된 요청 |
| `UNAUTHORIZED` | 401 | 인증 실패 |
| `FORBIDDEN` | 403 | 권한 없음 |
| `NOT_FOUND` | 404 | 리소스 없음 |
| `CONFLICT` | 409 | 충돌 |
| `RATE_LIMITED` | 429 | 요청 제한 초과 |
| `INTERNAL_ERROR` | 500 | 내부 서버 오류 |
| `SERVICE_UNAVAILABLE` | 503 | 서비스 불가 |

### 예시 에러 응답

#### 400 Bad Request
```json
{
  "error": "INVALID_REQUEST",
  "message": "필수 파라미터가 누락되었습니다.",
  "details": "person 파라미터가 필요합니다.",
  "timestamp": "2025-09-09T13:00:00Z"
}
```

#### 500 Internal Server Error
```json
{
  "error": "INTERNAL_ERROR",
  "message": "서버 내부 오류가 발생했습니다.",
  "details": "Notion API 연결 실패",
  "timestamp": "2025-09-09T13:00:00Z"
}
```

## 🔧 개발 도구

### API 테스트

#### cURL 예시
```bash
# 헬스체크
curl -X GET https://meetuploader.fly.dev/health

# 통계 조회
curl -X GET "https://meetuploader.fly.dev/stats/daily?date=2025-09-09"

# Task 생성
curl -X POST https://meetuploader.fly.dev/tasks \
  -H "Content-Type: application/json" \
  -d '{"person": "홍길동", "name": "새 작업", "priority": "high"}'
```

#### Postman 컬렉션
```json
{
  "info": {
    "name": "MeetupLoader API",
    "description": "MeetupLoader REST API 컬렉션"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/health"
      }
    }
  ]
}
```

### API 클라이언트

#### Python 예시
```python
import requests

# 헬스체크
response = requests.get("https://meetuploader.fly.dev/health")
print(response.json())

# Task 생성
data = {
    "person": "홍길동",
    "name": "새 작업",
    "priority": "high"
}
response = requests.post("https://meetuploader.fly.dev/tasks", json=data)
print(response.json())
```

#### JavaScript 예시
```javascript
// 헬스체크
fetch('https://meetuploader.fly.dev/health')
  .then(response => response.json())
  .then(data => console.log(data));

// Task 생성
fetch('https://meetuploader.fly.dev/tasks', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    person: '홍길동',
    name: '새 작업',
    priority: 'high'
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

---

**더 자세한 정보는 [README.md](README.md)를 참조하세요!**
