# CareerOS ↔ dinobot 연동 가이드

dinobot은 [CareerOS](https://github.com/leebeanbin/careerOS) 백엔드와 두 가지 방식으로 통신합니다.

1. **dinobot → CareerOS**: REST API 호출 (이력서 업로드, GitHub 싱크 트리거, 그래프 조회)
2. **CareerOS → dinobot**: Webhook (일일 공고 다이제스트 푸시)

---

## 아키텍처 개요

```
사용자 (Discord)
  │
  ├── /onboard ──────────────────────────────────────┐
  │   /career                                        │
  │   /restart_onboard                               │
  │   (메시지: 이력서 PDF, GitHub ID 입력)            │
  │                                                  ▼
  │                                       dinobot (FastAPI + discord.py)
  │                                                  │
  │                                    ┌─────────────┴──────────────────┐
  │                                    │  CareerOSApiClient (httpx)     │
  │                                    │  POST /api/v1/resumes          │
  │                                    │  POST /api/v1/github/sync      │
  │                                    │  GET  /api/v1/candidate/{id}/graph │
  │                                    │  POST /api/v1/digest/trigger   │
  │                                    └─────────────┬──────────────────┘
  │                                                  │
  │                                       CareerOS Spring Boot
  │                                                  │
  │    ◄─── Discord Embed (일일 공고) ───────────────┤
  │                                    POST /careeros/jobs/daily
  └── (Telegram은 CareerOS가 직접 Bot API 호출)
```

---

## 환경 변수 설정

`.env.example`을 복사한 뒤 아래 값을 채웁니다.

### Discord / Notion (기존)

| 변수 | 설명 | 예시 |
|---|---|---|
| `DISCORD_TOKEN` | Discord 봇 토큰 (BotFather) | `MTAx...` |
| `DISCORD_APP_ID` | Discord 앱 ID | `123456789` |
| `DISCORD_GUILD_ID` | 봇이 동작할 서버 ID | `987654321` |
| `DISCORD_CHANNEL_ID` | 기본 알림 채널 | `111222333` |
| `DEFAULT_DISCORD_CHANNEL_ID` | Notion 동기화 결과 채널 | `444555666` |
| `NOTION_TOKEN` | Notion 통합 토큰 | `secret_...` |
| `FACTORY_TRACKER_DB_ID` | Notion DB ID (작업 추적) | `abc123...` |
| `BOARD_DB_ID` | Notion DB ID (칸반 보드) | `def456...` |
| `MONGODB_URL` | MongoDB 연결 문자열 | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | dinobot DB 이름 | `dinobot` |
| `HOST` / `PORT` | FastAPI 서버 주소 | `0.0.0.0` / `8889` |
| `WEBHOOK_SECRET` | Notion 웹훅 인증 비밀값 | `my-notion-webhook-secret` |

### CareerOS 연동 (신규)

| 변수 | 설명 | 어디서 얻는가 |
|---|---|---|
| `CAREEROS_API_URL` | CareerOS 백엔드 기본 URL | 로컬: `http://localhost:8080`, 프로덕션 URL |
| `CAREEROS_API_TOKEN` | CareerOS 서비스 계정 JWT | CareerOS `POST /api/v1/auth/login` 응답 `accessToken` |
| `CAREEROS_WEBHOOK_SECRET` | dinobot 웹훅 인증 비밀값 | CareerOS `app.dinobot.webhook-secret` 설정과 **동일한 값** |
| `DIGEST_CHANNEL_ID` | 일일 공고 다이제스트 Discord 채널 ID | Discord 채널 우클릭 → "ID 복사" |

### Telegram (선택)

> Telegram 채널 발송은 CareerOS가 Bot API를 직접 호출합니다.
> dinobot은 MCP 툴을 통해 활성화 여부를 제어하는 역할만 합니다.

| 변수 | 설명 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather에서 발급한 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 수신 채팅방/채널 ID (예: `-1001234567890`) |

---

## 온보딩 플로우

```
Discord /onboard
  → OnboardingHandler.start()
      → MongoDB에 OnboardingSession 생성 (state: CAREER_GOAL)
      → "어떤 개발자가 되고 싶으신가요?" 안내

사용자: "Spring Boot 백엔드 개발자"
  → state: RESUME
  → "이력서 PDF를 업로드해 주세요 (없으면 /skip)"

사용자: (PDF 첨부)
  → download_attachment()
  → careeros_client.upload_resume()  → POST /api/v1/resumes
  → state: GITHUB
  → "GitHub 아이디를 알려주세요 (/skip 가능)"

사용자: "leebeanbin"
  → careeros_client.trigger_github_sync()  → POST /api/v1/github/sync
  → state: COMPLETE
  → "프로필 생성 완료! 매일 맞춤 공고를 보내드릴게요."
```

### 지원 슬래시 커맨드

| 커맨드 | 설명 |
|---|---|
| `/onboard` | 온보딩 시작 (또는 재시작) |
| `/career` | 현재 커리어 프로필 상태 조회 (`CandidateGraph.status`) |
| `/restart_onboard` | 온보딩 세션 초기화 후 처음부터 |

---

## 일일 공고 다이제스트 웹훅

CareerOS `DailyDigestAgent`가 매일 08:00 UTC에 다이제스트를 완료하면
`POST /careeros/jobs/daily` 를 dinobot으로 전송합니다.

### 요청 헤더

```
X-Webhook-Secret: <CAREEROS_WEBHOOK_SECRET>
Content-Type: application/json
```

### 요청 바디

```json
{
  "digestDate": "2026-06-22",
  "sections": [
    {
      "userId": 42,
      "jobs": [
        {
          "jobId": "abc123",
          "title": "Backend Engineer",
          "companyName": "Kakao",
          "applyUrl": "https://...",
          "score": 91.5,
          "matchedSkills": ["Java", "Spring Boot", "Redis"],
          "missingSkills": ["Kafka"],
          "roleCategory": "BACKEND",
          "country": "KR",
          "remoteType": "HYBRID"
        }
      ]
    }
  ]
}
```

### dinobot 처리 흐름

1. `X-Webhook-Secret` 검증
2. `CareerOsJobDigestPayload.from_dict()` 파싱
3. `build_digest_embeds_from_payload()` → user별 Discord Embed 리스트 생성
4. `DIGEST_CHANNEL_ID` 채널에 Embed 전송

---

## MCP 툴 (Claude Code 연동)

dinobot은 `/mcp/careeros` 경로로 MCP 툴을 FastAPI 라우터로 노출합니다.

| 엔드포인트 | 설명 |
|---|---|
| `POST /mcp/careeros/configure_channel` | Discord / Telegram 채널 활성화 토글 |
| `POST /mcp/careeros/send_digest` | 온디맨드 다이제스트 트리거 |
| `GET /mcp/careeros/digest_status` | 마지막 다이제스트 상태 + 채널 설정 조회 |

Claude Code에서 사용 예:
```
careeros.configure_channel(channel_type="telegram", enabled=true)
careeros.send_digest(channel_type="discord", user_id=42)
careeros.digest_status()
```

---

## CareerOS 설정 (백엔드 측)

CareerOS `application.yml`에 아래 설정이 있어야 dinobot 연동이 활성화됩니다.

```yaml
app:
  dinobot:
    base-url: ${DINOBOT_BASE_URL:http://localhost:8889}
    webhook-secret: ${DINOBOT_WEBHOOK_SECRET:}   # dinobot의 CAREEROS_WEBHOOK_SECRET과 동일
  digest:
    scheduler:
      enabled: ${DIGEST_SCHEDULER_ENABLED:false}
      cron: ${DIGEST_CRON:0 0 8 * * *}           # 08:00 UTC = 17:00 KST
  telegram:
    enabled: ${TELEGRAM_ENABLED:false}
    bot-token: ${TELEGRAM_BOT_TOKEN:}
    chat-id: ${TELEGRAM_CHAT_ID:}
```

---

## 로컬 개발 시작 순서

```bash
# 1. CareerOS 백엔드 기동
cd /path/to/careerOS
docker compose up -d
./gradlew bootRun --args='--spring.profiles.active=local'

# 2. dinobot 기동 (별도 터미널)
cd /path/to/dinobot
cp .env.example .env   # 값 채우기
poetry install
poetry run python run.py

# 3. 웹훅 테스트 (로컬)
curl -X POST http://localhost:8889/careeros/jobs/daily \
  -H "X-Webhook-Secret: test-secret" \
  -H "Content-Type: application/json" \
  -d '{"digestDate":"2026-06-22","sections":[]}'
```
