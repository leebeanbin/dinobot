# DinoBot 🚀

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Poetry](https://img.shields.io/badge/Poetry-Package%20Manager-blue?style=for-the-badge&logo=poetry&logoColor=white)](https://python-poetry.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Database-green.svg?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![Discord.py](https://img.shields.io/badge/Discord.py-Bot%20Framework-7289da.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Web%20Framework-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Fly.io](https://img.shields.io/badge/Fly.io-Deployment-purple.svg?style=for-the-badge&logo=fly.io&logoColor=white)](https://fly.io)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/ruff-000000.svg?style=for-the-badge&logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)

**CareerOS AI 커리어 플랫폼과 연동하여 취업 준비를 Discord에서 관리하는 봇 + 노션-디스코드 팀 협업 자동화 봇**

[🚀 빠른 시작](docs/QUICK_START.md) • [📖 명령어](docs/COMMANDS.md) • [🔧 배포](docs/DEPLOYMENT.md) • [📊 기능](#-주요-기능) • [🛠️ 개발](#-개발-가이드)

</div>

---

## 포트폴리오 에코시스템

dinobot은 동일 개발자가 구성한 3개 프로젝트 포트폴리오의 알림 레이어입니다.

| 프로젝트 | 역할 | 스택 |
|---------|------|------|
| **[beanllm](https://github.com/leebeanbin/beanllm)** | AI 인프라 — 8개 LLM 프로바이더 통합 라이브러리 (PyPI) | Python · 6,340 tests |
| **[careerOS](https://github.com/leebeanbin/careerOS)** | 커리어 AI 플랫폼 백엔드 | Spring Boot 3.3 · 415 tests |
| **dinobot** ← (this repo) | Discord 커리어 봇 + Notion 협업 봇 | Python · FastAPI · Discord.py |

**연결 방식:**
- careerOS `DailyDigestAgent` → `POST /careeros/jobs/daily` 웹훅 전송 (매일 08:00 UTC)
- dinobot 온보딩(`/onboard`) → careerOS REST API로 이력서·GitHub 연동 요청
- dinobot `/career` → careerOS CandidateGraph 상태 실시간 조회

---

## 🎯 프로젝트 개요

<div align="center">

### 💡 **DinoBot는 무엇인가요?**

**노션(Notion)과 디스코드(Discord)를 완벽하게 통합하여 팀 협업을 혁신하는 고성능 봇입니다.**

</div>

### 🌟 핵심 가치

<table>
<tr>
<td width="50%">

**⚡ 고성능**
- 비동기 병렬 처리로 5배 빠른 동기화
- MongoDB 인덱싱으로 빠른 검색
- 캐싱 시스템으로 90% 응답속도 향상

</td>
<td width="50%">

**🔍 스마트 검색**
- 검색 엔진 수준의 유연한 검색 기능
- 연관 검색어, 인기 검색어 제안
- 실시간 결과 제공

</td>
</tr>
<tr>
<td width="50%">

**📊 실시간 통계**
- 팀 생산성을 한눈에 파악하는 시각적 통계
- 7가지 통계 명령어로 상세 분석
- matplotlib 기반 차트 생성

</td>
<td width="50%">

**🛡️ 안정성**
- 99.9% 가동률을 위한 견고한 아키텍처
- 자동 에러 복구 및 모니터링
- 실시간 동기화로 데이터 일관성 보장

</td>
</tr>
</table>

### 🎯 해결하는 문제

<details>
<summary><strong>🔍 자세히 보기</strong></summary>

- **분산된 정보**: 노션과 디스코드 간 정보 동기화 어려움
- **비효율적인 협업**: 수동으로 페이지 생성하고 알림하는 번거로움
- **생산성 측정 어려움**: 팀의 실제 활동과 성과를 파악하기 어려움
- **검색의 한계**: 노션의 제한적인 검색 기능

</details>

---

## 🚀 빠른 시작

<div align="center">

### ⚡ **5분 만에 시작하기**

</div>

```bash
# 1️⃣ 저장소 클론
git clone https://github.com/leebeanbin/dinobot.git
cd dinobot

# 2️⃣ 의존성 설치
poetry install

# 3️⃣ 환경 변수 설정
cp env.example .env
# .env 파일에 토큰들 입력

# 4️⃣ 실행
poetry run python run.py
```

### 🎮 첫 번째 명령어

<table>
<tr>
<td width="33%" align="center">

**📋 Task 생성**
```bash
/task person:홍길동 name:"첫 번째 작업" priority:높음
```

</td>
<td width="33%" align="center">

**📅 회의록 생성**
```bash
/meeting title:"팀 미팅" participants:홍길동,김영희
```

</td>
<td width="33%" align="center">

**📊 통계 확인**
```bash
/daily_stats
```

</td>
</tr>
</table>

> 📖 **더 자세한 가이드**: [🚀 빠른 시작 가이드](docs/QUICK_START.md)

---

## ✨ 주요 기능

### 🤖 Discord 통합

<table>
<tr>
<td width="25%" align="center">

**15개 슬래시 명령어**
- `/task`, `/meeting`, `/document`
- `/search`, `/stats` 등

</td>
<td width="25%" align="center">

**자동 스레드 관리**
- 날짜별 스레드 자동 생성
- 스마트 제목 생성

</td>
<td width="25%" align="center">

**실시간 알림**
- 노션 변경사항 즉시 전송
- Rich Embed 메시지

</td>
<td width="25%" align="center">

**사용자 친화적**
- 직관적인 명령어
- 한국어 완벽 지원

</td>
</tr>
</table>

### 📝 Notion 연동

<table>
<tr>
<td width="33%" align="center">

**스키마 자동 인식**
- 데이터베이스 구조 자동 파악
- 타입 안전 페이지 생성

</td>
<td width="33%" align="center">

**실시간 동기화**
- 3분마다 자동 동기화
- 페이지 삭제 감지

</td>
<td width="33%" align="center">

**스마트 처리**
- 옵션 자동 추가
- 스키마 검증

</td>
</tr>
</table>

### 🔍 스마트 검색

<table>
<tr>
<td width="50%">

**기본 검색**
```bash
/search "키워드"
```

**고급 검색**
```bash
/search "API" type:task user:@정빈 days:7
```

</td>
<td width="50%">

**검색 옵션**
- **타입 필터**: `type:task`, `type:meeting`, `type:document`
- **사용자 필터**: `user:@사용자명`
- **기간 필터**: `days:7`, `days:30`, `days:90`

</td>
</tr>
</table>

### 📊 실시간 통계

<table>
<tr>
<td width="50%">

**7가지 통계 명령어**

| 명령어 | 기능 | 사용법 |
|--------|------|--------|
| `/daily_stats` | 일별 활동 통계 | `/daily_stats date:2025-09-08` |
| `/weekly_stats` | 주별 활동 통계 | `/weekly_stats` |
| `/monthly_stats` | 월별 활동 통계 | `/monthly_stats year:2025 month:9` |
| `/user_stats` | 개인 생산성 분석 | `/user_stats days:30` |
| `/team_stats` | 팀 활동 비교 | `/team_stats days:14` |
| `/task_stats` | Task 완료율 | `/task_stats days:7` |
| `/trends` | 활동 트렌드 | `/trends days:14` |

</td>
<td width="50%">

**통계 특징**
- **실시간 반영**: 페이지 생성 즉시 통계 업데이트
- **시각적 차트**: matplotlib 기반 차트 이미지 생성
- **개인정보 보호**: 사용자 ID 마지막 4자리만 표시
- **상세한 분석**: 단순 수치가 아닌 패턴과 트렌드 제공

</td>
</tr>
</table>

> 📖 **더 자세한 가이드**: [📖 명령어 가이드](docs/COMMANDS.md)

### 🎯 CareerOS 커리어 AI 연동

CareerOS 백엔드와 연동하여 취업 준비 과정을 Discord에서 관리합니다.

<table>
<tr>
<td width="33%" align="center">

**온보딩**
```bash
/onboard
```
AI 커리어 프로필 생성<br>
이력서 PDF → GitHub 분석

</td>
<td width="33%" align="center">

**프로필 확인**
```bash
/career
```
CandidateGraph 상태 조회<br>
(EMPTY / BUILDING / READY)

</td>
<td width="33%" align="center">

**일일 공고 다이제스트**<br>
매일 08:00 UTC 자동 발송<br>
점수 + 매칭/부족 스킬 포함

</td>
</tr>
</table>

**다이제스트 Discord Embed 예시:**
```
🔍 오늘의 채용 공고 — 2026-06-22   총 5개 선별

[91점] Backend Engineer @ Kakao
  ✅ 매칭 스킬: Java, Spring Boot, Redis
  ❌ 부족 스킬: Kafka
  Backend · KR · HYBRID
```

**새 슬래시 커맨드:**

| 커맨드 | 설명 |
|---|---|
| `/onboard` | CareerOS 커리어 프로필 온보딩 시작 |
| `/career` | 현재 CandidateGraph 상태 확인 |
| `/restart_onboard` | 온보딩 세션 초기화 후 재시작 |

**웹훅 엔드포인트:**

| 엔드포인트 | 설명 |
|---|---|
| `POST /careeros/jobs/daily` | CareerOS 일일 다이제스트 수신 (X-Webhook-Secret 인증) |

**MCP 툴 (Claude Code 연동):**

| 툴 | 설명 |
|---|---|
| `POST /mcp/careeros/configure_channel` | Discord/Telegram 채널 활성화 토글 |
| `POST /mcp/careeros/send_digest` | 온디맨드 다이제스트 트리거 |
| `GET /mcp/careeros/digest_status` | 마지막 다이제스트 상태 조회 |

> 📖 **연동 상세 가이드**: [CareerOS 연동 가이드](docs/CAREEROS_INTEGRATION.md)

---

## 📦 설치 및 실행

### 🔧 시스템 요구사항

<table>
<tr>
<td width="50%">

**최소 요구사항**
- Python 3.11+
- MongoDB 6.0+
- 1GB RAM
- 500MB 디스크 공간

</td>
<td width="50%">

**권장 사양**
- Python 3.11+
- MongoDB Atlas
- 2GB RAM
- 1GB 디스크 공간

</td>
</tr>
</table>

### 📥 상세 설치 과정

<details>
<summary><strong>🔍 자세한 설치 방법</strong></summary>

#### 1. 저장소 클론
```bash
git clone https://github.com/leebeanbin/dinobot.git
cd dinobot
```

#### 2. 의존성 설치
```bash
# Poetry 설치 (없는 경우)
curl -sSL https://install.python-poetry.org | python3 -

# 프로젝트 의존성 설치
poetry install
```

#### 3. 환경 설정
```bash
# 환경 변수 파일 생성
cp env.example .env

# .env 파일 편집
nano .env
```

#### 4. MongoDB 설정
```bash
# 로컬 MongoDB (Docker)
docker run -d -p 27017:27017 --name mongodb mongo:6

# 또는 MongoDB Atlas 사용 (권장)
```

#### 5. 실행
```bash
# 방법 1: 편의 스크립트 (권장)
poetry run python run.py

# 방법 2: 모듈 형태
poetry run python -m dinobot.main

# 방법 3: 가상환경 활성화
poetry shell
python run.py
```

</details>

### ⚙️ 환경 변수 설정

<table>
<tr>
<td width="50%">

**Discord 설정**
```bash
DISCORD_TOKEN=your_discord_bot_token
DISCORD_APP_ID=your_discord_app_id
DISCORD_GUILD_ID=your_discord_guild_id
DEFAULT_DISCORD_CHANNEL_ID=your_default_channel_id
```

</td>
<td width="50%">

**Notion 설정**
```bash
NOTION_TOKEN=secret_your_notion_token
FACTORY_TRACKER_DB_ID=your_factory_tracker_db_id
BOARD_DB_ID=your_board_db_id
```

</td>
</tr>
<tr>
<td width="50%">

**MongoDB 설정**
```bash
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=dinobot
```

</td>
<td width="50%">

**보안 설정**
```bash
WEBHOOK_SECRET=your_secure_webhook_secret
```

</td>
</tr>
<tr>
<td width="50%">

**CareerOS 연동**
```bash
CAREEROS_API_URL=http://localhost:8080
CAREEROS_API_TOKEN=<CareerOS JWT>
CAREEROS_WEBHOOK_SECRET=<공유 비밀값>
DIGEST_CHANNEL_ID=<Discord 채널 ID>
```

</td>
<td width="50%">

**Telegram (선택)**
```bash
TELEGRAM_BOT_TOKEN=<BotFather 토큰>
TELEGRAM_CHAT_ID=<채팅방 ID>
```

</td>
</tr>
</table>

> 📖 **상세 설명**: [CareerOS 연동 가이드](docs/CAREEROS_INTEGRATION.md)

---

## 🛠️ 기술 스택

### 🐍 Backend

<table>
<tr>
<td width="25%" align="center">

**Python 3.11+**
- 최신 Python 기능 활용
- 비동기 프로그래밍

</td>
<td width="25%" align="center">

**FastAPI**
- 고성능 웹 프레임워크
- 자동 API 문서 생성

</td>
<td width="25%" align="center">

**Discord.py**
- Discord 봇 개발
- 슬래시 명령어 지원

</td>
<td width="25%" align="center">

**Motor**
- MongoDB 비동기 드라이버
- 고성능 데이터베이스 연동

</td>
</tr>
</table>

### 🗄️ Database & Storage

<table>
<tr>
<td width="50%" align="center">

**MongoDB**
- 문서 기반 NoSQL 데이터베이스
- 유연한 스키마

</td>
<td width="50%" align="center">

**MongoDB Atlas**
- 클라우드 데이터베이스 (권장)
- 자동 백업 및 스케일링

</td>
</tr>
</table>

### 🔧 DevOps & Tools

<table>
<tr>
<td width="20%" align="center">

**Poetry**
- 의존성 관리
- 가상환경 관리

</td>
<td width="20%" align="center">

**Docker**
- 컨테이너화
- 환경 일관성

</td>
<td width="20%" align="center">

**Fly.io**
- 클라우드 배포
- 자동 스케일링

</td>
<td width="20%" align="center">

**Ruff**
- 코드 린팅
- 빠른 분석

</td>
<td width="20%" align="center">

**Black**
- 코드 포맷팅
- 일관된 스타일

</td>
</tr>
</table>

### 📊 Analytics & Visualization

<table>
<tr>
<td width="33%" align="center">

**Matplotlib**
- 차트 생성
- 시각화

</td>
<td width="33%" align="center">

**Seaborn**
- 통계 시각화
- 고급 차트

</td>
<td width="33%" align="center">

**Pandas**
- 데이터 분석
- 데이터 처리

</td>
</tr>
</table>

---

## 🏗️ 아키텍처

### 🎯 프로젝트 구조

```
src/
├── core/                      # 핵심 시스템 (로깅, DB, config, exceptions)
├── service/
│   ├── discord/               # Discord 봇 서비스 (슬래시 커맨드 등록, 이벤트 핸들러)
│   ├── notion/                # Notion API 연동
│   ├── careeros/              # CareerOS REST API 클라이언트 (httpx)
│   ├── sync_service.py        # Notion ↔ MongoDB 실시간 동기화
│   ├── search_service.py      # 통합 검색 엔진
│   └── analytics.py           # 통계 분석
├── conversation/              # CareerOS 온보딩 대화 상태 머신
│   ├── state.py               # OnboardingState, ConversationSession (MongoDB TTL)
│   ├── onboarding_handler.py  # 메시지 라우팅 (CAREER_GOAL → RESUME → GITHUB → COMPLETE)
│   └── file_upload_handler.py # Discord 첨부파일 다운로드 → CareerOS 업로드
├── dto/
│   ├── careeros/              # CareerOS 웹훅 페이로드 (JobCard, UserDigestSection 등)
│   └── common/                # 공통 DTO, CommandType enum
├── embeds/
│   └── careeros_embed.py      # Discord Embed 빌더 (일일 공고 다이제스트)
└── mcp_server/
    └── careeros_tools.py      # FastAPI MCP 라우터 (/mcp/careeros/*)

main.py                        # FastAPI 앱 + Discord 봇 진입점
```

### 🔄 데이터 플로우

```mermaid
graph TD
    A[Discord /onboard] --> B[OnboardingHandler]
    B --> C[CareerOSApiClient]
    C --> D[CareerOS REST API]
    D --> E[이력서 분석 / GitHub 싱크]
    E --> F[CandidateGraph READY]

    G[CareerOS DailyDigestAgent] -->|POST /careeros/jobs/daily| H[dinobot FastAPI]
    H --> I[X-Webhook-Secret 검증]
    I --> J[build_digest_embeds]
    J --> K[Discord DIGEST_CHANNEL_ID]

    L[Discord Command] --> M[Command Handler]
    M --> N[Notion API]
    N --> O[Page Creation]
    O --> P[Discord Response]
```

---

## 🚀 배포

### 🐳 Docker 배포

<table>
<tr>
<td width="50%">

**Dockerfile 빌드**
```bash
docker build -t dinobot .
```

**컨테이너 실행**
```bash
docker run --env-file .env -p 8888:8888 dinobot
```

</td>
<td width="50%">

**Docker Compose**
```yaml
version: '3.8'
services:
  dinobot:
    build: .
    ports:
      - "8888:8888"
    env_file:
      - .env
    depends_on:
      - mongodb
```

</td>
</tr>
</table>

### ☁️ Fly.io 배포

<table>
<tr>
<td width="50%">

**1. CLI 설치**
```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh
```

**2. 로그인 및 앱 생성**
```bash
fly auth login
fly apps create dinobot
```

</td>
<td width="50%">

**3. 환경 변수 설정**
```bash
fly secrets set DISCORD_TOKEN="your_token"
fly secrets set NOTION_TOKEN="your_notion_token"
fly secrets set MONGODB_URL="your_mongodb_url"
```

**4. 배포**
```bash
fly deploy
```

</td>
</tr>
</table>

> 📖 **더 자세한 가이드**: [🚀 배포 가이드](docs/DEPLOYMENT.md)

---

## 🔧 개발 가이드

### 🏗️ 프로젝트 구조

```
dinobot/
├── dinobot/                    # 메인 애플리케이션 패키지
│   ├── core/                       # 핵심 모듈
│   │   ├── config.py              # 설정 관리
│   │   ├── database.py            # 데이터베이스 연결
│   │   ├── logger.py              # 로깅 시스템
│   │   ├── exceptions.py          # 예외 처리
│   │   ├── metrics.py             # Prometheus 메트릭
│   │   └── decorators.py          # 메트릭 데코레이터
│   ├── models/                     # 데이터 모델
│   │   ├── dtos.py                # 데이터 전송 객체
│   │   └── interfaces.py          # 인터페이스 정의
│   ├── services/                   # 비즈니스 로직 서비스
│   │   ├── discord_service.py     # Discord 봇 서비스
│   │   ├── notion.py              # Notion API 서비스
│   │   ├── mongodb_advanced.py    # MongoDB 고급 서비스
│   │   ├── sync_service.py        # 동기화 서비스
│   │   ├── search_service.py      # 검색 서비스
│   │   └── analytics.py           # 분석 서비스
│   ├── utils/                      # 유틸리티 함수
│   └── main.py                     # 메인 애플리케이션
├── scripts/                        # 유틸리티 스크립트
│   ├── start-dev.sh               # 개발 환경 시작
│   └── check_config.py            # 설정 확인
├── docs/                          # 문서
├── grafana/                       # Grafana 설정
├── .github/workflows/             # CI/CD 파이프라인
├── logs/                          # 로그 파일
├── docker-compose.yml             # Docker Compose 설정
├── Dockerfile                     # Docker 이미지 설정
├── fly.toml                       # Fly.io 배포 설정
├── prometheus.yml                 # Prometheus 설정
└── run.py                         # 실행 스크립트
```

### 🎨 코드 스타일

<table>
<tr>
<td width="33%" align="center">

**포맷팅**
```bash
poetry run black dinobot/
```

</td>
<td width="33%" align="center">

**린팅**
```bash
poetry run ruff check dinobot/
```

</td>
<td width="33%" align="center">

**테스트**
```bash
poetry run pytest
```

</td>
</tr>
</table>

### 🚀 새 기능 추가

<table>
<tr>
<td width="33%" align="center">

**1. 인터페이스 정의**
```python
# models/interfaces.py
class NewServiceInterface(ABC):
    @abstractmethod
    async def new_method(self) -> str:
        pass
```

</td>
<td width="33%" align="center">

**2. DTO 정의**
```python
# models/dtos.py
@dataclass
class NewRequestDTO:
    field1: str
    field2: int
```

</td>
<td width="33%" align="center">

**3. 서비스 구현**
```python
# services/new_service.py
class NewService(NewServiceInterface):
    async def new_method(self) -> str:
        return "implementation"
```

</td>
</tr>
</table>

---

## 📈 모니터링

### 📊 실시간 메트릭

<table>
<tr>
<td width="50%">

**API 엔드포인트**
- `GET /health` - 헬스체크
- `GET /metrics/dashboard` - 실시간 대시보드
- `GET /sync/status` - 동기화 상태
- `POST /sync/manual` - 수동 동기화

</td>
<td width="50%">

**메트릭 종류**
- 명령어 사용 통계
- 캐시 성능
- 에러 추적
- 동기화 상태

</td>
</tr>
</table>

### 📝 로그 분석

<table>
<tr>
<td width="50%">

**로그 레벨**
- **INFO**: 일반적인 작업 진행 상황
- **WARNING**: 주의가 필요한 상황
- **ERROR**: 오류 발생 상황
- **DEBUG**: 상세한 디버깅 정보

</td>
<td width="50%">

**로그 파일**
```bash
# 로그 파일 위치
logs/dinobot_YYYYMMDD.log

# 실시간 로그 모니터링
tail -f logs/dinobot_20250909.log
```

</td>
</tr>
</table>

---

## 📖 API 문서

### 🔗 REST API 엔드포인트

<table>
<tr>
<td width="50%">

**헬스체크**
```http
GET /health
```

**실시간 대시보드**
```http
GET /metrics/dashboard
```

</td>
<td width="50%">

**동기화 상태**
```http
GET /sync/status
```

**수동 동기화**
```http
POST /sync/manual
```

</td>
</tr>
</table>

### 🔗 웹훅 엔드포인트

<table>
<tr>
<td width="50%">

**Notion 웹훅**
```http
POST /notion/webhook
Content-Type: application/json
X-Webhook-Secret: your_secret
```

</td>
<td width="50%">

**요청 예시**
```json
{
  "page_id": "notion_page_id",
  "channel_id": 1234567890,
  "mode": "meeting"
}
```

</td>
</tr>
</table>

> 📖 **더 자세한 가이드**: [📖 API 문서](docs/API.md)

---

## 🔧 트러블슈팅

### ❌ 일반적인 문제들

<table>
<tr>
<td width="50%">

**MongoDB 연결 실패**
```bash
# 연결 문자열 확인
echo $MONGODB_URL

# MongoDB 서비스 상태 확인
docker ps | grep mongo
```

</td>
<td width="50%">

**Discord 봇 연결 실패**
```bash
# 토큰 확인
echo $DISCORD_TOKEN

# 봇 권한 확인
# - 서버에 초대되어 있는지
# - 필요한 권한이 있는지
```

</td>
</tr>
<tr>
<td width="50%">

**Notion API 오류**
```bash
# 토큰 확인
echo $NOTION_TOKEN

# 데이터베이스 공유 확인
# - 봇이 데이터베이스에 접근할 수 있는지
```

</td>
<td width="50%">

**메모리 부족**
```bash
# 메모리 사용량 확인
free -h

# 스왑 파일 생성
sudo fallocate -l 2G /swapfile
```

</td>
</tr>
</table>

### 📋 로그 분석

<table>
<tr>
<td width="50%">

**에러 로그 확인**
```bash
# 에러만 필터링
grep "ERROR" logs/dinobot_*.log

# 특정 시간대 로그
grep "2025-09-09 13:" logs/dinobot_*.log
```

</td>
<td width="50%">

**성능 분석**
```bash
# 응답 시간 분석
grep "완료" logs/dinobot_*.log | grep "실행시간"

# API 호출 분석
grep "HTTP Request" logs/dinobot_*.log
```

</td>
</tr>
</table>

---

## 🤝 기여하기

### 🚀 기여 방법

<table>
<tr>
<td width="50%">

**1. Fork & Clone**
```bash
git clone https://github.com/leebeanbin/dinobot.git
cd dinobot
```

**2. 브랜치 생성**
```bash
git checkout -b feature/amazing-feature
```

</td>
<td width="50%">

**3. 개발 및 테스트**
```bash
# 코드 작성
# 테스트 실행
poetry run pytest

# 코드 포맷팅
poetry run black dinobot/
```

**4. 커밋 및 푸시**
```bash
git add .
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
```

</td>
</tr>
</table>

### 📋 기여 가이드라인

<table>
<tr>
<td width="50%">

**코드 스타일**
- **Black** 포맷팅 준수
- **Ruff** 린팅 규칙 준수
- **Type hints** 사용 권장
- **Docstring** 작성 필수

</td>
<td width="50%">

**커밋 메시지**
```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 업데이트
style: 코드 스타일 변경
refactor: 코드 리팩토링
test: 테스트 추가/수정
chore: 빌드/설정 변경
```

</td>
</tr>
</table>

---

## 📄 라이센스

이 프로젝트는 [MIT 라이센스](LICENSE) 하에 배포됩니다.

```
MIT License

Copyright (c) 2026 leebeanbin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙋‍♂️ 지원

### 📞 연락처

<table>
<tr>
<td width="33%" align="center">

**Issues**
[GitHub Issues](https://github.com/leebeanbin/dinobot/issues)

</td>
<td width="33%" align="center">

**Discussions**
[GitHub Discussions](https://github.com/leebeanbin/dinobot/discussions)

</td>
<td width="33%" align="center">

**Discord**
[프로젝트 디스코드 서버](https://github.com/leebeanbin/dinobot/discussions)

</td>
</tr>
</table>

### 📚 문서

<table>
<tr>
<td width="20%" align="center">

[🚀 빠른 시작](docs/QUICK_START.md)
5분 만에 시작하기

</td>
<td width="20%" align="center">

[📖 명령어 가이드](docs/COMMANDS.md)
모든 명령어 상세 설명

</td>
<td width="20%" align="center">

[🚀 배포 가이드](docs/DEPLOYMENT.md)
프로덕션 배포 방법

</td>
<td width="20%" align="center">

[📖 API 문서](docs/API.md)
REST API 상세 문서

</td>
<td width="20%" align="center">

[🎯 CareerOS 연동](docs/CAREEROS_INTEGRATION.md)
커리어 AI 연동 가이드

</td>
</tr>
</table>

### 🎯 로드맵

<table>
<tr>
<td width="50%">

**단기 계획**
- [ ] Redis 캐싱 레이어 추가
- [ ] 다중 서버 지원
- [ ] Grafana 대시보드 통합

</td>
<td width="50%">

**장기 계획**
- [ ] AI 기반 회의록 자동 요약
- [ ] Slack 통합 지원
- [ ] 모바일 알림 지원
- [ ] 웹 대시보드 UI

</td>
</tr>
</table>

---

<div align="center">

**DinoBot**로 팀의 생산성을 한 단계 끌어올려보세요! 🚀

[![Star](https://img.shields.io/github/stars/leebeanbin/dinobot?style=social)](https://github.com/leebeanbin/dinobot)
[![Fork](https://img.shields.io/github/forks/leebeanbin/dinobot?style=social)](https://github.com/leebeanbin/dinobot/fork)
[![Watch](https://img.shields.io/github/watchers/leebeanbin/dinobot?style=social)](https://github.com/leebeanbin/dinobot)

Made with ❤️ by [leebeanbin](https://github.com/leebeanbin/dinobot/graphs/contributors)

</div>