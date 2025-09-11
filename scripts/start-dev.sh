#!/bin/bash

# DinoBot 개발 환경 시작 스크립트

echo "🚀 DinoBot 개발 환경 시작 중..."

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."

# 의존성 설치
echo "📦 의존성 설치 중..."
poetry install

# Docker Compose로 서비스 시작
echo "🐳 Docker Compose로 서비스 시작 중..."
docker-compose up -d

# 서비스 상태 확인
echo "⏳ 서비스 시작 대기 중..."
sleep 30

# 헬스체크
echo "🔍 서비스 상태 확인 중..."

# DinoBot 헬스체크
if curl -f http://localhost:8888/health > /dev/null 2>&1; then
    echo "✅ DinoBot: 정상"
else
    echo "❌ DinoBot: 오류"
fi

# Prometheus 헬스체크
if curl -f http://localhost:9091/-/healthy > /dev/null 2>&1; then
    echo "✅ Prometheus: 정상"
else
    echo "❌ Prometheus: 오류"
fi

# Grafana 헬스체크
if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "✅ Grafana: 정상"
else
    echo "❌ Grafana: 오류"
fi

echo ""
echo "🎉 개발 환경이 시작되었습니다!"
echo ""
echo "📊 서비스 접속 정보:"
echo "  - DinoBot API: http://localhost:8888"
echo "  - DinoBot Metrics: http://localhost:9090/metrics"
echo "  - Prometheus: http://localhost:9091"
echo "  - Grafana: http://localhost:3000 (admin/admin123)"
echo "  - MongoDB: mongodb://localhost:27017"
echo ""
echo "📝 로그 확인:"
echo "  docker-compose logs -f meetuploader"
echo ""
echo "🛑 서비스 중지:"
echo "  docker-compose down"
