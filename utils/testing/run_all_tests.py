"""
DinoBot 통합 테스트 실행기
모든 테스트를 체계적으로 실행하고 결과를 종합
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# DinoBot 프로젝트 루트를 Python path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.testing.comprehensive_command_tester import run_comprehensive_tests
from utils.testing.crud_command_tester import run_crud_tests
from src.core.logger import get_logger

logger = get_logger("test_runner")


class TestRunner:
    """통합 테스트 실행기"""

    def __init__(self):
        self.test_results = []

    async def run_all_tests(self, cleanup: bool = True) -> Dict[str, Any]:
        """모든 테스트 실행"""
        logger.info("🚀 DinoBot 통합 테스트 시작")
        start_time = datetime.now()

        results = {
            "start_time": start_time,
            "tests": {},
            "summary": {}
        }

        # 1. 종합 커맨드 테스트
        logger.info("📋 종합 커맨드 테스트 실행")
        try:
            comprehensive_suite = await run_comprehensive_tests(cleanup=False)
            results["tests"]["comprehensive"] = {
                "suite": comprehensive_suite,
                "success": True
            }
            logger.info(f"✅ 종합 테스트 완료: {comprehensive_suite.success_rate:.1f}%")
        except Exception as e:
            logger.error(f"❌ 종합 테스트 실패: {str(e)}")
            results["tests"]["comprehensive"] = {
                "suite": None,
                "success": False,
                "error": str(e)
            }

        # 2. CRUD 패턴 테스트
        logger.info("🔄 CRUD 패턴 테스트 실행")
        try:
            crud_suite = await run_crud_tests(cleanup=False)
            results["tests"]["crud"] = {
                "suite": crud_suite,
                "success": True
            }
            logger.info(f"✅ CRUD 테스트 완료: {crud_suite.success_rate:.1f}%")
        except Exception as e:
            logger.error(f"❌ CRUD 테스트 실패: {str(e)}")
            results["tests"]["crud"] = {
                "suite": None,
                "success": False,
                "error": str(e)
            }

        # 3. 성능 테스트 (향후 구현)
        # logger.info("⚡ 성능 테스트 실행")
        # performance_suite = await run_performance_tests()
        # results["tests"]["performance"] = performance_suite

        # 4. 부하 테스트 (향후 구현)
        # logger.info("🔥 부하 테스트 실행")
        # load_suite = await run_load_tests()
        # results["tests"]["load"] = load_suite

        end_time = datetime.now()
        results["end_time"] = end_time
        results["total_duration"] = (end_time - start_time).total_seconds()

        # 결과 요약
        results["summary"] = self._generate_summary(results)

        # 통합 리포트 생성
        report = self._generate_integrated_report(results)
        print(report)

        # 리포트 파일 저장
        self._save_report(report, results)

        # 테스트 데이터 정리
        if cleanup:
            await self._cleanup_all_test_data()

        logger.info("🏁 DinoBot 통합 테스트 완료")
        return results

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """테스트 결과 요약 생성"""
        summary = {
            "total_test_suites": 0,
            "successful_suites": 0,
            "total_tests": 0,
            "total_passed": 0,
            "total_failed": 0,
            "overall_success_rate": 0.0,
            "duration": results["total_duration"]
        }

        for test_name, test_data in results["tests"].items():
            summary["total_test_suites"] += 1

            if test_data["success"] and test_data["suite"]:
                summary["successful_suites"] += 1
                suite = test_data["suite"]
                summary["total_tests"] += suite.total_tests
                summary["total_passed"] += suite.passed_tests
                summary["total_failed"] += suite.failed_tests

        if summary["total_tests"] > 0:
            summary["overall_success_rate"] = (summary["total_passed"] / summary["total_tests"]) * 100

        return summary

    def _generate_integrated_report(self, results: Dict[str, Any]) -> str:
        """통합 테스트 리포트 생성"""
        report = []

        # 헤더
        report.append("=" * 80)
        report.append("🤖 DinoBot 통합 테스트 최종 리포트")
        report.append("=" * 80)
        report.append(f"📅 실행 시간: {results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"⏱️ 총 실행 시간: {results['total_duration']:.2f}초")
        report.append("")

        # 요약 정보
        summary = results["summary"]
        report.append("📊 전체 테스트 요약:")
        report.append(f"  테스트 스위트: {summary['successful_suites']}/{summary['total_test_suites']} 성공")
        report.append(f"  개별 테스트: {summary['total_passed']}/{summary['total_tests']} 성공")
        report.append(f"  전체 성공률: {summary['overall_success_rate']:.1f}%")
        report.append("")

        # 스위트별 결과
        report.append("📋 테스트 스위트별 결과:")
        report.append("-" * 50)

        test_results = []
        for test_name, test_data in results["tests"].items():
            if test_data["success"] and test_data["suite"]:
                suite = test_data["suite"]
                status = "✅"
                details = f"{suite.passed_tests}/{suite.total_tests} 성공 ({suite.success_rate:.1f}%)"
                test_results.append((test_name, status, details, suite.execution_time))
            else:
                status = "❌"
                details = f"실행 실패: {test_data.get('error', '알 수 없는 오류')}"
                test_results.append((test_name, status, details, 0))

        for test_name, status, details, duration in test_results:
            report.append(f"{status} {test_name.upper()} 테스트: {details} ({duration:.2f}s)")

        report.append("")

        # 카테고리별 상세 결과
        for test_name, test_data in results["tests"].items():
            if test_data["success"] and test_data["suite"]:
                report.append(f"📂 {test_name.upper()} 테스트 상세:")
                suite = test_data["suite"]

                # 성공한 테스트
                passed_tests = [r for r in suite.results if r.success]
                if passed_tests:
                    report.append(f"  ✅ 성공 ({len(passed_tests)}개):")
                    for result in passed_tests:
                        report.append(f"    • {result.command_name} ({result.execution_time:.2f}s)")

                # 실패한 테스트
                failed_tests = [r for r in suite.results if not r.success]
                if failed_tests:
                    report.append(f"  ❌ 실패 ({len(failed_tests)}개):")
                    for result in failed_tests:
                        report.append(f"    • {result.command_name}: {result.error_message or '알 수 없는 오류'}")

                report.append("")

        # 권장사항
        report.append("💡 개선 권장사항:")
        report.append("-" * 30)

        if summary["overall_success_rate"] < 100:
            report.append("🔧 실패한 테스트들을 분석하여 버그 수정 필요")

        report.append("🔄 Update/Delete 기능 추가로 완전한 CRUD 구현")
        report.append("⚡ 성능 테스트 및 최적화 고려")
        report.append("🔥 부하 테스트로 확장성 검증")
        report.append("🧪 단위 테스트 커버리지 확대")
        report.append("📈 지속적 통합(CI) 파이프라인 구축")

        return "\n".join(report)

    def _save_report(self, report: str, results: Dict[str, Any]):
        """리포트를 파일로 저장"""
        timestamp = results["start_time"].strftime("%Y%m%d_%H%M%S")

        # 텍스트 리포트 저장
        report_filename = f"/Users/leejungbin/Downloads/dinobot/integrated_test_report_{timestamp}.txt"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(report)

        # JSON 결과 저장 (상세 데이터)
        json_filename = f"/Users/leejungbin/Downloads/dinobot/test_results_{timestamp}.json"
        import json

        # TestResult 객체들을 dict로 변환
        json_data = {}
        for test_name, test_data in results["tests"].items():
            if test_data["success"] and test_data["suite"]:
                suite = test_data["suite"]
                json_data[test_name] = {
                    "total_tests": suite.total_tests,
                    "passed_tests": suite.passed_tests,
                    "failed_tests": suite.failed_tests,
                    "success_rate": suite.success_rate,
                    "execution_time": suite.execution_time,
                    "results": [
                        {
                            "command_name": r.command_name,
                            "command_type": r.command_type,
                            "success": r.success,
                            "execution_time": r.execution_time,
                            "parameters": r.parameters,
                            "error_message": r.error_message,
                            "created_page_id": r.created_page_id
                        }
                        for r in suite.results
                    ]
                }

        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump({
                "summary": results["summary"],
                "start_time": results["start_time"].isoformat(),
                "end_time": results["end_time"].isoformat(),
                "total_duration": results["total_duration"],
                "test_data": json_data
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"📄 통합 리포트 저장: {report_filename}")
        logger.info(f"📊 JSON 결과 저장: {json_filename}")

    async def _cleanup_all_test_data(self):
        """모든 테스트 데이터 정리"""
        logger.info("🧹 테스트 데이터 정리 시작")

        try:
            # 종합 테스트 데이터 정리
            from utils.testing.comprehensive_command_tester import comprehensive_tester
            await comprehensive_tester.cleanup_test_pages()

            # CRUD 테스트 데이터 정리
            from utils.testing.crud_command_tester import crud_tester
            await crud_tester.cleanup_crud_test_data()

            logger.info("✅ 모든 테스트 데이터 정리 완료")

        except Exception as e:
            logger.error(f"❌ 테스트 데이터 정리 중 오류: {str(e)}")


# 전역 테스트 러너
test_runner = TestRunner()


async def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="DinoBot 통합 테스트 실행")
    parser.add_argument("--no-cleanup", action="store_true", help="테스트 후 데이터 정리 건너뛰기")
    parser.add_argument("--test-type", choices=["all", "comprehensive", "crud"],
                       default="all", help="실행할 테스트 타입")

    args = parser.parse_args()

    cleanup = not args.no_cleanup

    if args.test_type == "comprehensive":
        await run_comprehensive_tests(cleanup=cleanup)
    elif args.test_type == "crud":
        await run_crud_tests(cleanup=cleanup)
    else:  # all
        await test_runner.run_all_tests(cleanup=cleanup)


if __name__ == "__main__":
    asyncio.run(main())