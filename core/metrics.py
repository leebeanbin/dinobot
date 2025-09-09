"""
Prometheus 메트릭 수집 모듈
- 시스템 메트릭
- 애플리케이션 메트릭
- 비즈니스 메트릭
"""

from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry
import time
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    """메트릭 수집기 클래스"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self._init_metrics()
    
    def _init_metrics(self):
        """메트릭 초기화"""
        
        # Discord 관련 메트릭
        self.discord_commands = Counter(
            'discord_commands_total',
            'Total Discord commands executed',
            ['command', 'user', 'status'],
            registry=self.registry
        )
        
        self.discord_command_duration = Histogram(
            'discord_command_duration_seconds',
            'Discord command execution time',
            ['command'],
            registry=self.registry
        )
        
        # Notion API 관련 메트릭
        self.notion_api_calls = Counter(
            'notion_api_calls_total',
            'Total Notion API calls',
            ['operation', 'database', 'status'],
            registry=self.registry
        )
        
        self.notion_api_duration = Histogram(
            'notion_api_duration_seconds',
            'Notion API call duration',
            ['operation'],
            registry=self.registry
        )
        
        # MongoDB 관련 메트릭
        self.mongodb_queries = Counter(
            'mongodb_queries_total',
            'Total MongoDB queries',
            ['operation', 'collection', 'status'],
            registry=self.registry
        )
        
        self.mongodb_query_duration = Histogram(
            'mongodb_query_duration_seconds',
            'MongoDB query duration',
            ['operation', 'collection'],
            registry=self.registry
        )
        
        # 시스템 메트릭
        self.active_users = Gauge(
            'active_users_total',
            'Number of active users',
            registry=self.registry
        )
        
        self.notion_pages_synced = Gauge(
            'notion_pages_synced_total',
            'Total Notion pages synced',
            ['database'],
            registry=self.registry
        )
        
        self.discord_threads_created = Counter(
            'discord_threads_created_total',
            'Total Discord threads created',
            ['page_type'],
            registry=self.registry
        )
        
        # 에러 메트릭
        self.errors_total = Counter(
            'errors_total',
            'Total errors',
            ['service', 'error_type'],
            registry=self.registry
        )
        
        # 비즈니스 메트릭
        self.meetings_created = Counter(
            'meetings_created_total',
            'Total meetings created',
            ['participants_count'],
            registry=self.registry
        )
        
        self.tasks_created = Counter(
            'tasks_created_total',
            'Total tasks created',
            ['priority', 'person'],
            registry=self.registry
        )
        
        self.documents_created = Counter(
            'documents_created_total',
            'Total documents created',
            ['doc_type'],
            registry=self.registry
        )
    
    def record_discord_command(self, command: str, user: str, status: str, duration: float):
        """Discord 명령어 실행 기록"""
        self.discord_commands.labels(
            command=command,
            user=user,
            status=status
        ).inc()
        
        self.discord_command_duration.labels(
            command=command
        ).observe(duration)
    
    def record_notion_api_call(self, operation: str, database: str, status: str, duration: float):
        """Notion API 호출 기록"""
        self.notion_api_calls.labels(
            operation=operation,
            database=database,
            status=status
        ).inc()
        
        self.notion_api_duration.labels(
            operation=operation
        ).observe(duration)
    
    def record_mongodb_query(self, operation: str, collection: str, status: str, duration: float):
        """MongoDB 쿼리 기록"""
        self.mongodb_queries.labels(
            operation=operation,
            collection=collection,
            status=status
        ).inc()
        
        self.mongodb_query_duration.labels(
            operation=operation,
            collection=collection
        ).observe(duration)
    
    def record_error(self, service: str, error_type: str):
        """에러 기록"""
        self.errors_total.labels(
            service=service,
            error_type=error_type
        ).inc()
    
    def update_active_users(self, count: int):
        """활성 사용자 수 업데이트"""
        self.active_users.set(count)
    
    def update_notion_pages_synced(self, database: str, count: int):
        """동기화된 Notion 페이지 수 업데이트"""
        self.notion_pages_synced.labels(
            database=database
        ).set(count)
    
    def record_discord_thread_created(self, page_type: str):
        """Discord 스레드 생성 기록"""
        self.discord_threads_created.labels(
            page_type=page_type
        ).inc()
    
    def record_meeting_created(self, participants_count: int):
        """회의 생성 기록"""
        self.meetings_created.labels(
            participants_count=str(participants_count)
        ).inc()
    
    def record_task_created(self, priority: str, person: str):
        """작업 생성 기록"""
        self.tasks_created.labels(
            priority=priority,
            person=person
        ).inc()
    
    def record_document_created(self, doc_type: str):
        """문서 생성 기록"""
        self.documents_created.labels(
            doc_type=doc_type
        ).inc()
    
    def start_metrics_server(self, port: int = 9090):
        """메트릭 서버 시작"""
        try:
            start_http_server(port, registry=self.registry)
            logger.info(f"📊 Prometheus 메트릭 서버 시작: http://localhost:{port}/metrics")
        except Exception as e:
            logger.error(f"❌ 메트릭 서버 시작 실패: {e}")

# 전역 메트릭 수집기 인스턴스
metrics_collector = MetricsCollector()

def get_metrics_collector() -> MetricsCollector:
    """메트릭 수집기 인스턴스 반환"""
    return metrics_collector
