# ADR-001: FastAPI + Discord.py 단일 프로세스 동시 실행

* **Status:** Accepted
* **Date:** 2025-11
* **Author:** leebeanbin

## Context & Problem Statement

dinobot은 두 가지 진입점이 필요합니다:

1. **Discord.py 봇** — 사용자 슬래시 커맨드 처리 (`/onboard`, `/task`, `/career` 등)
2. **FastAPI HTTP 서버** — CareerOS에서 전송하는 웹훅 수신 (`POST /careeros/jobs/daily`)

두 시스템을 어떻게 공존시킬지 결정이 필요했습니다.

## Decision Drivers

* CareerOS 웹훅을 받으려면 HTTP 서버 필수 (Discord Gateway만으로 불가)
* Discord.py는 자체 asyncio 이벤트 루프에서 동작
* Fly.io 단일 인스턴스 배포 — 프로세스를 늘릴수록 비용·복잡도 증가
* 두 서버 간 상태 공유가 필요 (DiscordService 인스턴스 공유)

## Considered Options

1. **별도 프로세스** — FastAPI 프로세스 + Discord 봇 프로세스 (Docker Compose 2개)
2. **Discord Gateway만** — 웹훅 대신 Discord 봇이 polling으로 CareerOS 조회
3. **FastAPI + Discord.py 동일 asyncio 루프** ← 선택

## Decision Outcome

Chosen Option: **Option 3**.

Discord 봇을 `asyncio.create_task()`로 백그라운드 태스크로 실행하고, FastAPI uvicorn이 이벤트 루프의 메인 서버를 담당합니다.

```python
# main.py :: run_service()
async def run_service(self):
    # Discord 봇 → 백그라운드 태스크 (이벤트 루프 비점유)
    bot_task = asyncio.create_task(
        self.discord_service.bot.start(settings.discord_token)
    )
    # FastAPI → 메인 서버 (이벤트 루프 점유)
    server = uvicorn.Server(uvicorn.Config(app=self.web_application, ...))
    await server.serve()
```

**초기화 순서 (중요):**
```
1. MongoDB 연결
2. 서비스 매니저 초기화 (Notion, Discord, Sync)
3. Discord 봇 start_bot() — 슬래시 커맨드 등록
4. FastAPI 라우트 등록
5. run_service() → asyncio.create_task(bot.start) + server.serve()
```

Discord 봇 `start_bot()`과 `bot.start()` 호출 분리가 핵심입니다:
- `start_bot()`: 커맨드 등록 + 이벤트 핸들러 바인딩
- `bot.start()`: Gateway WebSocket 연결 (블로킹) → 반드시 `create_task`로 분리

### Consequences

* **Positive:**
  - 단일 프로세스 — Fly.io 최소 사양으로 운영 가능
  - `DiscordService` 인스턴스를 FastAPI 핸들러와 Discord 봇이 직접 공유 (IPC 불필요)
  - 단일 MongoDB 연결 공유
* **Negative/Trade-offs:**
  - Discord 봇이 무한 루프 실행 중이므로 `server.serve()` 종료 시 `bot_task.cancel()` 명시 필요
  - uvicorn worker 수를 늘려도 Discord 봇은 단일 인스턴스만 유지됨 (수평 확장 제한)
  - Discord API 오류로 봇 태스크가 예외 종료 시 FastAPI 서버는 계속 동작 (부분 장애 탐지 필요)

---

## Options Comparison Matrix

| Criteria | 별도 프로세스 | Discord polling | FastAPI + Discord 단일 루프 |
|---|---|---|---|
| **운영 복잡도** | 높음 (2개 컨테이너) | 낮음 | 낮음 |
| **실시간 웹훅 수신** | ✅ | ❌ (polling 지연) | ✅ |
| **상태 공유** | IPC 필요 | — | ✅ 메모리 공유 |
| **수평 확장** | ✅ | ✅ | ❌ (Discord 봇 중복 불가) |
| **Fly.io 비용** | 2x | 1x | 1x |
