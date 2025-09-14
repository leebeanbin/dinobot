#!/usr/bin/env python3
"""
DinoBot 테스트 실행기 - ServiceManager 초기화 포함
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.core.logger import initialize_logging_system
from src.core.service_manager import service_manager
from utils.testing.comprehensive_command_tester import run_comprehensive_tests
from utils.testing.perfect_crud_tester import run_perfect_crud_tests

async def initialize_system():
    """시스템 초기화"""
    # 1. 로깅 시스템 초기화
    initialize_logging_system()

    # 2. ServiceManager 초기화
    await service_manager.initialize()
    print("✅ ServiceManager 초기화 완료")

async def run_all_tests():
    """모든 테스트 실행"""
    try:
        print("🚀 DinoBot 종합 테스트 시작")

        # 시스템 초기화
        await initialize_system()

        # 1. 종합 명령어 테스트
        print("\n📋 1단계: 종합 명령어 테스트")
        comprehensive_suite = await run_comprehensive_tests()

        # 2. 완벽한 CRUD 테스트
        print("\n🎯 2단계: 완벽한 CRUD 테스트")
        crud_suite = await run_perfect_crud_tests()

        # 결과 요약
        print("\n" + "="*60)
        print("🏁 최종 테스트 결과 요약")
        print("="*60)
        print(f"📊 종합 테스트: {comprehensive_suite.success_rate:.1f}% ({comprehensive_suite.passed_tests}/{comprehensive_suite.total_tests})")
        print(f"🎯 CRUD 테스트: {crud_suite.success_rate:.1f}% ({crud_suite.passed_tests}/{crud_suite.total_tests})")

        total_tests = comprehensive_suite.total_tests + crud_suite.total_tests
        total_passed = comprehensive_suite.passed_tests + crud_suite.passed_tests
        overall_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        print(f"🌟 전체 성공률: {overall_rate:.1f}% ({total_passed}/{total_tests})")

    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # ServiceManager 정리
        await service_manager.shutdown()
        print("✅ ServiceManager 종료 완료")

if __name__ == "__main__":
    asyncio.run(run_all_tests())