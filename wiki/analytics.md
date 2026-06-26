# Analytics & Metrics

dinobot은 Prometheus 클라이언트 라이브러리(`prometheus_client`)를 사용해 메트릭을 수집하고, `/metrics/dashboard` 엔드포인트로 실시간 대시보드를 제공한다.

---

## MetricsCollector

`src/core/metrics.py`의 `MetricsCollector` 클래스가 모든 메트릭을 관리한다.

글로벌 싱글턴: `from src.core.metrics import metrics_collector`

---

## Prometheus 메트릭 목록

### Discord 메트릭

| 메트릭 이름 | 타입 | 레이블 | 설명 |
|------------|------|--------|------|
| `discord_commands_total` | Counter | `command`, `user`, `status` | 실행된 슬래시 커맨드 총 수 |
| `discord_command_duration_seconds` | Histogram | `command` | 커맨드 실행 소요 시간 |
| `discord_threads_created_total` | Counter | `page_type` | 생성된 Discord 스레드 수 |

### Notion API 메트릭

| 메트릭 이름 | 타입 | 레이블 | 설명 |
|------------|------|--------|------|
| `notion_api_calls_total` | Counter | `operation`, `database`, `status` | Notion API 호출 수 |
| `notion_api_duration_seconds` | Histogram | `operation` | Notion API 응답 시간 |
| `notion_pages_synced_total` | Gauge | `database` | 동기화된 Notion 페이지 수 |

### MongoDB 메트릭

| 메트릭 이름 | 타입 | 레이블 | 설명 |
|------------|------|--------|------|
| `mongodb_queries_total` | Counter | `operation`, `collection`, `status` | MongoDB 쿼리 수 |
| `mongodb_query_duration_seconds` | Histogram | `operation`, `collection` | MongoDB 쿼리 소요 시간 |

### 비즈니스 메트릭

| 메트릭 이름 | 타입 | 레이블 | 설명 |
|------------|------|--------|------|
| `active_users_total` | Gauge | — | 현재 활성 사용자 수 |
| `meetings_created_total` | Counter | `participants_count` | 생성된 회의 수 |
| `tasks_created_total` | Counter | `priority`, `person` | 생성된 태스크 수 |
| `documents_created_total` | Counter | `doc_type` | 생성된 문서 수 |
| `errors_total` | Counter | `service`, `error_type` | 서비스별 에러 수 |

---

## 메트릭 기록 API

```python
# Discord 커맨드 실행 기록
metrics_collector.record_discord_command("task", "user123", "success", 0.35)

# Notion API 호출 기록
metrics_collector.record_notion_api_call("query", "factory_tracker", "success", 0.82)

# MongoDB 쿼리 기록
metrics_collector.record_mongodb_query("find", "notion_pages", "success", 0.05)

# 에러 기록
metrics_collector.record_error("notion_service", "rate_limit")
```

---

## 엔드포인트

| 경로 | 설명 |
|------|------|
| `GET /metrics/dashboard` | 실시간 메트릭 대시보드 (HTML/JSON) |
| `GET /metrics` | Prometheus 스크래핑 엔드포인트 (`:9090`) |

---

## 알림 임계값 (권장)

| 메트릭 | 임계값 | 행동 |
|--------|--------|------|
| `errors_total{service="careeros"}` | 5분 내 > 10 | CareerOS API 장애 플레이북 참조 |
| `notion_api_calls_total{status="error"}` | 5분 내 > 5 | Notion rate limit 확인 |
| `discord_command_duration_seconds` p99 | > 3s | Discord 응답 지연 조사 |
| `notion_pages_synced_total` | 1시간 내 변화 없음 | 동기화 중단 플레이북 참조 |

Grafana 대시보드 설정은 [docs/MONITORING.md](../docs/MONITORING.md) 참조.
