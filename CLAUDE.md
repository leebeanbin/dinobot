# dinobot Agent Rules

FastAPI + Discord.py 봇 — CareerOS AI 커리어 플랫폼 연동 + Notion–Discord 팀 협업 자동화.

## 아키텍처 소스 오브 트루스

단일 asyncio 프로세스에서 FastAPI(웹훅 수신)와 Discord.py(봇)가 함께 동작한다.

```
src/
  controller/     HTTP 라우터 (webhook/, discord/ 슬래시 커맨드)
  service/        비즈니스 로직 (careeros/, notion/, discord/, sync/, analytics/)
  conversation/   온보딩 상태 머신 (state.py, onboarding_handler.py)
  dto/            데이터 전송 객체 (careeros/, notion/, discord/, common/)
  embeds/         Discord Embed 빌더
  interface/      서비스 인터페이스 정의
  utils/          공통 유틸리티
  core/           DB 연결, 로거, 설정, 예외

main.py           FastAPI 앱 + Discord 봇 통합 진입점 (ServiceManager)
```

## 코드 작성 전 반드시 확인

- **시스템 아키텍처**: [`docs/architecture/system-overview.md`](docs/architecture/system-overview.md)
- **CareerOS 연동 상세**: [`docs/CAREEROS_INTEGRATION.md`](docs/CAREEROS_INTEGRATION.md)
- **ADR (설계 결정)**: [`docs/adr/`](docs/adr/)

## 핵심 패턴

**CareerOS API 호출** — `src/service/careeros/careeros_api_client.py` 경유. 직접 httpx 호출 금지.

**온보딩 상태 전이** — `OnboardingState` enum 순서 준수:
```
CAREER_GOAL → RESUME → GITHUB → COMPLETE
```
상태는 MongoDB `onboarding_sessions` 컬렉션에 TTL(7일) 인덱스로 저장.

**Discord Embed** — `src/embeds/careeros_embed.py` 패턴을 따른다. 직접 `discord.Embed()` 생성 금지.

**웹훅 인증** — `POST /careeros/jobs/daily`는 반드시 `X-Webhook-Secret` 검증 후 처리.

## 절대 규칙

- **커밋에 `Co-Authored-By` 줄을 절대 넣지 않는다.** 작성자는 사용자 단독.
- 커밋은 논리 단위로 분리한다.
- asyncio 이벤트 루프를 블로킹하는 동기 코드를 `async def` 안에 직접 넣지 않는다. `asyncio.to_thread()` 사용.
- 환경변수는 `src/core/config.py`에서만 읽는다. 서비스 레이어에서 직접 `os.environ` 접근 금지.

## 코드 품질

```bash
poetry run black src/          # 포맷팅
poetry run ruff check src/     # 린팅
poetry run pytest              # 테스트
```

pre-commit 훅이 커밋 시 자동 실행된다.

## 에코시스템 연결

이 레포는 3개 프로젝트 포트폴리오의 알림 레이어다:
- **[beanllm](https://github.com/leebeanbin/beanllm)** — AI 인프라 (careerOS가 사용)
- **[careerOS](https://github.com/leebeanbin/careerOS)** — 커리어 AI 플랫폼 백엔드
- **dinobot** — Discord 봇 (이 레포)

전체 연결 구조: [`docs/architecture/system-overview.md`](docs/architecture/system-overview.md)
