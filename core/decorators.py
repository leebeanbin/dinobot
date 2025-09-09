"""
메트릭 수집을 위한 데코레이터들
"""

import time
import functools
import logging
from typing import Callable, Any
from .metrics import get_metrics_collector

logger = logging.getLogger(__name__)


def track_discord_command(command_name: str):
    """Discord 명령어 실행 추적 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            user = "unknown"

            try:
                # 사용자 정보 추출 (Discord 서비스에서)
                if len(args) > 0 and hasattr(args[0], "user"):
                    user = (
                        str(args[0].user.id)
                        if hasattr(args[0].user, "id")
                        else "unknown"
                    )

                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                status = "error"
                logger.error(f"Discord 명령어 실행 실패: {command_name} - {e}")
                raise

            finally:
                duration = time.time() - start_time
                metrics = get_metrics_collector()
                metrics.record_discord_command(command_name, user, status, duration)

        return wrapper

    return decorator


def track_notion_api(operation: str, database: str = "unknown"):
    """Notion API 호출 추적 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                status = "error"
                logger.error(f"Notion API 호출 실패: {operation} - {e}")
                raise

            finally:
                duration = time.time() - start_time
                metrics = get_metrics_collector()
                metrics.record_notion_api_call(operation, database, status, duration)

        return wrapper

    return decorator


def track_mongodb_query(operation: str, collection: str = "unknown"):
    """MongoDB 쿼리 추적 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                status = "error"
                logger.error(f"MongoDB 쿼리 실패: {operation} - {e}")
                raise

            finally:
                duration = time.time() - start_time
                metrics = get_metrics_collector()
                metrics.record_mongodb_query(operation, collection, status, duration)

        return wrapper

    return decorator


def track_error(service: str, error_type: str = "unknown"):
    """에러 추적 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                metrics = get_metrics_collector()
                metrics.record_error(service, error_type)
                logger.error(f"에러 발생: {service} - {error_type} - {e}")
                raise

        return wrapper

    return decorator
