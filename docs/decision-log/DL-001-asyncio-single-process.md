# DL-001: asyncio 단일 프로세스 패턴 선택

- **날짜:** 2025-11
- **상태:** 결정됨
- **관련 ADR:** [ADR-001](../adr/ADR-001-fastapi-discord-hybrid.md)

---

## 배경

dinobot은 두 가지 진입점이 필요하다:

1. **Discord.py 봇** — 사용자 슬래시 커맨드 처리
2. **FastAPI HTTP 서버** — CareerOS 웹훅 수신

두 서버를 어떻게 실행할지 결정이 필요했다.

---

## 고려한 옵션

| 옵션 | 설명 | 장점 | 단점 |
|------|------|------|------|
| **A. 별도 프로세스** | FastAPI 컨테이너 + Discord Bot 컨테이너 (Docker Compose 2개) | 독립 확장 가능 | Fly.io 비용 2배, IPC 필요 |
| **B. Discord polling** | Bot이 주기적으로 CareerOS를 polling | 단일 프로세스 | 실시간 웹훅 수신 불가, 지연 발생 |
| **C. 단일 asyncio 루프** | `create_task(bot.start())` + `server.serve()` 동시 실행 | 단일 프로세스, 메모리 공유 | 수평 확장 제한 |

---

## 결정

**옵션 C: FastAPI + Discord.py 단일 asyncio 프로세스**를 선택한다.

```python
async def run_service(self):
    bot_task = asyncio.create_task(
        self.discord_service.bot.start(settings.discord_token)
    )
    server = uvicorn.Server(uvicorn.Config(app=self.web_application, host="0.0.0.0", port=8889))
    await server.serve()
```

---

## 트레이드오프

**긍정적 결과:**
- Fly.io 최소 사양 (1 shared CPU, 256MB RAM)으로 운영 가능.
- `DiscordService` 인스턴스를 FastAPI 핸들러와 Discord Bot이 직접 공유 — IPC 불필요.
- 단일 MongoDB Motor 연결 공유.
- 배포 단순화: Dockerfile 1개, 단일 `fly.toml`.

**부정적 트레이드오프:**
- Discord Bot이 예외 종료 시 FastAPI는 계속 실행 — 부분 장애 탐지 로직 필요.
- uvicorn worker 수 증가가 Discord Bot 수에는 영향을 주지 않음 — 수평 확장 불가.
- 하나의 서비스(예: Notion sync)가 이벤트 루프를 블로킹하면 전체 영향.

**완화 방법:**
- `@safe_execution` 데코레이터로 uncaught exception이 루프를 중단하지 않도록 처리.
- `/health` 엔드포인트에서 Bot Gateway 연결 상태를 별도 추적 (개선 예정).
- SyncService에 `asyncio.sleep()`을 명시적으로 넣어 이벤트 루프 점유 방지.
