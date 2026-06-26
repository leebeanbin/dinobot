# DL-002: 온보딩 세션 MongoDB TTL 관리 (Redis 대신)

- **날짜:** 2025-11
- **상태:** 결정됨
- **관련 ADR:** [ADR-002](../adr/ADR-002-mongodb-conversation-state.md)

---

## 배경

Discord 온보딩은 `/onboard → 목표 입력 → PDF 업로드 → GitHub ID`의 멀티스텝 대화다. 각 Discord Gateway 이벤트 사이에 사용자의 현재 단계를 어딘가에 저장해야 한다.

인메모리 dict는 프로세스 재시작 시 진행 중인 온보딩을 모두 잃는다.

---

## 고려한 옵션

| 옵션 | 설명 | 장점 | 단점 |
|------|------|------|------|
| **A. 메모리 dict** | `{user_id: ConversationSession}` | 구현 단순, O(1) 조회 | 재시작 내구성 없음, TTL 직접 구현 필요 |
| **B. Redis** | TTL 내장 key-value | 빠른 TTL(1초 이내), 조회 O(1) | 추가 인프라 필요 (Redis 서버) |
| **C. MongoDB TTL** | `expires_at` 필드 + TTL 인덱스 | 재시작 내구성, 자동 만료, 추가 인프라 불필요 | 조회 O(log n), TTL 오차 ~60초 |

---

## 결정

**옵션 C: MongoDB TTL 컬렉션**을 선택한다.

MongoDB는 Notion 페이지 캐시(`notion_pages`)를 위해 이미 운영 중이다. Redis를 추가하는 것보다 동일 인프라를 재사용하는 것이 합리적이다.

**구현:**
```python
# state.py
async def save_session(session: ConversationSession) -> None:
    session.updated_at = datetime.utcnow()
    doc = session.to_doc()  # expires_at = updated_at + 7d
    await _col().update_one(
        {"channel_user_id": session.channel_user_id,
         "channel_type": session.channel_type},
        {"$set": doc},
        upsert=True,
    )
```

**TTL 인덱스:**
```js
db.onboarding_sessions.createIndex(
    { "expires_at": 1 },
    { expireAfterSeconds: 0 }
)
```

---

## 트레이드오프

**긍정적 결과:**
- 프로세스 재시작 후에도 온보딩 상태 복원 가능.
- TTL 인덱스가 7일 경과한 미완료 세션을 자동 정리 — 애플리케이션 코드 불필요.
- 유연한 문서 스키마 — 단계마다 일부 필드가 `null`이어도 무방.
- 추가 인프라(Redis) 없이 운영 가능 → Fly.io 비용 절감.
- `save_session()` 호출 시 `expires_at`이 자동 갱신되어 활성 세션은 연장됨.

**부정적 트레이드오프:**
- 매 메시지마다 MongoDB I/O 왕복 발생 (인메모리 dict 대비).
- TTL 만료 정확도 약 60초 (MongoDB TTL 체크 주기) — 온보딩에는 허용 가능한 수준.
- 조회가 B-tree 인덱스 기반으로 Redis O(1)보다 느림 (하지만 온보딩 트래픽에서는 무시 가능).

---

## 향후 고려사항

온보딩 사용자 수가 수천 명 수준으로 증가하거나, TTL 정확도 < 1초가 필요해지면 Redis 도입을 재고할 수 있다. 현재 MVP 트래픽에서는 MongoDB TTL이 충분하다.
