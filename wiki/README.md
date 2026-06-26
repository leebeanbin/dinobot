# dinobot Wiki

dinobot은 CareerOS AI 커리어 플랫폼 연동 봇이자 Notion–Discord 협업 자동화 봇이다.

## 아키텍처

```mermaid
graph TB
    subgraph CLIENT["Client Zone"]
        DISCORD[Discord Guild<br/>Users / Slash Commands]
        CAREEROS_API[CareerOS API :8080]
    end

    subgraph PROCESS["Single asyncio Process (:8889)"]
        direction TB
        subgraph HTTP["FastAPI HTTP Server"]
            WH[POST /careeros/jobs/daily]
            HEALTH[GET /health]
            MCP[POST /mcp/careeros/*]
        end
        subgraph BOT["Discord.py Bot"]
            EVENTS[on_message / on_ready]
            SLASH[/onboard /sync /status /help]
        end
        SM[ServiceManager<br/>Dependency Hub]
        subgraph SERVICES["Services"]
            ONBOARD[OnboardingService]
            NOTION[NotionSyncService]
            NOTIFY[NotificationService]
            CLIENT_SVC[CareerOSApiClient]
        end
    end

    subgraph INFRA["Infrastructure"]
        MONGO[(MongoDB Motor<br/>sessions / notion_pages)]
        PROM[Prometheus :9090/metrics]
    end

    DISCORD -- "Gateway events" --> BOT
    CAREEROS_API -- "POST /careeros/jobs/daily" --> HTTP
    HTTP --> SM
    BOT --> SM
    SM --> SERVICES
    SERVICES --> MONGO
    CLIENT_SVC --> CAREEROS_API
```

## 이벤트 플로우

```mermaid
flowchart TD
    subgraph ONBOARD["온보딩 플로우"]
        JOIN[/onboard 실행] --> GOAL[커리어 목표 수집]
        GOAL --> RESUME_Q[이력서 요청]
        RESUME_Q --> RESUME_A[PDF 업로드 → CareerOS 전송]
        RESUME_A --> GITHUB_Q[GitHub 아이디 요청]
        GITHUB_Q --> GITHUB_A[GitHub 동기화 트리거]
        GITHUB_A --> COMPLETE[State: COMPLETE]
    end

    subgraph DIGEST["일일 다이제스트 (08:00 UTC)"]
        SCHED[CareerOS POST /careeros/jobs/daily] --> RECV[Webhook 수신]
        RECV --> RENDER[Discord Embed 생성]
        RENDER --> DM[사용자 DM 전송]
    end

    subgraph NOTION["Notion 동기화"]
        CMD[/sync 커맨드] --> PULL[Notion 페이지 조회]
        PULL --> DIFF[notion_pages 컬렉션 비교]
        DIFF --> UPSERT[변경 페이지 CareerOS 업서트]
        UPSERT --> ACK[동기화 결과 응답]
    end
```

## 도메인 문서

| 도메인 | 설명 | 문서 |
|--------|------|------|
| Architecture | 시스템 구성 + asyncio 패턴 | [architecture.md](architecture.md) |
| CareerOS | CareerOS API 연동 클라이언트 | [careeros.md](careeros.md) |
| Onboarding | 온보딩 상태 머신 | [onboarding.md](onboarding.md) |
| Notion | Notion DB 연동 | [notion.md](notion.md) |
| Discord | 슬래시 커맨드 + Embed | [discord.md](discord.md) |
| Analytics | Prometheus 메트릭 | [analytics.md](analytics.md) |
| MCP | MCP 서버 툴 | [mcp.md](mcp.md) |

## 운영 문서

- [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) — Fly.io 배포
- [docs/MONITORING.md](../docs/MONITORING.md) — Prometheus + Grafana
- [docs/playbooks/](../docs/playbooks/) — 인시던트 런북
- [docs/decision-log/](../docs/decision-log/) — 의사결정 로그

## ADR (Architecture Decision Records)

| ADR | 제목 |
|-----|------|
| [ADR-001](../docs/adr/ADR-001-fastapi-discord-hybrid.md) | FastAPI + Discord.py 단일 프로세스 동시 실행 |
| [ADR-002](../docs/adr/ADR-002-mongodb-conversation-state.md) | MongoDB TTL 문서로 온보딩 대화 상태 관리 |
