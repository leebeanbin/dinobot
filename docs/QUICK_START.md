# 🚀 빠른 시작 가이드

**5분 만에 DinoBot를 시작하세요!**

## 📋 사전 준비

### 1. 시스템 요구사항
- Python 3.11+
- MongoDB 6.0+
- Discord 서버 관리자 권한
- Notion 계정

### 2. 필요한 토큰들
- Discord 봇 토큰
- Notion 통합 토큰
- MongoDB 연결 문자열

## ⚡ 5분 설정

### 1️⃣ **저장소 클론**
```bash
git clone https://github.com/yourusername/meetupLoader.git
cd meetupLoader
```

### 2️⃣ **의존성 설치**
```bash
# Poetry 설치 (없는 경우)
curl -sSL https://install.python-poetry.org | python3 -

# 프로젝트 의존성 설치
poetry install
```

### 3️⃣ **환경 변수 설정**
```bash
# 환경 변수 파일 생성
cp env.example .env

# .env 파일 편집
nano .env
```

**필수 환경 변수:**
```bash
DISCORD_TOKEN=your_discord_bot_token
NOTION_TOKEN=secret_your_notion_token
MONGODB_URL=mongodb://localhost:27017
```

### 4️⃣ **MongoDB 설정**
```bash
# Docker로 로컬 MongoDB 실행
docker run -d -p 27017:27017 --name mongodb mongo:6
```

### 5️⃣ **실행**
```bash
poetry run python run.py
```

## 🤖 Discord 봇 설정

### 1. Discord Developer Portal
1. [Discord Developer Portal](https://discord.com/developers/applications) 접속
2. "New Application" 클릭
3. 애플리케이션 이름 입력
4. "Bot" 탭으로 이동
5. "Add Bot" 클릭
6. 토큰 복사

### 2. 봇 권한 설정
1. "OAuth2" > "URL Generator" 이동
2. Scopes: `bot`, `applications.commands` 선택
3. Bot Permissions: `Send Messages`, `Use Slash Commands`, `Manage Threads` 선택
4. 생성된 URL로 봇 초대

### 3. 서버에 봇 초대
- 생성된 URL을 브라우저에서 열기
- 서버 선택 후 "Authorize" 클릭

## 📝 Notion 설정

### 1. 통합 생성
1. [Notion 통합](https://www.notion.so/my-integrations) 접속
2. "New integration" 클릭
3. 이름 입력 (예: "DinoBot Bot")
4. 워크스페이스 선택
5. "Submit" 클릭
6. 토큰 복사

### 2. 데이터베이스 공유
1. 사용할 Notion 데이터베이스 열기
2. 우상단 "Share" 클릭
3. "Invite"에서 생성한 통합 선택
4. "Invite" 클릭

### 3. 데이터베이스 ID 복사
1. 데이터베이스 URL에서 ID 추출
2. `https://notion.so/your-workspace/DATABASE_ID?v=...`
3. DATABASE_ID 부분을 복사

## 🎮 첫 번째 명령어

### Task 생성
```
/task person:홍길동 name:"첫 번째 작업" priority:높음
```

### 회의록 생성
```
/meeting title:"팀 미팅" participants:홍길동,김영희
```

### 통계 확인
```
/daily_stats
```

## ✅ 확인사항

### 1. 봇이 온라인인지 확인
- Discord에서 봇 상태 확인
- "온라인" 표시되어야 함

### 2. 슬래시 명령어 작동 확인
- `/` 입력 시 명령어 목록 표시
- 명령어 실행 시 응답 확인

### 3. Notion 페이지 생성 확인
- Notion에서 새 페이지 생성 확인
- Discord 스레드 생성 확인

## 🔧 문제 해결

### 봇이 응답하지 않는 경우
1. 봇 토큰 확인
2. 봇 권한 확인
3. 서버에 봇이 초대되었는지 확인

### Notion 페이지가 생성되지 않는 경우
1. Notion 토큰 확인
2. 데이터베이스 공유 확인
3. 데이터베이스 ID 확인

### MongoDB 연결 오류
1. MongoDB 서비스 실행 확인
2. 연결 문자열 확인
3. 방화벽 설정 확인

## 📞 지원

문제가 발생하면:
- [GitHub Issues](https://github.com/yourusername/meetupLoader/issues)
- [Discord 서버](https://discord.gg/your-server)

---

**축하합니다! DinoBot가 성공적으로 설정되었습니다!** 🎉
