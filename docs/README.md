# 📚 MeetupLoader 문서

<div align="center">

**MeetupLoader의 모든 문서를 한 곳에서 확인하세요**

[![문서](https://img.shields.io/badge/문서-완전한_가이드-blue.svg?style=for-the-badge)](https://github.com/your-repo/meetupLoader)
[![버전](https://img.shields.io/badge/버전-1.0.0-green.svg?style=for-the-badge)](https://github.com/your-repo/meetupLoader)
[![상태](https://img.shields.io/badge/상태-활성_개발-yellow.svg?style=for-the-badge)](https://github.com/your-repo/meetupLoader)

</div>

---

## 🚀 빠른 시작

### [QUICK_START.md](./QUICK_START.md)
**5분 만에 MeetupLoader를 시작하세요!**

- ✅ 환경 설정
- ✅ 의존성 설치
- ✅ 첫 실행
- ✅ 기본 명령어 테스트

---

## 📖 사용자 가이드

### [COMMANDS.md](./COMMANDS.md)
**모든 Discord 명령어 완전 가이드**

- 🤖 **Discord 명령어**: `/task`, `/meeting`, `/fetch`, `/search` 등
- 📊 **통계 명령어**: `/daily_stats`, `/weekly_stats`, `/monthly_stats` 등
- 🔍 **검색 기능**: 유연한 검색, 필터링, 자동완성
- 📈 **분석 도구**: 트렌드 분석, 사용자별 통계

---

## 🔧 개발자 가이드

### [API.md](./API.md)
**REST API 및 웹훅 완전 참조**

- 🌐 **REST API**: 모든 엔드포인트 문서화
- 🔗 **웹훅**: Notion 웹훅 처리
- 📝 **DTO**: 데이터 전송 객체 스키마
- 🔐 **인증**: API 키 및 보안 설정

### [DEPLOYMENT.md](./DEPLOYMENT.md)
**프로덕션 배포 완전 가이드**

- 🐳 **Docker**: 컨테이너화 및 최적화
- ☁️ **Fly.io**: 클라우드 배포
- 🔄 **CI/CD**: GitHub Actions 자동화
- 📊 **모니터링**: Prometheus + Grafana

### [GITHUB_SETUP.md](./GITHUB_SETUP.md)
**GitHub Actions 설정 가이드**

- 🔐 **Secrets 설정**: 환경 변수 구성
- 🚀 **자동 배포**: CI/CD 파이프라인
- 🧪 **테스트**: 자동화된 테스트 실행
- 📈 **모니터링**: 배포 상태 확인

---

## 🏗️ 아키텍처

### 시스템 구조
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discord Bot   │◄──►│  MeetupLoader   │◄──►│   Notion API    │
│                 │    │                 │    │                 │
│ • Slash Commands│    │ • FastAPI       │    │ • Page Creation │
│ • Threads       │    │ • MongoDB       │    │ • Content Sync  │
│ • Messages      │    │ • Prometheus    │    │ • Webhooks      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Monitoring    │
                       │                 │
                       │ • Grafana       │
                       │ • Prometheus    │
                       │ • Fly.io        │
                       └─────────────────┘
```

### 기술 스택
- **Backend**: Python 3.11, FastAPI, asyncio
- **Database**: MongoDB, Motor (async driver)
- **Bot**: Discord.py, Slash Commands
- **Integration**: Notion API, Webhooks
- **Deployment**: Docker, Fly.io
- **Monitoring**: Prometheus, Grafana
- **CI/CD**: GitHub Actions

---

## 📊 모니터링

### 실시간 대시보드
- **시스템 메트릭**: CPU, 메모리, 네트워크
- **애플리케이션 메트릭**: Discord 명령어, Notion API 호출
- **비즈니스 메트릭**: 작업 생성, 회의 수, 문서 수
- **에러 모니터링**: 실시간 에러 추적

### 접속 정보
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9091
- **애플리케이션**: http://localhost:8888
- **메트릭**: http://localhost:9090/metrics

---

## 🛠️ 개발 환경

### 로컬 개발
```bash
# 개발 환경 시작
./scripts/start-dev.sh

# 로그 확인
docker-compose logs -f meetuploader

# 서비스 중지
docker-compose down
```

### 배포
```bash
# Fly.io 배포
fly deploy

# 배포 상태 확인
./scripts/check-deployment.sh
```

---

## 📞 지원

### 문제 해결
1. **로그 확인**: `docker-compose logs -f meetuploader`
2. **상태 확인**: `./scripts/check-deployment.sh`
3. **설정 확인**: `./scripts/check_config.py`

### 기여하기
1. Fork 저장소
2. Feature 브랜치 생성
3. 변경사항 커밋
4. Pull Request 생성

---

<div align="center">

**📚 모든 문서가 준비되었습니다!**

[🚀 빠른 시작하기](./QUICK_START.md) • [📖 명령어 가이드](./COMMANDS.md) • [🔧 배포 가이드](./DEPLOYMENT.md)

</div>