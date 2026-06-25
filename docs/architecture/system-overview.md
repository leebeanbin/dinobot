# dinobot 시스템 아키텍처

dinobot은 두 가지 역할을 하나의 프로세스에서 수행합니다:
1. **CareerOS 연동 봇** — 취업 준비 온보딩 + 일일 공고 다이제스트 전달
2. **Notion–Discord 협업 봇** — 태스크/회의록 생성, 검색, 통계

---

## 시스템 컴포넌트 다이어그램

```mermaid
graph TB
    subgraph process ["단일 Python 프로세스 (asyncio 이벤트 루프)"]
        direction TB
        FW["FastAPI (uvicorn)\n웹훅 수신 서버\nPORT :8889"]
        BOT["Discord.py Bot\nasyncio.create_task() 백그라운드"]
        SM["ServiceManager\n(서비스 통합 관리자)"]
        NS["NotionService\nAPI 클라이언트"]
        DS["DiscordService\n봇 커맨드 핸들러"]
        SS["SyncService\nNotion↔MongoDB 3분 동기화"]
        CC["CareerOSApiClient\nhttpx 비동기 HTTP"]
        OH["OnboardingHandler\n온보딩 상태 머신"]
        FW --> SM
        BOT --> SM
        SM --> NS & DS & SS & CC & OH
        OH --> CC
    end

    subgraph external ["외부 시스템"]
        CAREEROS["CareerOS\n(Spring Boot :8080)"]
        NOTION["Notion API"]
        DISCORD_API["Discord API\n(Gateway + REST)"]
        MONGO["MongoDB\n(onboarding_sessions\n+ notion_pages)"]
    end

    FW -->|"POST /careeros/jobs/daily\n(X-Webhook-Secret)"| FW
    CAREEROS -->|"웹훅 전송"| FW
    CC -->|"httpx async"| CAREEROS
    NS -->|"httpx"| NOTION
    DS <-->|"Gateway WS\n+ REST"| DISCORD_API
    SM <-->|"Motor async"| MONGO
```

---

## 모듈 책임 테이블

| 경로 | 역할 |
|------|------|
| `main.py :: ServiceManager` | FastAPI 앱 + Discord 봇 통합 초기화, 라우트 등록, 워크플로우 디스패치 |
| `src/service/careeros/careeros_api_client.py` | CareerOS REST API 호출 (이력서 업로드, GitHub sync 트리거, 그래프 조회) |
| `src/conversation/onboarding_handler.py` | 온보딩 상태 머신 — 메시지 라우팅, 상태 전이 |
| `src/conversation/state.py` | `ConversationSession` DTO + MongoDB upsert/get/delete |
| `src/conversation/file_upload_handler.py` | Discord 첨부파일(PDF) 다운로드 → CareerOS 업로드 |
| `src/embeds/careeros_embed.py` | `CareerOsJobDigestPayload` → `discord.Embed` 변환 |
| `src/service/notion/` | Notion DB 페이지 CRUD (task/meeting/document) |
| `src/service/sync/sync_service.py` | Notion ↔ MongoDB 실시간 동기화 (3분 주기) |
| `src/service/analytics/` | Prometheus 메트릭, MongoDB 성능 분석, 통계 차트 |
| `mcp_server/careeros_tools.py` | FastAPI MCP 라우터 (`/mcp/careeros/*`) |

---

## FastAPI + Discord 동시 실행 패턴

```python
# main.py :: run_service()
async def run_service(self):
    # Discord 봇 → asyncio 백그라운드 태스크
    bot_task = asyncio.create_task(
        self.discord_service.bot.start(settings.discord_token)
    )
    # FastAPI uvicorn → 메인 서버 (이벤트 루프 점유)
    server = uvicorn.Server(uvicorn.Config(app=self.web_application, ...))
    await server.serve()
```

두 서비스가 **동일한 asyncio 이벤트 루프**에서 실행됩니다. (→ [ADR-001](../adr/ADR-001-fastapi-discord-hybrid.md))

---

## CareerOS 온보딩 플로우

```mermaid
sequenceDiagram
    actor User as 사용자 (Discord)
    participant D as dinobot<br>(Discord + FastAPI)
    participant S as ConversationSession<br>(MongoDB)
    participant C as CareerOS API<br>(Spring Boot)

    User->>D: /onboard
    D->>S: upsert(state=CAREER_GOAL)
    D-->>User: "어떤 개발자가 되고 싶으신가요?"

    User->>D: "백엔드 엔지니어"
    D->>S: update(career_goal_text, state=RESUME)
    D-->>User: "이력서 PDF를 업로드해 주세요"

    User->>D: PDF 첨부파일 전송
    D->>C: POST /api/v1/resume/upload (multipart PDF)
    C-->>D: { resumeId: "abc123" }
    D->>S: update(resume_id, state=GITHUB)
    D-->>User: "이력서 분석 중... GitHub 아이디를 알려주세요"

    User->>D: "leebeanbin"
    D->>C: POST /api/v1/github/sync { userId, githubUsername }
    C-->>D: { syncId: "xyz" }
    D->>S: update(github_username, state=COMPLETE)
    D-->>User: "✅ 커리어 프로필 생성 완료!"
```

### 온보딩 상태 머신

```mermaid
stateDiagram-v2
    [*] --> CAREER_GOAL : /onboard
    CAREER_GOAL --> RESUME : 목표 텍스트 입력
    RESUME --> GITHUB : PDF 업로드 또는 /skip
    GITHUB --> COMPLETE : GitHub 아이디 또는 /skip
    COMPLETE --> CAREER_GOAL : /restart_onboard (세션 초기화)
```

**`ConversationSession` 필드:**
| 필드 | 타입 | 설명 |
|------|------|------|
| `channel_user_id` | str | Discord 사용자 ID (복합 키) |
| `channel_type` | DISCORD \| TELEGRAM | 채널 타입 (복합 키) |
| `state` | OnboardingState | 현재 상태 |
| `career_goal_text` | str? | 입력된 커리어 목표 |
| `resume_id` | str? | CareerOS resumeId |
| `github_username` | str? | GitHub 사용자명 |
| `careeros_user_id` | int? | CareerOS userId |
| `expires_at` | datetime | TTL 7일 (MongoDB index) |

---

## 일일 공고 다이제스트 플로우

```mermaid
sequenceDiagram
    participant C as CareerOS<br>DailyDigestAgent<br>(08:00 UTC)
    participant D as dinobot<br>FastAPI
    participant E as careeros_embed.py
    participant DC as Discord 채널

    C->>D: POST /careeros/jobs/daily<br>X-Webhook-Secret: <secret>
    D->>D: X-Webhook-Secret 검증
    D->>D: CareerOsJobDigestPayload.from_dict(raw)
    D->>E: build_digest_embeds_from_payload(payload)
    E-->>D: { userId: [Embed, ...], ... }
    D->>DC: channel.send(embed=embed) × N jobs
    DC-->>C: HTTP 200 { success: true, sent: N }
```

**Discord Embed 출력 형식:**
```
🔍 오늘의 채용 공고 — 2026-06-25   총 5개 선별

[91점] Backend Engineer @ Kakao
  ✅ 매칭 스킬: Java, Spring Boot, Redis
  ❌ 부족 스킬: Kafka
  Backend · KR · HYBRID
```

---

## 웹훅 엔드포인트 목록

| Method | Path | 인증 | 역할 |
|--------|------|------|------|
| `POST` | `/careeros/jobs/daily` | `X-Webhook-Secret` | CareerOS 일일 다이제스트 수신 |
| `POST` | `/notion/webhook` | `X-Webhook-Secret` | Notion 변경사항 수신 → Discord 전달 |
| `GET` | `/health` | 없음 | 서비스 헬스체크 |
| `GET` | `/metrics/dashboard` | 없음 | Prometheus 실시간 대시보드 |
| `GET` | `/sync/status` | 없음 | Notion 동기화 상태 |
| `POST` | `/sync/manual` | 없음 | 수동 동기화 트리거 |
| `POST` | `/mcp/careeros/configure_channel` | — | Discord/Telegram 채널 토글 |
| `POST` | `/mcp/careeros/send_digest` | — | 온디맨드 다이제스트 트리거 |
| `GET` | `/mcp/careeros/digest_status` | — | 마지막 다이제스트 상태 |

---

## 배포 아키텍처

```
Fly.io (단일 인스턴스)
  └── dinobot (Python 3.11, Docker)
        ├── FastAPI :8889 (uvicorn)
        └── Discord.py (asyncio task)

MongoDB Atlas (외부)
  └── onboarding_sessions (TTL 7d)
  └── notion_pages (Notion 캐시)

Prometheus :9090 (메트릭 스크래핑)
```
