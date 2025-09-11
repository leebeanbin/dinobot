"""
전역 오류 처리 시스템 테스트
- 다양한 오류 시나리오 테스트
- 터미널 오류 표시 확인
"""

import asyncio
from datetime import datetime, timedelta

from src.core.global_error_handler import (
    handle_exception,
    ErrorSeverity,
    global_error_handler,
)
# Note: UnifiedMCPManager may need to be updated based on actual file structure
# from src.service.workflow.unified_mcp_manager import UnifiedMCPManager


def test_basic_errors():
    """기본 오류 처리 테스트"""
    print("🧪 기본 오류 처리 테스트 시작...")

    # 1. 간단한 오류
    try:
        raise ValueError("테스트 오류입니다")
    except Exception as e:
        handle_exception(e, "기본 테스트", ErrorSeverity.LOW)

    # 2. 심각한 오류
    try:
        raise RuntimeError("심각한 시스템 오류")
    except Exception as e:
        handle_exception(
            e, "심각한 오류 테스트", ErrorSeverity.CRITICAL, show_traceback=True
        )

    # 3. 반복 오류 (같은 오류가 여러 번 발생)
    for i in range(5):
        try:
            raise ConnectionError(f"연결 오류 #{i+1}")
        except Exception as e:
            handle_exception(e, "연결 테스트", ErrorSeverity.MEDIUM)

    print("✅ 기본 오류 처리 테스트 완료")


async def test_mcp_errors():
    """MCP 서비스 오류 테스트 - 현재 비활성화됨"""
    print("🧪 MCP 서비스 오류 테스트 시작... (현재 비활성화됨)")
    
    # NOTE: UnifiedMCPManager가 현재 코드베이스에 존재하지 않아 비활성화
    # TODO: MCP 매니저 구현 후 테스트 활성화
    
    try:
        # 임시로 간단한 오류 테스트
        raise NotImplementedError("MCP 매니저가 아직 구현되지 않았습니다")
    except Exception as e:
        handle_exception(e, "MCP 서비스 테스트", ErrorSeverity.LOW)

    print("✅ MCP 서비스 오류 테스트 완료 (임시 구현)")


def test_error_summary():
    """오류 요약 정보 테스트"""
    print("🧪 오류 요약 정보 테스트...")

    summary = global_error_handler.get_error_summary()
    print(f"📊 오류 요약:")
    print(f"   - 고유 오류 수: {summary['total_unique_errors']}")
    print(f"   - 오류 카운트: {summary['error_counts']}")
    print(f"   - 고빈도 오류: {summary['high_frequency_errors']}")

    print("✅ 오류 요약 정보 테스트 완료")


async def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("🔧 전역 오류 처리 시스템 테스트")
    print("=" * 60)

    # 1. 기본 오류 처리 테스트
    test_basic_errors()
    print()

    # 2. MCP 서비스 오류 테스트 (현재 비활성화됨)
    await test_mcp_errors()
    print()

    # 3. 오류 요약 정보 테스트
    test_error_summary()
    print()

    print("=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
