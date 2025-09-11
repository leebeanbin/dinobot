#!/bin/bash

# DinoBot 배포 상태 확인 스크립트

echo "🔍 DinoBot 배포 상태 확인 중..."

# Fly.io 앱 이름 (환경 변수에서 가져오거나 기본값 사용)
APP_NAME=${FLY_APP_NAME:-meetuploader}

echo "📊 앱 정보: $APP_NAME"

# 1. Fly.io 앱 상태 확인
echo "1️⃣ Fly.io 앱 상태 확인..."
if command -v fly &> /dev/null; then
    fly status --app $APP_NAME
else
    echo "❌ Fly.io CLI가 설치되지 않았습니다."
    echo "   설치: curl -L https://fly.io/install.sh | sh"
fi

echo ""

# 2. 헬스체크
echo "2️⃣ 애플리케이션 헬스체크..."
HEALTH_URL="https://$APP_NAME.fly.dev/health"
if curl -f -s "$HEALTH_URL" > /dev/null; then
    echo "✅ 헬스체크 성공: $HEALTH_URL"
else
    echo "❌ 헬스체크 실패: $HEALTH_URL"
fi

echo ""

# 3. 메트릭 엔드포인트 확인
echo "3️⃣ 메트릭 엔드포인트 확인..."
METRICS_URL="https://$APP_NAME.fly.dev/metrics"
if curl -f -s "$METRICS_URL" | head -5; then
    echo "✅ 메트릭 엔드포인트 정상: $METRICS_URL"
else
    echo "❌ 메트릭 엔드포인트 실패: $METRICS_URL"
fi

echo ""

# 4. 최근 로그 확인
echo "4️⃣ 최근 로그 확인..."
if command -v fly &> /dev/null; then
    echo "📋 최근 로그 (마지막 10줄):"
    fly logs --app $APP_NAME | tail -10
else
    echo "❌ Fly.io CLI가 설치되지 않았습니다."
fi

echo ""
echo "🎉 배포 상태 확인 완료!"
