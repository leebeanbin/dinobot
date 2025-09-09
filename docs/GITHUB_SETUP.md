# 🔧 GitHub Actions 설정 가이드

## 📋 필요한 GitHub Secrets

GitHub 저장소에서 다음 Secrets를 설정해야 합니다:

### 1. GitHub Secrets 추가 방법

1. **GitHub 저장소** → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. 각 Secret 추가:

### 2. Discord 설정 (테스트용)
```
DISCORD_TOKEN_TEST=your_test_discord_bot_token
DISCORD_GUILD_ID_TEST=your_test_discord_guild_id
```

### 3. Notion 설정 (테스트용)
```
NOTION_API_KEY_TEST=your_test_notion_api_key
FACTORY_TRACKER_DB_ID_TEST=your_test_factory_tracker_db_id
BOARD_DB_ID_TEST=your_test_board_db_id
```

### 4. Fly.io 설정 (배포용)
```
FLY_API_TOKEN=your_fly_io_api_token
FLY_APP_NAME=meetuploader
```

## 🚀 Fly.io API 토큰 생성

1. **Fly.io CLI 설치:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Fly.io 로그인:**
   ```bash
   fly auth login
   ```

3. **API 토큰 생성:**
   ```bash
   fly auth token
   ```

4. **앱 생성 (아직 없다면):**
   ```bash
   fly apps create meetuploader
   ```

## 🔐 환경 변수 설정

### Fly.io에 환경 변수 설정:
```bash
# Discord 설정
fly secrets set DISCORD_TOKEN="your_production_discord_token"
fly secrets set DISCORD_GUILD_ID="your_production_discord_guild_id"

# Notion 설정
fly secrets set NOTION_API_KEY="your_production_notion_api_key"
fly secrets set FACTORY_TRACKER_DB_ID="your_production_factory_tracker_db_id"
fly secrets set BOARD_DB_ID="your_production_board_db_id"

# MongoDB 설정
fly secrets set MONGODB_URI="mongodb+srv://username:password@cluster.mongodb.net/meetuploader"

# 기타 설정
fly secrets set LOG_LEVEL="INFO"
fly secrets set TIMEZONE="Asia/Seoul"
```

## 📊 모니터링 설정

### Grafana Cloud 설정 (선택사항):
1. [Grafana Cloud](https://grafana.com/products/cloud/) 가입
2. 무료 플랜 선택
3. Prometheus 데이터소스 추가
4. 대시보드 임포트

### 로컬 모니터링:
```bash
# 개발 환경 시작
./scripts/start-dev.sh

# 접속 정보:
# - MeetupLoader: http://localhost:8888
# - Grafana: http://localhost:3000 (admin/admin123)
# - Prometheus: http://localhost:9091
```

## 🔄 CI/CD 파이프라인 동작

1. **코드 푸시** → GitHub Actions 트리거
2. **코드 품질 검사** → Lint, Type Check, Security Check
3. **테스트 실행** → Unit Tests, Integration Tests
4. **Docker 빌드** → 이미지 생성 및 테스트
5. **Fly.io 배포** → 자동 배포 (main 브랜치만)
6. **헬스체크** → 배포 성공 확인

## 🚨 문제 해결

### Fly.io 배포 실패 시:
```bash
# 로그 확인
fly logs

# 앱 상태 확인
fly status

# 수동 배포
fly deploy
```

### GitHub Actions 실패 시:
1. **Actions** 탭에서 실패한 워크플로우 확인
2. 로그에서 구체적인 오류 메시지 확인
3. Secrets 설정 확인
4. 환경 변수 값 검증

## 📈 모니터링 확인

### 배포 후 확인사항:
1. **애플리케이션 헬스체크:**
   ```bash
   curl https://meetuploader.fly.dev/health
   ```

2. **메트릭 엔드포인트:**
   ```bash
   curl https://meetuploader.fly.dev/metrics
   ```

3. **Discord 봇 상태:**
   - Discord에서 `/help` 명령어 테스트
   - `/status` 명령어로 시스템 상태 확인
