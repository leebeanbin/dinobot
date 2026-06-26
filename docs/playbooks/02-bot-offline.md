# Playbook 02: Bot Offline

**증상:** Discord 서버에서 dinobot이 오프라인 상태로 표시됨. 슬래시 커맨드가 응답하지 않음.

---

## 진단

### 1. FastAPI 서버는 살아있는지 확인
```bash
curl https://<dinobot-host>/health
```

- HTTP 200 응답 → FastAPI는 정상. Discord Bot 태스크만 중단된 상태.
- 연결 거부 → 전체 프로세스 크래시.

### 2. Fly.io 인스턴스 상태 확인
```bash
fly status --app dinobot
fly instances list --app dinobot
```

### 3. 로그에서 asyncio 루프 크래시 확인
```bash
fly logs --app dinobot | grep -E "discord|asyncio|bot|CancelledError|Exception"
```

찾을 수 있는 에러 패턴:
```
discord.errors.LoginFailure: Improper token
discord.errors.PrivilegedIntentsRequired
asyncio.CancelledError
Task exception was never retrieved
```

### 4. Discord Gateway 연결 상태
```bash
fly logs --app dinobot | grep "on_ready\|Logged in as\|Disconnected"
```

---

## 해결

### Bot 태스크만 중단 (FastAPI 정상)

프로세스를 재시작하면 `create_task(bot.start())` 재실행:
```bash
fly restart --app dinobot
```

재시작 후 확인:
```bash
fly logs --app dinobot | grep "Logged in as"
# "Logged in as DinoBot#XXXX" 로그 확인
```

### 전체 프로세스 크래시

```bash
fly restart --app dinobot
fly logs --app dinobot --tail
```

### Discord Token 문제 (`LoginFailure`)
```bash
fly secrets list --app dinobot
# DISCORD_TOKEN 존재 확인

fly secrets set DISCORD_TOKEN=<new_token> --app dinobot
fly deploy --app dinobot
```

### Intent 권한 부족 (`PrivilegedIntentsRequired`)

[Discord Developer Portal](https://discord.com/developers/applications)에서:
1. 해당 앱 → Bot 설정
2. Privileged Gateway Intents에서 필요한 Intent 활성화
3. `fly restart --app dinobot`

---

## 재확인

Discord 서버에서 `/health` 또는 `/onboard` 커맨드가 응답하면 복구 완료.

```bash
# FastAPI 헬스
curl https://<dinobot-host>/health

# Bot 로그인 확인
fly logs --app dinobot | grep "Logged in"
```

---

## 재발 방지

- `/health` 엔드포인트에서 Discord Bot Gateway 연결 상태를 체크하도록 개선 고려.
- Prometheus `errors_total{service="discord"}` 메트릭 알림 설정.
- Fly.io 자동 재시작 정책 (`restart_policy = "always"`) 설정 확인 (`fly.toml`).
