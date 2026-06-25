# ADR-002: MongoDB TTL 문서로 온보딩 대화 상태 관리

* **Status:** Accepted
* **Date:** 2025-11
* **Author:** leebeanbin

## Context & Problem Statement

Discord 온보딩(`/onboard`)은 단일 HTTP 요청이 아닌 **여러 메시지에 걸친 멀티스텝 대화**입니다:

```
/onboard → 커리어 목표 → 이력서 PDF → GitHub ID → 완료
```

각 메시지가 다른 Discord Gateway 이벤트로 도착하므로, 사용자의 현재 단계(상태)를 어딘가에 저장해야 합니다.

## Decision Drivers

* 상태가 메모리에만 있으면 재시작 시 진행 중인 온보딩 모두 손실
* 사용자별 상태 스키마가 단계마다 다름 (CAREER_GOAL 단계엔 resume_id 없음)
* TTL이 지난 미완료 세션은 자동으로 정리되어야 함
* MongoDB는 이미 Notion 캐시용으로 인프라에 포함됨

## Considered Options

1. **Python 메모리 dict** — `{user_id: ConversationSession}` 전역 딕셔너리
2. **Redis** — TTL 내장, 빠른 key-value 저장소
3. **MongoDB TTL 컬렉션** ← 선택

## Decision Outcome

Chosen Option: **Option 3**.

`onboarding_sessions` 컬렉션에 `ConversationSession` 문서를 upsert로 저장합니다. `expires_at` 필드에 MongoDB TTL 인덱스를 적용하여 7일 후 자동 삭제합니다.

**`ConversationSession` 문서 구조:**
```json
{
  "channel_user_id": "123456789",
  "channel_type": "DISCORD",
  "state": "RESUME",
  "career_goal_text": "백엔드 엔지니어",
  "resume_id": null,
  "github_username": null,
  "careeros_user_id": 42,
  "created_at": "2026-06-25T08:00:00Z",
  "updated_at": "2026-06-25T08:01:30Z",
  "expires_at": "2026-07-02T08:01:30Z"
}
```

**복합 키:** `{ channel_user_id, channel_type }` — 동일 사용자가 Discord·Telegram 각각 독립 세션 보유 가능.

**실제 구현 (`state.py`):**
```python
async def save_session(session: ConversationSession) -> None:
    session.updated_at = datetime.utcnow()
    doc = session.to_doc()  # expires_at = updated_at + 7days
    await _col().update_one(
        {"channel_user_id": session.channel_user_id, "channel_type": session.channel_type},
        {"$set": doc},
        upsert=True,
    )
```

**TTL 인덱스:**
```
db.onboarding_sessions.createIndex(
    { "expires_at": 1 },
    { expireAfterSeconds: 0 }
)
```
`expires_at`이 현재 시각보다 이전이면 MongoDB가 자동 삭제. `/restart_onboard`는 `delete_session()` 후 새 세션 생성으로 초기화.

### Consequences

* **Positive:**
  - 재시작 후에도 온보딩 상태 복원 (MongoDB 영속성)
  - TTL 인덱스로 미완료 세션 자동 정리 (애플리케이션 코드 불필요)
  - 유연한 스키마 — 단계마다 필드가 `null`이어도 무방
  - MongoDB는 이미 운영 중 (추가 인프라 없음)
* **Negative/Trade-offs:**
  - 메모리 dict 대비 I/O 왕복 비용 (매 메시지마다 DB 조회)
  - Redis 대비 TTL 정확도 낮음 (MongoDB TTL 체크 주기 60초)
  - `expires_at` 갱신이 `save_session()` 호출 시 자동으로 늦춰짐 → 활성 세션은 자동 연장

---

## Options Comparison Matrix

| Criteria | 메모리 dict | Redis | MongoDB TTL |
|---|---|---|---|
| **재시작 내구성** | ❌ | ✅ | ✅ |
| **자동 만료** | 직접 구현 필요 | ✅ TTL 내장 | ✅ TTL 인덱스 |
| **유연한 스키마** | ✅ | ❌ 직렬화 필요 | ✅ |
| **추가 인프라** | ❌ | ✅ Redis 필요 | ❌ (이미 보유) |
| **TTL 정확도** | — | 1초 이내 | ~60초 오차 |
| **조회 속도** | O(1) 메모리 | O(1) 네트워크 | O(log n) B-tree |
