# 🚀 배포 가이드

**MeetupLoader를 프로덕션 환경에 배포하는 방법을 안내합니다.**

## 📋 배포 옵션

### 1. Fly.io (권장)
- **장점**: 간편한 설정, 자동 스케일링, 글로벌 CDN
- **비용**: 무료 티어 제공, 사용량 기반 과금
- **적합**: 중소규모 팀, 빠른 배포

### 2. Docker
- **장점**: 컨테이너화, 환경 일관성
- **비용**: 서버 비용만
- **적합**: 기존 인프라 활용, 커스터마이징

### 3. VPS/클라우드
- **장점**: 완전한 제어, 커스터마이징
- **비용**: 서버 비용
- **적합**: 대규모 팀, 특수 요구사항

## ☁️ Fly.io 배포

### 1. 사전 준비

#### Fly.io CLI 설치
```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Windows
iwr https://fly.io/install.ps1 -useb | iex
```

#### Fly.io 계정 생성
```bash
fly auth signup
# 또는 기존 계정으로 로그인
fly auth login
```

### 2. 애플리케이션 생성

```bash
# 애플리케이션 생성
fly apps create meetuploader

# 설정 파일 생성
fly launch
```

### 3. 환경 변수 설정

```bash
# Discord 설정
fly secrets set DISCORD_TOKEN="your_discord_bot_token"
fly secrets set DISCORD_APP_ID="your_discord_app_id"
fly secrets set DISCORD_GUILD_ID="your_discord_guild_id"
fly secrets set DEFAULT_DISCORD_CHANNEL_ID="your_default_channel_id"

# Notion 설정
fly secrets set NOTION_TOKEN="secret_your_notion_token"
fly secrets set FACTORY_TRACKER_DB_ID="your_factory_tracker_db_id"
fly secrets set BOARD_DB_ID="your_board_db_id"

# MongoDB 설정
fly secrets set MONGODB_URL="mongodb+srv://username:password@cluster.mongodb.net"
fly secrets set MONGODB_DB_NAME="meetuploader"

# 보안 설정
fly secrets set WEBHOOK_SECRET="your_secure_webhook_secret"
```

### 4. 배포 실행

```bash
# 첫 배포
fly deploy

# 업데이트 배포
fly deploy
```

### 5. 배포 확인

```bash
# 상태 확인
fly status

# 로그 확인
fly logs

# 헬스체크
fly open /health
```

## 🐳 Docker 배포

### 1. Dockerfile 빌드

```bash
# 이미지 빌드
docker build -t meetuploader .

# 태그 설정
docker tag meetuploader your-registry/meetuploader:latest
```

### 2. 컨테이너 실행

#### 로컬 실행
```bash
# 환경 변수 파일 사용
docker run --env-file .env -p 8888:8888 meetuploader

# 환경 변수 직접 전달
docker run \
  -e DISCORD_TOKEN="your_token" \
  -e NOTION_TOKEN="your_notion_token" \
  -e MONGODB_URL="mongodb://host.docker.internal:27017" \
  -p 8888:8888 \
  meetuploader
```

#### Docker Compose 사용
```yaml
# docker-compose.yml
version: '3.8'
services:
  meetuploader:
    build: .
    ports:
      - "8888:8888"
    env_file:
      - .env
    depends_on:
      - mongodb
    restart: unless-stopped
    
  mongodb:
    image: mongo:6
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    restart: unless-stopped

volumes:
  mongodb_data:
```

```bash
# 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f meetuploader
```

### 3. 프로덕션 배포

#### Docker Swarm
```bash
# 스택 배포
docker stack deploy -c docker-compose.yml meetuploader

# 서비스 확인
docker service ls
```

#### Kubernetes
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meetuploader
spec:
  replicas: 2
  selector:
    matchLabels:
      app: meetuploader
  template:
    metadata:
      labels:
        app: meetuploader
    spec:
      containers:
      - name: meetuploader
        image: your-registry/meetuploader:latest
        ports:
        - containerPort: 8888
        env:
        - name: DISCORD_TOKEN
          valueFrom:
            secretKeyRef:
              name: meetuploader-secrets
              key: discord-token
        - name: NOTION_TOKEN
          valueFrom:
            secretKeyRef:
              name: meetuploader-secrets
              key: notion-token
        - name: MONGODB_URL
          valueFrom:
            secretKeyRef:
              name: meetuploader-secrets
              key: mongodb-url
```

## 🖥️ VPS/클라우드 배포

### 1. 서버 설정

#### Ubuntu/Debian
```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 3.11 설치
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# Poetry 설치
curl -sSL https://install.python-poetry.org | python3 -

# MongoDB 설치
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
```

### 2. 애플리케이션 배포

```bash
# 저장소 클론
git clone https://github.com/yourusername/meetupLoader.git
cd meetupLoader

# 의존성 설치
poetry install

# 환경 변수 설정
cp env.example .env
nano .env

# 실행
poetry run python run.py
```

### 3. 서비스 등록

#### systemd 서비스
```ini
# /etc/systemd/system/meetuploader.service
[Unit]
Description=MeetupLoader Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/meetupLoader
Environment=PATH=/home/ubuntu/.local/bin:/usr/bin:/bin
ExecStart=/home/ubuntu/.local/bin/poetry run python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 등록
sudo systemctl daemon-reload
sudo systemctl enable meetuploader
sudo systemctl start meetuploader

# 상태 확인
sudo systemctl status meetuploader
```

### 4. 리버스 프록시 설정

#### Nginx
```nginx
# /etc/nginx/sites-available/meetuploader
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 사이트 활성화
sudo ln -s /etc/nginx/sites-available/meetuploader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔧 환경별 설정

### 개발 환경
```bash
# .env.development
DISCORD_TOKEN=dev_token
NOTION_TOKEN=dev_notion_token
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=meetuploader_dev
LOG_LEVEL=DEBUG
```

### 스테이징 환경
```bash
# .env.staging
DISCORD_TOKEN=staging_token
NOTION_TOKEN=staging_notion_token
MONGODB_URL=mongodb+srv://staging:password@cluster.mongodb.net
MONGODB_DB_NAME=meetuploader_staging
LOG_LEVEL=INFO
```

### 프로덕션 환경
```bash
# .env.production
DISCORD_TOKEN=prod_token
NOTION_TOKEN=prod_notion_token
MONGODB_URL=mongodb+srv://prod:password@cluster.mongodb.net
MONGODB_DB_NAME=meetuploader_prod
LOG_LEVEL=WARNING
```

## 📊 모니터링 설정

### 1. 로그 관리

#### 로그 로테이션
```bash
# /etc/logrotate.d/meetuploader
/home/ubuntu/meetupLoader/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload meetuploader
    endscript
}
```

### 2. 헬스체크 설정

#### Uptime Robot
1. [Uptime Robot](https://uptimerobot.com) 가입
2. "Add New Monitor" 클릭
3. Monitor Type: HTTP(s)
4. URL: `https://your-domain.com/health`
5. Monitoring Interval: 5분

### 3. 알림 설정

#### Discord 웹훅
```bash
# Discord 채널에 웹훅 생성
# 웹훅 URL을 환경 변수에 추가
WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-url
```

## 🔐 보안 설정

### 1. 방화벽 설정

#### UFW (Ubuntu)
```bash
# 기본 정책 설정
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH 허용
sudo ufw allow ssh

# HTTP/HTTPS 허용
sudo ufw allow 80
sudo ufw allow 443

# 방화벽 활성화
sudo ufw enable
```

### 2. SSL 인증서

#### Let's Encrypt
```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx -y

# 인증서 발급
sudo certbot --nginx -d your-domain.com

# 자동 갱신 설정
sudo crontab -e
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. 환경 변수 보안

```bash
# 민감한 정보는 별도 파일로 관리
sudo chmod 600 /home/ubuntu/meetupLoader/.env
sudo chown ubuntu:ubuntu /home/ubuntu/meetupLoader/.env
```

## 🚨 트러블슈팅

### 일반적인 문제들

#### 1. 메모리 부족
```bash
# 메모리 사용량 확인
free -h

# 스왑 파일 생성
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 2. 포트 충돌
```bash
# 포트 사용 확인
sudo netstat -tulpn | grep :8888

# 프로세스 종료
sudo kill -9 PID
```

#### 3. 권한 문제
```bash
# 파일 권한 확인
ls -la /home/ubuntu/meetupLoader/

# 권한 수정
sudo chown -R ubuntu:ubuntu /home/ubuntu/meetupLoader/
```

### 로그 분석

#### 에러 로그 확인
```bash
# 실시간 로그
tail -f /home/ubuntu/meetupLoader/logs/meetuploader_*.log

# 에러만 필터링
grep "ERROR" /home/ubuntu/meetupLoader/logs/meetuploader_*.log

# 특정 시간대
grep "2025-09-09 13:" /home/ubuntu/meetupLoader/logs/meetuploader_*.log
```

## 📈 성능 최적화

### 1. 리소스 모니터링

#### htop 설치
```bash
sudo apt install htop -y
htop
```

#### 시스템 모니터링
```bash
# CPU 사용률
top -p $(pgrep -f "python run.py")

# 메모리 사용률
ps aux --sort=-%mem | head -10

# 디스크 사용률
df -h
```

### 2. 데이터베이스 최적화

#### MongoDB 인덱스 확인
```bash
# MongoDB 연결
mongosh

# 인덱스 확인
db.notion_pages.getIndexes()

# 쿼리 성능 분석
db.notion_pages.find({"title": "test"}).explain("executionStats")
```

### 3. 애플리케이션 최적화

#### 프로세스 모니터링
```bash
# 프로세스 상태 확인
ps aux | grep python

# 메모리 사용량 모니터링
watch -n 1 'ps aux --sort=-%mem | head -5'
```

---

**배포가 완료되었습니다! 이제 MeetupLoader를 프로덕션에서 사용할 수 있습니다.** 🎉
