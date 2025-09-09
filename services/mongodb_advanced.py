"""
MongoDB 고급 활용 서비스
- 집계 파이프라인을 통한 복잡한 데이터 분석
- 실시간 데이터 스트리밍 및 Change Streams
- 자동 데이터 정리 및 아카이빙
- 성능 최적화 및 인덱스 관리
- 데이터 백업 및 복구
"""

from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
import asyncio
from pymongo import DESCENDING, ASCENDING
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorChangeStream

from core.config import settings
from core.logger import get_logger, logger_manager
from core.database import mongodb_connection
from core.exceptions import DatabaseOperationException, safe_execution
from core.decorators import track_mongodb_query
from models.dtos import (
    CommandExecutionMetricDTO,
    APICallMetricDTO,
    CachePerformanceMetricDTO,
    SystemStatusDTO,
)

# Module logger
logger = get_logger("services.mongodb_advanced")


class MongoDBAnalysisService:
    """
    MongoDB 집계 파이프라인을 활용한 고급 데이터 분석

    주요 기능:
    - 실시간 성능 대시보드 데이터 생성
    - 사용자별/명령어별 통계 분석
    - 트렌드 분석 및 예측
    - 이상 징후 탐지
    """

    def __init__(self):
        self.metrics_collection = mongodb_connection.metrics_collection
        self.schema_cache_collection = mongodb_connection.schema_cache_collection
        self.thread_cache_collection = mongodb_connection.thread_cache_collection

    @safe_execution("generate_realtime_dashboard_data")
    async def generate_realtime_dashboard_data(self) -> Dict[str, Any]:
        """
        실시간 성능 대시보드를 위한 종합 데이터 생성

        Returns:
            Dict: 대시보드용 실시간 데이터
        """
        try:
            with logger_manager.performance_logger("dashboard_data_aggregation"):
                # 동시에 여러 분석 실행
                results = await asyncio.gather(
                    self._get_recent_1hour_command_stats(),
                    self._analyze_realtime_response_time(),
                    self._analyze_cache_performance(),
                    self._analyze_error_trends(),
                    self._analyze_user_activity(),
                    return_exceptions=True,
                )

                # 결과 통합
                dashboard_data = {
                    "timestamp": datetime.now().isoformat(),
                    "command_stats": (
                        results[0] if not isinstance(results[0], Exception) else {}
                    ),
                    "response_time_analysis": (
                        results[1] if not isinstance(results[1], Exception) else {}
                    ),
                    "cache_performance": (
                        results[2] if not isinstance(results[2], Exception) else {}
                    ),
                    "error_trends": (
                        results[3] if not isinstance(results[3], Exception) else {}
                    ),
                    "user_activity": (
                        results[4] if not isinstance(results[4], Exception) else {}
                    ),
                }

                logger.debug("📊 실시간 대시보드 데이터 생성 완료")
                return dashboard_data

        except Exception as analysis_error:
            raise DatabaseOperationException(
                "대시보드 데이터 생성 실패", original_exception=analysis_error
            )

    async def _get_recent_1hour_command_stats(self) -> Dict[str, Any]:
        """최근 1시간 명령어 사용 통계"""
        start_time = datetime.now() - timedelta(hours=1)

        pipeline = [
            {"$match": {"type": "command_usage", "timestamp": {"$gte": start_time}}},
            {
                "$group": {
                    "_id": "$command",
                    "total_executions": {"$sum": 1},
                    "successful_executions": {
                        "$sum": {"$cond": [{"$eq": ["$success", True]}, 1, 0]}
                    },
                    "avg_execution_time": {"$avg": "$execution_time"},
                    "max_execution_time": {"$max": "$execution_time"},
                    "min_execution_time": {"$min": "$execution_time"},
                }
            },
            {
                "$addFields": {
                    "success_rate": {
                        "$multiply": [
                            {
                                "$divide": [
                                    "$successful_executions",
                                    "$total_executions",
                                ]
                            },
                            100,
                        ]
                    }
                }
            },
            {"$sort": {"total_executions": DESCENDING}},
        ]

        result = await self.metrics_collection.aggregate(pipeline).to_list(100)

        return {
            "period": f"최근 1시간 ({start_time.strftime('%H:%M')} ~ {datetime.now().strftime('%H:%M')})",
            "command_statistics": result,
            "total_commands": sum(item["total_executions"] for item in result),
            "average_success_rate": (
                sum(item["success_rate"] for item in result) / len(result)
                if result
                else 0
            ),
        }

    async def _analyze_realtime_response_time(self) -> Dict[str, Any]:
        """실시간 응답 시간 분석 (5분 단위)"""
        start_time = datetime.now() - timedelta(minutes=30)

        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_time},
                    "execution_time": {"$exists": True},
                }
            },
            {
                "$group": {
                    "_id": {
                        # 5분 단위로 그룹핑
                        "year": {"$year": "$timestamp"},
                        "month": {"$month": "$timestamp"},
                        "day": {"$dayOfMonth": "$timestamp"},
                        "hour": {"$hour": "$timestamp"},
                        "five_min_interval": {
                            "$multiply": [
                                {"$floor": {"$divide": [{"$minute": "$timestamp"}, 5]}},
                                5,
                            ]
                        },
                    },
                    "avg_response_time": {"$avg": "$execution_time"},
                    "max_response_time": {"$max": "$execution_time"},
                    "request_count": {"$sum": 1},
                }
            },
            {
                "$addFields": {
                    "time_period": {
                        "$dateFromParts": {
                            "year": "$_id.year",
                            "month": "$_id.month",
                            "day": "$_id.day",
                            "hour": "$_id.hour",
                            "minute": "$_id.five_min_interval",
                        }
                    }
                }
            },
            {"$sort": {"time_period": ASCENDING}},
        ]

        result = await self.metrics_collection.aggregate(pipeline).to_list(100)

        return {
            "hourly_response_times": result,
            "overall_avg_response_time": (
                sum(item["avg_response_time"] for item in result) / len(result)
                if result
                else 0
            ),
            "max_response_time": max(
                (item["max_response_time"] for item in result), default=0
            ),
        }

    async def _analyze_cache_performance(self) -> Dict[str, Any]:
        """캐시 시스템 성능 분석"""
        start_time = datetime.now() - timedelta(hours=1)

        # 스키마 캐시 분석
        schema_cache_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_cache_count": {"$sum": 1},
                    "avg_cache_size": {"$avg": {"$bsonSize": "$$ROOT"}},
                    "last_update": {"$max": "$updated_at"},
                }
            }
        ]

        schema_cache_result = await self.schema_cache_collection.aggregate(
            schema_cache_pipeline
        ).to_list(1)

        # 스레드 캐시 분석
        thread_cache_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_thread_count": {"$sum": 1},
                    "avg_usage_count": {"$avg": "$use_count"},
                    "total_usage_count": {"$sum": "$use_count"},
                    "active_thread_count": {
                        "$sum": {"$cond": [{"$gte": ["$last_used", start_time]}, 1, 0]}
                    },
                }
            }
        ]

        thread_cache_result = await self.thread_cache_collection.aggregate(
            thread_cache_pipeline
        ).to_list(1)

        return {
            "schema_cache": schema_cache_result[0] if schema_cache_result else {},
            "thread_cache": thread_cache_result[0] if thread_cache_result else {},
            "cache_efficiency": (
                "high"
                if thread_cache_result
                and thread_cache_result[0].get("avg_usage_count", 0) > 2
                else "normal"
            ),
        }

    async def _analyze_error_trends(self) -> Dict[str, Any]:
        """에러 발생 패턴 및 추이 분석"""
        start_time = datetime.now() - timedelta(hours=24)

        pipeline = [
            {"$match": {"timestamp": {"$gte": start_time}, "success": False}},
            {
                "$group": {
                    "_id": {"hour": {"$hour": "$timestamp"}, "type": "$type"},
                    "error_count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.hour": ASCENDING}},
        ]

        result = await self.metrics_collection.aggregate(pipeline).to_list(100)

        # 시간대별 에러 집계
        hourly_errors = {}
        for item in result:
            hour = item["_id"]["hour"]
            if hour not in hourly_errors:
                hourly_errors[hour] = 0
            hourly_errors[hour] += item["error_count"]

        return {
            "24hour_error_trends": hourly_errors,
            "total_error_count": sum(item["error_count"] for item in result),
            "error_patterns": result,
        }

    async def _analyze_user_activity(self) -> Dict[str, Any]:
        """사용자 활동 패턴 분석"""
        start_time = datetime.now() - timedelta(hours=24)

        pipeline = [
            {"$match": {"type": "command_usage", "timestamp": {"$gte": start_time}}},
            {
                "$group": {
                    "_id": "$user_id",
                    "command_executions": {"$sum": 1},
                    "used_commands": {"$addToSet": "$command"},
                    "first_execution": {"$min": "$timestamp"},
                    "last_execution": {"$max": "$timestamp"},
                    "avg_execution_time": {"$avg": "$execution_time"},
                }
            },
            {
                "$addFields": {
                    "activity_duration_minutes": {
                        "$divide": [
                            {"$subtract": ["$last_execution", "$first_execution"]},
                            60000,  # 밀리초를 분으로 변환
                        ]
                    },
                    "unique_command_count": {"$size": "$used_commands"},
                }
            },
            {"$sort": {"command_executions": DESCENDING}},
            {"$limit": 20},  # 상위 20명만
        ]

        result = await self.metrics_collection.aggregate(pipeline).to_list(20)

        return {
            "active_user_count": len(result),
            "top_users": result,
            "total_command_executions": sum(
                item["command_executions"] for item in result
            ),
        }


class MongoDBRealTimeStreaming:
    """
    MongoDB Change Streams를 활용한 실시간 데이터 스트리밍

    주요 기능:
    - 실시간 데이터 변경 모니터링
    - 이벤트 기반 알림 시스템
    - 데이터 동기화 및 복제
    """

    def __init__(self):
        self.change_streams: Dict[str, AsyncIOMotorChangeStream] = {}
        self.event_handlers: Dict[str, callable] = {}

    @safe_execution("start_realtime_metrics_stream")
    async def start_realtime_metrics_stream(self, event_handler: callable):
        """
        메트릭 컬렉션의 실시간 변경사항을 스트리밍
        단일 MongoDB 인스턴스에서는 폴링 방식으로 동작

        Args:
            event_handler: 변경사항 처리 함수
        """
        try:
            # Change Stream 시도 (replica set에서만 동작)
            try:
                pipeline = [
                    {
                        "$match": {
                            "operationType": {"$in": ["insert", "update"]},
                            "fullDocument.type": {"$exists": True},
                        }
                    }
                ]

                change_stream = mongodb_connection.metrics_collection.watch(
                    pipeline, full_document="updateLookup"
                )

                self.change_streams["metrics"] = change_stream
                self.event_handlers["metrics"] = event_handler
                logger.info("📡 메트릭 실시간 스트리밍 시작 (Change Stream)")

                # 비동기 이벤트 처리 루프
                asyncio.create_task(self._process_change_events_loop("metrics"))

            except Exception as watch_error:
                # 단일 MongoDB 인스턴스에서는 change stream을 사용할 수 없음
                error_msg = str(watch_error)
                if "40573" in error_msg or "replica sets" in error_msg.lower():
                    logger.info("📡 단일 MongoDB 인스턴스 감지 - 폴링 방식으로 모니터링 대체")
                else:
                    logger.warning(f"⚠️ Change Stream 사용 불가: {error_msg[:100]}...")
                logger.info("📡 폴링 방식으로 메트릭 모니터링 시작")

                # 폴링 방식으로 대체
                self.event_handlers["metrics"] = event_handler
                asyncio.create_task(self._polling_metrics_monitor("metrics"))

        except Exception as stream_error:
            logger.error(f"❌ 메트릭 스트리밍 시작 실패: {stream_error}")
            # 예외를 발생시키지 않고 로그만 남김 (서비스 시작이 중단되지 않도록)

    async def _process_change_events_loop(self, stream_name: str):
        """Change Stream 이벤트 처리 루프"""
        try:
            change_stream = self.change_streams[stream_name]
            event_handler = self.event_handlers[stream_name]

            async for change_event in change_stream:
                try:
                    # 이벤트 핸들러 호출
                    await event_handler(change_event)

                except Exception as handler_error:
                    logger.error(f"❌ 이벤트 핸들러 실행 실패: {handler_error}")

        except Exception as loop_error:
            error_msg = str(loop_error)
            if "40573" in error_msg or "replica sets" in error_msg.lower():
                logger.debug(f"📡 Change Stream 기능 비활성화됨 (단일 MongoDB): {error_msg}")
            else:
                logger.error(f"❌ 변경사항 처리 루프 오류: {loop_error}")
        finally:
            # 스트림 정리
            if stream_name in self.change_streams:
                await self.change_streams[stream_name].close()
                del self.change_streams[stream_name]

    async def _polling_metrics_monitor(self, stream_name: str):
        """폴링 방식 메트릭 모니터링 (Change Stream 대체)"""
        try:
            event_handler = self.event_handlers[stream_name]
            last_check_time = datetime.now()

            logger.info("📡 폴링 방식 메트릭 모니터링 시작")

            while True:
                try:
                    # 30초마다 확인
                    await asyncio.sleep(30)

                    # 마지막 확인 이후 새로운 메트릭 조회
                    new_metrics = await mongodb_connection.metrics_collection.find(
                        {
                            "timestamp": {"$gte": last_check_time},
                            "type": {"$exists": True},
                        }
                    ).to_list(100)

                    # 새로운 메트릭이 있으면 이벤트 핸들러 호출
                    for metric in new_metrics:
                        try:
                            # Change Stream 이벤트 형태로 변환
                            mock_change_event = {
                                "operationType": "insert",
                                "fullDocument": metric,
                            }
                            await event_handler(mock_change_event)
                        except Exception as handler_error:
                            logger.error(
                                f"❌ 폴링 이벤트 핸들러 실행 실패: {handler_error}"
                            )

                    # 마지막 확인 시간 업데이트
                    last_check_time = datetime.now()

                except asyncio.CancelledError:
                    break
                except Exception as poll_error:
                    logger.error(f"❌ 폴링 모니터링 오류: {poll_error}")
                    await asyncio.sleep(60)  # 에러 시 1분 대기

        except Exception as monitor_error:
            logger.error(f"❌ 폴링 모니터링 시작 실패: {monitor_error}")
        finally:
            # 정리
            if stream_name in self.event_handlers:
                del self.event_handlers[stream_name]
            logger.info("📡 폴링 방식 메트릭 모니터링 종료")

    async def stop_stream(self, stream_name: str):
        """특정 스트림 중지"""
        if stream_name in self.change_streams:
            await self.change_streams[stream_name].close()
            del self.change_streams[stream_name]
            if stream_name in self.event_handlers:
                del self.event_handlers[stream_name]
            logger.info(f"📡 스트림 중지: {stream_name}")


class MongoDBAutoManagement:
    """
    MongoDB 자동 데이터 관리 및 최적화

    주요 기능:
    - 오래된 데이터 자동 정리
    - 인덱스 성능 모니터링 및 최적화
    - 자동 백업 및 아카이빙
    - 데이터 압축 및 최적화
    """

    def __init__(self):
        self.cleanup_in_progress = False

    @safe_execution("auto_cleanup_old_data")
    async def auto_cleanup_old_data(self):
        """
        설정된 보관 정책에 따라 오래된 데이터 자동 정리
        """
        if self.cleanup_in_progress:
            logger.warning("⚠️ 데이터 정리 작업이 이미 실행 중입니다")
            return

        self.cleanup_in_progress = True
        try:
            with logger_manager.performance_logger("old_data_cleanup"):
                # 동시 정리 작업 실행
                cleanup_results = await asyncio.gather(
                    self._cleanup_metrics_data(),
                    self._cleanup_cache_data(),
                    self._cleanup_temp_data(),
                    return_exceptions=True,
                )

                # 결과 요약
                total_deleted_docs = 0
                for result in cleanup_results:
                    if isinstance(result, dict) and "deleted_count" in result:
                        total_deleted_docs += result["deleted_count"]

                logger.info(f"🧹 데이터 정리 완료: 총 {total_deleted_docs}개 문서 삭제")

        finally:
            self.cleanup_in_progress = False

    async def _cleanup_metrics_data(self) -> Dict[str, int]:
        """30일 이상 된 메트릭 데이터 정리"""
        cutoff_date = datetime.now() - timedelta(days=30)

        delete_result = await mongodb_connection.metrics_collection.delete_many(
            {"timestamp": {"$lt": cutoff_date}}
        )

        logger.debug(f"📊 메트릭 데이터 정리: {delete_result.deleted_count}개 삭제")
        return {"deleted_count": delete_result.deleted_count}

    async def _cleanup_cache_data(self) -> Dict[str, int]:
        """만료된 캐시 데이터 정리"""
        current_time = datetime.now()

        # 만료된 스키마 캐시 정리
        schema_cutoff_time = current_time - timedelta(seconds=settings.schema_cache_ttl)
        schema_delete_result = (
            await mongodb_connection.schema_cache_collection.delete_many(
                {"created_at": {"$lt": schema_cutoff_time}}
            )
        )

        # 오래된 스레드 캐시 정리 (30일)
        thread_cutoff_time = current_time - timedelta(days=30)
        thread_delete_result = (
            await mongodb_connection.thread_cache_collection.delete_many(
                {"last_used": {"$lt": thread_cutoff_time}}
            )
        )

        total_deleted = (
            schema_delete_result.deleted_count + thread_delete_result.deleted_count
        )
        logger.debug(f"💾 캐시 데이터 정리: {total_deleted}개 삭제")
        return {"deleted_count": total_deleted}

    async def _cleanup_temp_data(self) -> Dict[str, int]:
        """임시 데이터 및 로그 정리"""
        # 여기서는 예시로 빈 결과 반환
        # 실제로는 임시 컬렉션이나 로그 데이터 정리 로직 추가
        return {"deleted_count": 0}

    @safe_execution("analyze_index_performance")
    async def analyze_index_performance(self) -> Dict[str, Any]:
        """
        모든 컬렉션의 인덱스 성능 분석

        Returns:
            Dict: 인덱스 성능 분석 결과
        """
        try:
            collections = ["metrics", "schema_cache", "thread_cache"]
            analysis_result = {}

            for collection_name in collections:
                collection = getattr(
                    mongodb_connection,
                    f"{collection_name.replace('_', '_')}_collection",
                    None,
                )
                if collection:
                    # 인덱스 통계 조회
                    index_stats = await collection.aggregate(
                        [{"$indexStats": {}}]
                    ).to_list(100)

                    analysis_result[collection_name] = {
                        "index_count": len(index_stats),
                        "index_details": index_stats,
                    }

            logger.info("📈 인덱스 성능 분석 완료")
            return analysis_result

        except Exception as analysis_error:
            raise DatabaseOperationException(
                "인덱스 성능 분석 실패", original_exception=analysis_error
            )

    @safe_execution("collect_database_statistics")
    async def collect_database_statistics(self) -> Dict[str, Any]:
        """
        데이터베이스 전체 통계 수집

        Returns:
            Dict: 데이터베이스 통계 정보
        """
        try:
            # 데이터베이스 상태 정보
            db_stats = await mongodb_connection.main_database.command("dbStats")

            # 컬렉션별 통계
            컬렉션_통계 = {}
            컬렉션들 = await mongodb_connection.main_database.list_collection_names()

            for 컬렉션명 in 컬렉션들:
                try:
                    컬렉션 = mongodb_connection.main_database[컬렉션명]
                    stats = await 컬렉션.aggregate(
                        [
                            {
                                "$group": {
                                    "_id": None,
                                    "문서_수": {"$sum": 1},
                                    "평균_문서_크기": {"$avg": {"$bsonSize": "$$ROOT"}},
                                    "총_크기": {"$sum": {"$bsonSize": "$$ROOT"}},
                                }
                            }
                        ]
                    ).to_list(1)

                    if stats:
                        컬렉션_통계[컬렉션명] = stats[0]

                except Exception:
                    # 특정 컬렉션 분석 실패는 무시
                    continue

            return {
                "데이터베이스_통계": {
                    "이름": db_stats.get("db"),
                    "컬렉션_수": db_stats.get("collections"),
                    "인덱스_수": db_stats.get("indexes"),
                    "데이터_크기_MB": round(
                        db_stats.get("dataSize", 0) / (1024 * 1024), 2
                    ),
                    "인덱스_크기_MB": round(
                        db_stats.get("indexSize", 0) / (1024 * 1024), 2
                    ),
                    "총_크기_MB": round(
                        db_stats.get("storageSize", 0) / (1024 * 1024), 2
                    ),
                },
                "컬렉션별_통계": 컬렉션_통계,
                "수집_시간": datetime.now().isoformat(),
            }

        except Exception as stats_error:
            raise DatabaseOperationException(
                "데이터베이스 통계 수집 실패", original_exception=stats_error
            )


class MongoDBBackupRestore:
    """
    MongoDB 백업 및 복구 관리

    주요 기능:
    - 자동 정기 백업
    - 선택적 데이터 백업
    - 백업 파일 관리
    - 복구 작업 지원
    """

    def __init__(self):
        self.백업_진행중 = False

    @safe_execution("중요_데이터_백업")
    async def 중요_데이터_백업(self) -> Dict[str, Any]:
        """
        중요 데이터의 백업 생성

        Returns:
            Dict: 백업 결과 정보
        """
        if self.백업_진행중:
            return {"상태": "이미_진행중", "메시지": "백업이 이미 진행 중입니다"}

        self.백업_진행중 = True
        try:
            with logger_manager.performance_logger("중요_데이터_백업"):
                백업_결과 = {"백업_시간": datetime.now().isoformat(), "백업_항목들": []}

                # 스키마 캐시 백업
                스키마_문서들 = await mongodb_connection.schema_cache_collection.find(
                    {}
                ).to_list(1000)
                백업_결과["백업_항목들"].append(
                    {
                        "타입": "스키마_캐시",
                        "문서_수": len(스키마_문서들),
                        "크기_추정_KB": sum(len(str(doc)) for doc in 스키마_문서들)
                        // 1024,
                    }
                )

                # 최근 7일 메트릭 백업
                일주일_전 = datetime.now() - timedelta(days=7)
                메트릭_문서들 = await mongodb_connection.metrics_collection.find(
                    {"timestamp": {"$gte": 일주일_전}}
                ).to_list(10000)
                백업_결과["백업_항목들"].append(
                    {
                        "타입": "최근_메트릭",
                        "문서_수": len(메트릭_문서들),
                        "크기_추정_KB": sum(len(str(doc)) for doc in 메트릭_문서들)
                        // 1024,
                    }
                )

                # 활성 스레드 정보 백업
                활성_스레드들 = await mongodb_connection.thread_cache_collection.find(
                    {"last_used": {"$gte": datetime.now() - timedelta(days=7)}}
                ).to_list(1000)
                백업_결과["백업_항목들"].append(
                    {
                        "타입": "활성_스레드",
                        "문서_수": len(활성_스레드들),
                        "크기_추정_KB": sum(len(str(doc)) for doc in 활성_스레드들)
                        // 1024,
                    }
                )

                # 실제 백업 저장은 파일 시스템이나 클라우드 스토리지에 구현
                # 여기서는 메타데이터만 기록

                logger.info(
                    f"💾 백업 완료: 총 {sum(item['문서_수'] for item in 백업_결과['백업_항목들'])}개 문서"
                )
                return 백업_결과

        finally:
            self.백업_진행중 = False


# Global instances (lazy initialization)
mongodb_analysis_service = None
mongodb_realtime_streaming = None
mongodb_auto_management = None
mongodb_backup_restore = None


def get_mongodb_analysis_service():
    """Get MongoDB analysis service instance with lazy initialization"""
    global mongodb_analysis_service
    if mongodb_analysis_service is None:
        mongodb_analysis_service = MongoDBAnalysisService()
    return mongodb_analysis_service


def get_mongodb_realtime_streaming():
    """Get MongoDB real-time streaming service with lazy initialization"""
    global mongodb_realtime_streaming
    if mongodb_realtime_streaming is None:
        mongodb_realtime_streaming = MongoDBRealTimeStreaming()
    return mongodb_realtime_streaming


def get_mongodb_auto_management():
    """Get MongoDB auto management service with lazy initialization"""
    global mongodb_auto_management
    if mongodb_auto_management is None:
        mongodb_auto_management = MongoDBAutoManagement()
    return mongodb_auto_management


def get_mongodb_backup_restore():
    """Get MongoDB backup restore service with lazy initialization"""
    global mongodb_backup_restore
    if mongodb_backup_restore is None:
        mongodb_backup_restore = MongoDBBackupRestore()
    return mongodb_backup_restore


# 스케줄링을 위한 자동 작업 함수들
async def daily_auto_cleanup_task():
    """매일 자동 실행될 데이터 정리 작업"""
    try:
        mongodb_auto_management = get_mongodb_auto_management()
        await mongodb_auto_management.auto_cleanup_old_data()
        logger.info("✅ 일일 자동 정리 작업 완료")
    except Exception as cleanup_error:
        logger.error(f"❌ 일일 자동 정리 작업 실패: {cleanup_error}")


async def weekly_backup_task():
    """주간 자동 백업 작업"""
    try:
        mongodb_backup_restore = get_mongodb_backup_restore()
        await mongodb_backup_restore.backup_critical_data()
        logger.info("✅ 주간 백업 작업 완료")
    except Exception as backup_error:
        logger.error(f"❌ 주간 백업 작업 실패: {backup_error}")


async def start_realtime_performance_monitoring():
    """실시간 성능 모니터링 시작"""

    async def performance_event_handler(change_event):
        """성능 관련 이벤트 처리"""
        try:
            document = change_event.get("fullDocument", {})
            if document.get("type") == "command_usage":
                execution_time = document.get("execution_time", 0)

                # 비정상적으로 긴 실행 시간 감지 (5초 초과)
                if execution_time > 5.0:
                    logger.warning(
                        f"🐌 느린 명령어 감지: {document.get('command')} "
                        f"실행시간 {execution_time:.2f}초"
                    )
        except Exception as handler_error:
            logger.error(f"성능 이벤트 핸들러 오류: {handler_error}")

    try:
        mongodb_realtime_streaming = get_mongodb_realtime_streaming()
        await mongodb_realtime_streaming.start_realtime_metrics_stream(
            performance_event_handler
        )
        logger.info("📡 실시간 성능 모니터링 시작")
    except Exception as monitoring_error:
        logger.error(f"❌ 실시간 성능 모니터링 시작 실패: {monitoring_error}")
