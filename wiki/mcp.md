# MCP Server

dinobot은 FastAPI 기반 MCP(Model Context Protocol) 서버를 내장한다. Claude Desktop 또는 다른 MCP 클라이언트가 `/mcp/careeros/*` 엔드포인트를 호출하여 dinobot 기능을 제어할 수 있다.

소스: `mcp_server/careeros_tools.py`

---

## MCP 툴 목록

### POST /mcp/careeros/configure_channel

Discord 또는 Telegram 알림 채널을 활성화/비활성화한다.

**요청:**
```json
{
  "channel_type": "discord",  // "discord" | "telegram"
  "enabled": true
}
```

**동작:** MongoDB `careeros_mcp_config` 컬렉션에 `{ channel.discord: true }` 형태로 저장. 프로세스 재시작 후에도 유지.

**응답:**
```json
{
  "channel_type": "discord",
  "enabled": true
}
```

---

### POST /mcp/careeros/send_digest

온디맨드 일일 공고 다이제스트를 트리거한다.

**요청:**
```json
{
  "channel_type": "discord",
  "user_id": 42  // null이면 전체 사용자
}
```

**동작:** `CareerOSApiClient.trigger_digest(user_id)` 호출 → CareerOS DailyDigestAgent 실행.

**응답:**
```json
{
  "triggered": true,
  "channel_type": "discord",
  "detail": { ... }  // CareerOS 반환값
}
```

**에러:** CareerOS API 실패 시 `HTTP 502 Bad Gateway`.

---

### GET /mcp/careeros/digest_status

마지막 다이제스트 실행 메타데이터와 채널 활성화 상태를 반환한다.

**응답:**
```json
{
  "careeros": {
    "lastRunAt": "2026-06-26T08:00:00Z",
    "sentCount": 5
  },
  "channels": {
    "discord": true,
    "telegram": false
  }
}
```

---

## Claude Desktop 연동 설정

`~/.claude/claude_desktop_config.json` 에 추가:

```json
{
  "mcpServers": {
    "dinobot": {
      "command": "curl",
      "args": ["-s", "http://localhost:8889/mcp/careeros/digest_status"],
      "type": "http",
      "baseUrl": "http://localhost:8889"
    }
  }
}
```

Fly.io 배포 환경에서는 `localhost:8889`를 배포 URL로 교체한다.

자세한 설정은 [docs/MCP_SETUP_GUIDE.md](../docs/MCP_SETUP_GUIDE.md) 참조.

---

## 내부 구조

MCP 라우터는 FastAPI `APIRouter`로 구현되어 있으며 `prefix="/mcp/careeros"`로 등록된다.

```python
careeros_mcp_router = APIRouter(prefix="/mcp/careeros", tags=["careeros-mcp"])
```

채널 설정 영속화는 MongoDB `careeros_mcp_config` 컬렉션을 사용한다. Redis나 별도 설정 파일이 필요 없다.
