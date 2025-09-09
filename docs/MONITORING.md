# 📊 모니터링 가이드

<div align="center">

**MeetupLoader의 모니터링 시스템 완전 가이드**

[![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-red.svg?style=for-the-badge&logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Grafana-Dashboard-orange.svg?style=for-the-badge&logo=grafana&logoColor=white)](https://grafana.com/)
[![Docker](https://img.shields.io/badge/Docker-Container-blue.svg?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com/)

</div>

---

## 🎯 모니터링 개요

MeetupLoader는 **Prometheus**와 **Grafana**를 사용하여 실시간 모니터링을 제공합니다.

### 📈 수집되는 메트릭

#### 1. 시스템 메트릭
- **CPU 사용률**: 애플리케이션 CPU 사용량
- **메모리 사용량**: RAM 사용량 및 힙 메모리
- **디스크 I/O**: 디스크 읽기/쓰기 성능
- **네트워크 I/O**: 네트워크 트래픽

#### 2. 애플리케이션 메트릭
- **Discord 명령어**: 실행 횟수, 성공률, 응답 시간
- **Notion API**: 호출 횟수, 응답 시간, 에러율
- **MongoDB**: 쿼리 성능, 연결 상태, 인덱스 사용률
- **동기화**: 페이지 동기화 성공률, 처리 시간

#### 3. 비즈니스 메트릭
- **작업 생성**: 일별/주별/월별 작업 생성 수
- **회의 생성**: 회의록 생성 및 참석자 수
- **문서 생성**: 문서 타입별 생성 수
- **사용자 활동**: 활성 사용자 수, 명령어 사용 패턴

---

## 🚀 모니터링 환경 시작

### 1. 개발 환경 (Docker Compose)
```bash
# 전체 모니터링 시스템 시작
./scripts/start-dev.sh

# 또는 직접 실행
docker-compose up -d
```

### 2. 서비스 접속 정보
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9091
- **애플리케이션**: http://localhost:8888
- **메트릭**: http://localhost:9090/metrics

---

## 📊 Grafana 대시보드

### 1. 시스템 대시보드
- **실시간 시스템 상태**: CPU, 메모리, 디스크 사용률
- **네트워크 트래픽**: 인바운드/아웃바운드 트래픽
- **컨테이너 상태**: Docker 컨테이너 리소스 사용량

### 2. 애플리케이션 대시보드
- **Discord 명령어**: 실행률, 응답 시간, 에러율
- **Notion API**: 호출 성능, 에러 추적
- **MongoDB**: 쿼리 성능, 연결 풀 상태

### 3. 비즈니스 대시보드
- **활동 통계**: 일별/주별/월별 활동 추이
- **사용자 분석**: 사용자별 활동 패턴
- **콘텐츠 분석**: 작업/회의/문서 생성 추이

---

## 🔧 Prometheus 설정

### 1. 메트릭 수집 설정
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'meetuploader'
    static_configs:
      - targets: ['meetuploader:9090']
    scrape_interval: 5s
```

### 2. 수집되는 메트릭
```bash
# 메트릭 확인
curl http://localhost:9090/metrics

# 주요 메트릭 예시
discord_commands_total{command="task",status="success"}
notion_api_calls_total{operation="create_page",database="board"}
mongodb_queries_total{operation="find",collection="notion_pages"}
```

---

## 📈 알림 설정

### 1. 임계값 설정
- **에러율 > 5%**: 즉시 알림
- **응답 시간 > 2초**: 경고 알림
- **메모리 사용량 > 80%**: 경고 알림
- **CPU 사용량 > 90%**: 즉시 알림

### 2. 알림 채널
- **Discord**: 봇 상태 알림
- **이메일**: 시스템 관리자
- **Slack**: 팀 알림 (선택사항)

---

## 🛠️ 문제 해결

### 1. 메트릭 수집 문제
```bash
# Prometheus 상태 확인
curl http://localhost:9091/-/healthy

# 메트릭 엔드포인트 확인
curl http://localhost:9090/metrics

# 로그 확인
docker-compose logs prometheus
```

### 2. Grafana 접속 문제
```bash
# Grafana 상태 확인
curl http://localhost:3000/api/health

# 로그 확인
docker-compose logs grafana

# 데이터베이스 초기화
docker-compose down
docker volume rm meetuploader_grafana_data
docker-compose up -d
```

### 3. 메트릭 데이터 문제
```bash
# Prometheus 데이터 초기화
docker-compose down
docker volume rm meetuploader_prometheus_data
docker-compose up -d
```

---

## 📚 고급 설정

### 1. 커스텀 메트릭 추가
```python
from meetuploader.core.metrics import get_metrics_collector

# 커스텀 메트릭 생성
metrics = get_metrics_collector()
metrics.record_custom_metric("custom_operation", "success", 1.0)
```

### 2. 대시보드 커스터마이징
- Grafana에서 새 대시보드 생성
- Prometheus 쿼리로 데이터 시각화
- 알림 규칙 설정

### 3. 외부 모니터링 연동
- **Grafana Cloud**: 클라우드 모니터링
- **DataDog**: APM 및 로그 관리
- **New Relic**: 성능 모니터링

---

## 🎯 모니터링 체크리스트

### ✅ 기본 설정
- [ ] Prometheus 서버 실행
- [ ] Grafana 대시보드 접속
- [ ] 메트릭 수집 확인
- [ ] 알림 설정 완료

### ✅ 성능 모니터링
- [ ] 응답 시간 모니터링
- [ ] 에러율 추적
- [ ] 리소스 사용량 확인
- [ ] 데이터베이스 성능 모니터링

### ✅ 비즈니스 모니터링
- [ ] 사용자 활동 추적
- [ ] 콘텐츠 생성 통계
- [ ] 시스템 사용률 분석
- [ ] 트렌드 분석

---

<div align="center">

**📊 완전한 모니터링 시스템이 준비되었습니다!**

[🚀 빠른 시작](../README.md) • [🔧 배포 가이드](./DEPLOYMENT.md) • [📖 명령어 가이드](./COMMANDS.md)

</div>
