# Playbook 01: CareerOS API Down

**증상:** CareerOS API 호출 실패, 온보딩이 특정 단계에서 멈춤, Discord 사용자에게 에러 메시지 출력.

**관련 메트릭:** `errors_total{service="careeros"}` 급증

---

## 진단

### 1. dinobot 헬스 확인
```bash
curl https://<dinobot-host>/health
```

봇 자체가 살아있으면 CareerOS 연결 문제.

### 2. CareerOS 상태 확인
```bash
curl http://careeros:8080/actuator/health
# 또는
curl https://<careeros-host>/health
```

### 3. dinobot 로그에서 httpx 타임아웃 확인
```bash
fly logs --app dinobot | grep "careeros\|HTTPStatusError\|ConnectTimeout"
```

찾을 수 있는 에러 패턴:
```
httpx.ConnectTimeout: ...
httpx.HTTPStatusError: 502 Bad Gateway
CareerOS resume upload returned no resumeId
```

### 4. 메트릭 대시보드 확인
```bash
curl https://<dinobot-host>/metrics/dashboard
# errors_total{service="careeros"} 값 확인
```

---

## 해결

### CareerOS 일시 장애 (5xx)

온보딩 중인 사용자에게 안내 메시지가 자동 전송된다 (`try/except` 처리됨):
```
CareerOS에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.
```

사용자는 현재 단계를 다시 입력하거나 `/restart_onboard`로 재시작할 수 있다.

### CareerOS 장기 중단

1. CareerOS 팀에 알림
2. 온보딩을 일시 중단하려면 Discord 채널에 공지 게시
3. 다이제스트 웹훅이 실패할 경우 — CareerOS가 재시도 로직을 보유하고 있으므로 복구 후 자동 재전송

### dinobot이 잘못된 CAREEROS_API_URL을 참조하는 경우
```bash
fly secrets list --app dinobot
fly secrets set CAREEROS_API_URL=http://careeros:8080 --app dinobot
fly deploy --app dinobot
```

---

## 재확인

```bash
# 온디맨드 다이제스트 트리거 테스트
curl -X POST https://<dinobot-host>/mcp/careeros/send_digest \
  -H "Content-Type: application/json" \
  -d '{"channel_type": "discord"}'

# 다이제스트 상태 확인
curl https://<dinobot-host>/mcp/careeros/digest_status
```

---

## 에스컬레이션

CareerOS API가 30분 이상 응답하지 않으면 CareerOS 팀 온콜에 연락.
