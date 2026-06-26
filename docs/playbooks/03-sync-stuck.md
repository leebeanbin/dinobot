# Playbook 03: Notion Sync Stuck

**증상:** Notion 페이지 변경사항이 Discord에 반영되지 않음. `GET /sync/status`에서 `is_running: false` 또는 `recent_sync: 0`.

---

## 진단

### 1. 동기화 상태 확인
```bash
curl https://<dinobot-host>/sync/status
```

응답 예시 (정상):
```json
{
  "is_running": true,
  "total_pages": 42,
  "recent_sync": 38,
  "sync_interval": 600,
  "last_check": "2026-06-26T08:00:00"
}
```

이상 징후:
- `is_running: false` — 동기화 루프 중단
- `recent_sync: 0` — 최근 1시간 내 동기화 없음
- `total_pages: 0` — MongoDB에 페이지 없음

### 2. 로그에서 동기화 에러 확인
```bash
fly logs --app dinobot | grep -E "sync|notion|mongodb|rate_limit|동기화"
```

찾을 수 있는 에러 패턴:
```
동기화 실패: ...
Notion API rate limit
MongoDB connection error
동기화 루프 오류
```

### 3. MongoDB 연결 확인
```bash
fly logs --app dinobot | grep -E "mongodb|Motor|connect_database"
```

### 4. Notion API rate limit 확인

Notion API는 평균 3 req/s로 제한된다. 로그에서 `429 Too Many Requests` 패턴 확인:
```bash
fly logs --app dinobot | grep "429\|rate_limit\|rate limit"
```

---

## 해결

### 즉시 수동 동기화 실행

```bash
curl -X POST https://<dinobot-host>/sync/manual
```

응답:
```json
{
  "success": true,
  "message": "동기화가 완료되었습니다.",
  "total_pages": 42
}
```

### 동기화 루프 중단 (is_running: false)

프로세스 재시작으로 루프 재개:
```bash
fly restart --app dinobot
```

재시작 후 상태 재확인:
```bash
curl https://<dinobot-host>/sync/status
```

### MongoDB 연결 문제

1. MongoDB Atlas 상태 확인 (https://status.mongodb.com)
2. `MONGODB_URI` secret 확인:
   ```bash
   fly secrets list --app dinobot
   ```
3. 연결 문자열 재설정:
   ```bash
   fly secrets set MONGODB_URI=<uri> --app dinobot
   fly deploy --app dinobot
   ```

### Notion API Rate Limit

동기화 간격이 너무 짧거나 페이지 수가 많은 경우:
- `SyncService.synchronization_interval_seconds`를 늘린다 (기본 600초).
- 동시 처리 세마포어(`asyncio.Semaphore(5)`)를 줄인다.
- 일시적으로 수동 동기화만 사용: 루프 중지 후 필요 시 `POST /sync/manual`.

---

## 재확인

```bash
# 동기화 상태 재확인
curl https://<dinobot-host>/sync/status

# 메트릭에서 notion_pages_synced_total 확인
curl https://<dinobot-host>/metrics/dashboard
```

---

## 예방

- `notion_pages_synced_total` Gauge를 Grafana에서 모니터링.
- 1시간 이상 변화 없으면 알림 트리거.
- Notion API 토큰 만료 여부 주기적 확인 (`NOTION_TOKEN` secret).
