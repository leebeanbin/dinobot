# Discord Integration

dinobot은 Discord.py를 사용하여 슬래시 커맨드를 처리하고, Embed 빌더로 응답을 포맷한다.

---

## 슬래시 커맨드 목록

### 온보딩

| 커맨드 | 설명 |
|--------|------|
| `/onboard` | CareerOS 커리어 온보딩 시작 |
| `/skip` | 현재 온보딩 단계 건너뜀 |
| `/restart_onboard` | 온보딩 세션 초기화 후 재시작 |
| `/career` | CandidateGraph 조회 (커리어 프로필 현황) |

### Notion 작업

| 커맨드 | 설명 |
|--------|------|
| `/task` | Notion Factory Tracker에 태스크 생성 |
| `/meeting` | Notion Board에 회의록 생성 |
| `/document` | Notion에 문서 생성 |
| `/search` | 저장된 Notion 페이지 전문 검색 |

### 분석/모니터링

| 커맨드 | 설명 |
|--------|------|
| `/analytics` | 메트릭 대시보드 요약 |
| `/stats` | MongoDB 통계 조회 |

---

## Embed 빌더 패턴

`src/embeds/careeros_embed.py`는 CareerOS 페이로드를 Discord Embed로 변환한다.

**주요 함수:**

| 함수 | 입력 | 출력 |
|------|------|------|
| `build_job_card_embed(job)` | `JobCard` | 단일 채용 공고 Embed |
| `build_digest_embeds(section, date)` | `UserDigestSection` | 헤더 + 공고 Embed 리스트 |
| `build_digest_embeds_from_payload(payload)` | `CareerOsJobDigestPayload` | `{userId: [Embed]}` 딕셔너리 |

**Embed 출력 예시:**
```
🔍 오늘의 채용 공고 — 2026-06-26   총 5개 선별

[91점] Backend Engineer @ Kakao
  ✅ 매칭 스킬: Java, Spring Boot, Redis
  ❌ 부족 스킬: Kafka
  Backend · KR · HYBRID
```

---

## 웹훅 인증

웹훅 수신 엔드포인트(`/careeros/jobs/daily`, `/notion/webhook`)는 `X-Webhook-Secret` 헤더로 요청을 인증한다.

```python
# 인증 실패 시 HTTP 401 반환
if request.headers.get("X-Webhook-Secret") != settings.webhook_secret:
    raise HTTPException(status_code=401)
```

설정 키: `WEBHOOK_SECRET` (환경변수 / Fly.io secret)

---

## Discord.py 봇 초기화 순서

```
1. start_bot() 호출
   ├── 슬래시 커맨드 등록 (app_commands.tree.sync)
   └── 이벤트 핸들러 바인딩 (on_ready, on_message)

2. asyncio.create_task(bot.start(DISCORD_TOKEN))
   └── Gateway WebSocket 연결 (블로킹 코루틴)
```

`start_bot()`과 `bot.start()`는 반드시 분리 호출해야 한다. `bot.start()`를 먼저 호출하면 Gateway에 블로킹되어 커맨드 등록이 실행되지 않는다.
