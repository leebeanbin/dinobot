# Decision Log

dinobot의 설계·운영 의사결정을 추적하는 로그.

ADR(Architecture Decision Records)과의 차이:
- **ADR** (`docs/adr/`) — 아키텍처 수준의 기술적 결정. 비가역적이거나 장기적인 영향을 미치는 결정.
- **Decision Log** (`docs/decision-log/`) — 운영, 전략, 설계 옵션 선택 등 보다 폭넓은 의사결정.

---

## 인덱스

| ID | 날짜 | 제목 | 파일 |
|----|------|------|------|
| DL-001 | 2025-11 | asyncio 단일 프로세스 패턴 선택 | [DL-001-asyncio-single-process.md](DL-001-asyncio-single-process.md) |
| DL-002 | 2025-11 | 온보딩 세션 MongoDB TTL 관리 (Redis 대신) | [DL-002-mongodb-ttl-session.md](DL-002-mongodb-ttl-session.md) |

---

## 새 항목 작성 방법

1. `DL-NNN-<slug>.md` 파일을 이 디렉토리에 생성한다.
2. 형식: 배경(Context) → 고려한 옵션(Options) → 결정(Decision) → 트레이드오프(Tradeoffs).
3. 이 README의 인덱스 테이블에 항목을 추가한다.
