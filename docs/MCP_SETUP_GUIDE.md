# MCP 통합 시스템 설정 가이드

## 🎯 구현 완료된 기능

### 1. MCP 기반 통합 서비스
- **Discord MCP 서버**: 메시지 전송, 스레드 생성, 이벤트 생성/관리
- **Notion MCP 서버**: DB 작업, 페이지 생성/수정, 캘린더 연동
- **Google Calendar MCP 서버**: 이벤트 생성/수정, 가용성 확인, 최적 시간 찾기
- **통합 MCP 클라이언트**: 모든 서비스를 통합 관리하는 워크플로우

### 2. 실제 DB 스키마 기반 구현
- **Factory Tracker DB**: `Task name`, `Person`, `Priority`, `Due date`, `Status`, `Task type`
- **Board DB**: `Name`, `Participants`, `Status` (multi_select)

### 3. Discord 명령어 개선
- **Task 명령어**: `days` 파라미터 추가 (마감일 자동 계산)
- **Meeting 명령어**: MCP를 통한 통합 회의 생성 (Notion + Google Calendar + Discord Event)

## 🔧 필요한 환경 변수 설정

### 기존 설정 (이미 있음)
```bash
# Discord
DISCORD_TOKEN=your_discord_token
DISCORD_APP_ID=your_discord_app_id
DISCORD_GUILD_ID=your_discord_guild_id

# Notion
NOTION_TOKEN=your_notion_token
FACTORY_TRACKER_DB_ID=your_factory_tracker_db_id
BOARD_DB_ID=your_board_db_id
```

### 새로 추가해야 할 설정
```bash
# Google Calendar API
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token.json

# Discord Event (선택사항)
DISCORD_EVENT_CHANNEL_ID=your_event_channel_id
```

## 📋 Google Calendar API 설정 방법

### 1. Google Cloud Console 설정
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. "API 및 서비스" > "라이브러리" 이동
4. "Google Calendar API" 검색 후 활성화

### 2. OAuth 2.0 클라이언트 ID 생성
1. "API 및 서비스" > "사용자 인증 정보" 이동
2. "사용자 인증 정보 만들기" > "OAuth 클라이언트 ID" 선택
3. 애플리케이션 유형: "데스크톱 애플리케이션"
4. 클라이언트 ID 생성 후 JSON 파일 다운로드
5. 다운로드한 파일을 `credentials.json`으로 프로젝트 루트에 저장

### 3. 자동 OAuth 로그인
```bash
# 애플리케이션 실행 시 자동으로 Google 로그인 진행
poetry run python run.py

# 또는 직접 테스트
poetry run python -c "
from services.mcp.google_calendar_mcp_server import GoogleCalendarMCPServer
server = GoogleCalendarMCPServer()
print('Google Calendar 초기화 완료')
"
```

**OAuth 로그인 과정:**
1. 애플리케이션 실행 시 자동으로 브라우저가 열림
2. Google 계정으로 로그인
3. 권한 승인
4. 토큰이 자동으로 `token.json`에 저장
5. 이후 실행 시 자동으로 토큰 사용

## 🤖 Discord Bot 권한 설정

### 필요한 권한
- `SEND_MESSAGES`
- `CREATE_EVENTS` (이벤트 생성)
- `MANAGE_EVENTS` (이벤트 관리)
- `EMBED_LINKS`
- `USE_SLASH_COMMANDS`

### Discord Developer Portal 설정
1. [Discord Developer Portal](https://discord.com/developers/applications) 접속
2. 해당 애플리케이션 선택
3. "Bot" 탭에서 필요한 권한 추가
4. "OAuth2" > "URL Generator"에서 권한 선택 후 URL 생성
5. 생성된 URL로 봇을 서버에 초대

## 🧪 테스트 방법

### 1. DB 스키마 확인
```bash
poetry run python check_db_schema.py
```

### 2. MCP 서비스 테스트
```bash
poetry run python -c "
import asyncio
from services.mcp.unified_mcp_manager import UnifiedMCPManager

async def test_mcp():
    manager = UnifiedMCPManager()
    await manager.initialize()
    
    # 사용 가능한 도구 목록 확인
    tools = await manager.list_available_tools()
    print('사용 가능한 도구:', tools)

asyncio.run(test_mcp())
"
```

### 3. 회의 생성 테스트
```bash
poetry run python -c "
import asyncio
from datetime import datetime, timedelta
from services.mcp.unified_mcp_manager import UnifiedMCPManager

async def test_meeting():
    manager = UnifiedMCPManager()
    await manager.initialize()
    
    result = await manager.create_meeting(
        title='테스트 회의',
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        participants=['소현', '정빈'],
        description='MCP 테스트 회의',
        sync_calendars=True
    )
    print('회의 생성 결과:', result)

asyncio.run(test_meeting())
"
```

### 4. 태스크 생성 테스트
```bash
poetry run python -c "
import asyncio
from datetime import datetime, timedelta
from services.mcp.unified_mcp_manager import UnifiedMCPManager

async def test_task():
    manager = UnifiedMCPManager()
    await manager.initialize()
    
    result = await manager.create_task(
        title='테스트 태스크',
        assignee='소현',
        priority='High',
        due_date=datetime.now() + timedelta(days=7),
        task_type='🐞 Bug'
    )
    print('태스크 생성 결과:', result)

asyncio.run(test_task())
"
```

## 🚀 실행 방법

### 1. 환경 변수 설정
```bash
# .env 파일에 필요한 변수들 추가
cp .env.example .env
# .env 파일을 편집하여 실제 값들 입력
```

### 2. 애플리케이션 실행
```bash
poetry run python run.py
```

## 📊 새로운 기능들

### 1. 통합 회의 생성
- **Notion Board DB**: 회의록 페이지 생성
- **Google Calendar**: 이벤트 생성 및 동기화
- **Discord Event**: 서버 내 이벤트 생성
- **Discord 알림**: 생성 결과 통합 알림

### 2. 개선된 태스크 관리
- **Due Date 필수**: `deadline` 또는 `days` 파라미터 필수
- **Task Type 지원**: 🐞 Bug, 💬 Feature request, 💅 Polish
- **실제 DB 스키마 기반**: 정확한 프로퍼티 매핑

### 3. MCP 워크플로우
- **create_meeting_with_calendars**: 통합 회의 생성
- **create_task_with_due_date**: 태스크 생성 + 마감일
- **sync_meeting_to_calendars**: 회의록 캘린더 동기화
- **notify_meeting_created**: 회의 생성 알림

## ⚠️ 주의사항

1. **Google Calendar API 할당량**: 일일 1,000,000 요청 제한
2. **Discord Rate Limit**: 초당 50 요청 제한
3. **Notion API Rate Limit**: 초당 3 요청 제한
4. **토큰 보안**: `.env` 파일을 `.gitignore`에 추가
5. **이메일 매핑**: `_name_to_email` 함수에서 실제 이메일 주소로 수정 필요

## 🔄 기존 기능과의 호환성

- 기존 Discord 명령어들은 그대로 작동
- MCP 서비스는 기존 서비스와 병행 사용 가능
- 점진적 마이그레이션 지원
