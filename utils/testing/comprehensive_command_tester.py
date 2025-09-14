"""
DinoBot 전체 커맨드 종합 테스트 시스템
모든 Discord 슬래시 커맨드를 체계적으로 테스트
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

# DinoBot 핵심 모듈 임포트
from src.dto.discord.discord_dtos import (
    DiscordCommandRequestDTO,
    DiscordUserDTO,
    DiscordGuildDTO
)
from src.dto.common.enums import CommandType
from src.core.service_manager import service_manager
from src.core.logger import get_logger
from src.core.constants import (
    VALID_PERSONS, VALID_DOCUMENT_TYPES, VALID_PRIORITIES,
    config_helper, TestConstants
)

logger = get_logger("comprehensive_test")


@dataclass
class TestResult:
    """개별 테스트 결과"""
    command_name: str
    command_type: str
    parameters: Dict[str, Any]
    success: bool
    execution_time: float
    error_message: Optional[str] = None
    response_content: Optional[str] = None
    created_page_id: Optional[str] = None


@dataclass
class TestSuite:
    """테스트 스위트 결과"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    execution_time: float
    results: List[TestResult]

    @property
    def success_rate(self) -> float:
        return (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0


class ComprehensiveCommandTester:
    """DinoBot 전체 커맨드 종합 테스터"""

    def __init__(self):
        self.test_user = DiscordUserDTO(
            user_id=123456789,
            username="테스트봇"
        )
        self.test_guild = DiscordGuildDTO(
            guild_id=987654321,
            channel_id=111222333
        )
        self.created_pages = []  # 생성된 페이지들 추적 (테스트 후 정리용)

    async def run_all_tests(self) -> TestSuite:
        """모든 커맨드 테스트 실행"""
        start_time = datetime.now()
        results = []

        logger.info("🚀 DinoBot 전체 커맨드 테스트 시작")

        # 1. 핵심 생성 커맨드 (CRUD - Create)
        results.extend(await self._test_creation_commands())

        # 2. 조회 커맨드 (CRUD - Read)
        results.extend(await self._test_query_commands())

        # 3. 통계 분석 커맨드
        results.extend(await self._test_analytics_commands())

        # 4. 유틸리티 커맨드
        results.extend(await self._test_utility_commands())

        # 5. 동적 커맨드 (Text-based)
        results.extend(await self._test_dynamic_commands())

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        passed = sum(1 for r in results if r.success)
        failed = len(results) - passed

        suite = TestSuite(
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=failed,
            execution_time=execution_time,
            results=results
        )

        logger.info(f"✅ 테스트 완료: {passed}/{len(results)} 성공 ({suite.success_rate:.1f}%)")
        return suite

    async def _test_creation_commands(self) -> List[TestResult]:
        """핵심 생성 커맨드 테스트 (CRUD - Create)"""
        results = []

        # Task 생성 테스트
        task_tests = [
            {
                "name": "기본 태스크 생성",
                "params": {"title": "테스트 태스크", "person": "정빈", "priority": "High", "days": 3}
            },
            {
                "name": "최소 파라미터 태스크",
                "params": {"title": "최소 태스크"}
            },
            {
                "name": "긴급 태스크",
                "params": {"title": "긴급 버그 수정", "person": "소현", "priority": "Critical", "days": 1}
            }
        ]

        for test in task_tests:
            result = await self._execute_command_test(
                CommandType.TASK, test["params"], test["name"]
            )
            results.append(result)

        # Meeting 생성 테스트
        meeting_tests = [
            {
                "name": "기본 회의록 생성",
                "params": {
                    "title": "주간 스프린트 회의",
                    "meeting_date": "오늘 14:00",
                    "participants": ["정빈", "소현"],
                    "meeting_type": "정기회의"
                }
            },
            {
                "name": "내일 회의 생성",
                "params": {
                    "title": "프로젝트 킥오프",
                    "meeting_date": "내일 10:00",
                    "participants": ["정빈", "소현", "동훈"]
                }
            }
        ]

        for test in meeting_tests:
            result = await self._execute_command_test(
                CommandType.MEETING, test["params"], test["name"]
            )
            results.append(result)

        # Document 생성 테스트
        document_tests = [
            {
                "name": "개발 문서 생성",
                "params": {"title": "API 설계 문서", "doc_type": "개발 문서"}
            },
            {
                "name": "기획안 생성",
                "params": {"title": "신규 기능 기획안", "doc_type": "기획안"}
            },
            {
                "name": "개발 규칙 생성",
                "params": {"title": "코드 리뷰 가이드라인", "doc_type": "개발 규칙"}
            }
        ]

        for test in document_tests:
            result = await self._execute_command_test(
                CommandType.DOCUMENT, test["params"], test["name"]
            )
            results.append(result)

        return results

    async def _test_query_commands(self) -> List[TestResult]:
        """조회 커맨드 테스트 (CRUD - Read)"""
        results = []

        # Status 테스트
        result = await self._execute_command_test(
            CommandType.STATUS, {}, "시스템 상태 확인"
        )
        results.append(result)

        # Help 테스트
        result = await self._execute_command_test(
            CommandType.HELP, {}, "도움말 조회"
        )
        results.append(result)

        # Search 테스트
        search_tests = [
            {
                "name": "키워드 검색",
                "params": {"query": "테스트", "page_type": "task"}
            },
            {
                "name": "전체 검색",
                "params": {"query": "회의", "days": 30}
            }
        ]

        for test in search_tests:
            result = await self._execute_command_test(
                CommandType.SEARCH, test["params"], test["name"]
            )
            results.append(result)

        return results

    async def _test_analytics_commands(self) -> List[TestResult]:
        """통계 분석 커맨드 테스트"""
        results = []

        analytics_tests = [
            {"type": CommandType.DAILY_STATS, "name": "일간 통계", "params": {}},
            {"type": CommandType.WEEKLY_STATS, "name": "주간 통계", "params": {}},
            {"type": CommandType.MONTHLY_STATS, "name": "월간 통계", "params": {}},
            {"type": CommandType.USER_STATS, "name": "사용자 통계", "params": {"days": 30}},
            {"type": CommandType.TEAM_STATS, "name": "팀 통계", "params": {"days": 30}},
            {"type": CommandType.TRENDS, "name": "트렌드 분석", "params": {"days": 14}},
            {"type": CommandType.TASK_STATS, "name": "태스크 통계", "params": {"days": 30}}
        ]

        for test in analytics_tests:
            result = await self._execute_command_test(
                test["type"], test["params"], test["name"]
            )
            results.append(result)

        return results

    async def _test_utility_commands(self) -> List[TestResult]:
        """유틸리티 커맨드 테스트"""
        results = []

        # Fetch 테스트 (페이지 ID가 있을 때만)
        # 실제 환경에서는 유효한 page_id를 사용해야 함
        # 테스트에서는 스킵하거나 mock 사용

        return results

    async def _test_dynamic_commands(self) -> List[TestResult]:
        """동적 커맨드 테스트 (Text-based commands)"""
        results = []

        # 동적 커맨드는 별도 서비스에서 처리되므로
        # 향후 확장 시 추가 구현

        return results

    async def _execute_command_test(
        self,
        command_type: CommandType,
        parameters: Dict[str, Any],
        test_name: str
    ) -> TestResult:
        """개별 커맨드 테스트 실행"""
        start_time = datetime.now()

        try:
            # Discord 커맨드 요청 DTO 생성
            request = DiscordCommandRequestDTO(
                command_type=command_type,
                user=self.test_user,
                guild=self.test_guild,
                parameters=parameters
            )

            # ServiceManager 인스턴스를 통한 커맨드 실행
            from main import app
            response = await app._process_command_business_logic(request)

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # 성공 여부 판단 (더 정확한 로직)
            if hasattr(response.message_type, 'value'):
                success = not response.message_type.value.startswith("ERROR")
            else:
                # 응답 내용 기반 판단
                content_str = str(response.content)
                success = not ("❌" in content_str or "ERROR" in content_str or "실패" in content_str)

            # 생성된 페이지 ID 추출 (정리용)
            page_id = self._extract_page_id(response.content)
            if page_id:
                self.created_pages.append(page_id)

            logger.info(f"{'✅' if success else '❌'} {test_name}: {execution_time:.2f}s")

            return TestResult(
                command_name=test_name,
                command_type=command_type.value,
                parameters=parameters,
                success=success,
                execution_time=execution_time,
                response_content=str(response.content),
                created_page_id=page_id
            )

        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            logger.error(f"❌ {test_name} 실패: {str(e)}")

            return TestResult(
                command_name=test_name,
                command_type=command_type.value,
                parameters=parameters,
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )

    def _extract_page_id(self, response_content: str) -> Optional[str]:
        """응답에서 Notion 페이지 ID 추출"""
        if not response_content:
            return None

        # Notion URL에서 페이지 ID 추출
        import re
        pattern = r"notion\.so/([a-f0-9]{32})"
        match = re.search(pattern, response_content)
        return match.group(1) if match else None

    async def cleanup_test_pages(self) -> int:
        """테스트로 생성된 페이지들 정리 (Archive 방식 사용)"""
        if not self.created_pages:
            logger.info("정리할 테스트 페이지가 없습니다")
            return 0

        cleaned_count = 0
        from src.core.service_manager import service_manager
        notion_service = service_manager.get_service("notion")

        for page_id in self.created_pages:
            try:
                success = await notion_service.archive_page(page_id)
                if success:
                    cleaned_count += 1
                    logger.info(f"🗑️ 테스트 페이지 아카이브 완료: {page_id}")
                else:
                    logger.warning(f"⚠️ 페이지 아카이브 실패: {page_id}")
            except Exception as e:
                logger.error(f"❌ 페이지 아카이브 중 오류: {page_id} - {str(e)}")

        logger.info(f"🧹 총 {cleaned_count}/{len(self.created_pages)} 페이지 아카이브 완료")
        self.created_pages.clear()
        return cleaned_count

    def generate_report(self, suite: TestSuite, save_to_file: bool = True) -> str:
        """테스트 결과 리포트 생성"""
        report = []

        # 헤더
        report.append("=" * 60)
        report.append("🤖 DinoBot 전체 커맨드 테스트 리포트")
        report.append("=" * 60)
        report.append(f"📅 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"⏱️ 총 실행 시간: {suite.execution_time:.2f}초")
        report.append(f"📊 성공률: {suite.success_rate:.1f}% ({suite.passed_tests}/{suite.total_tests})")
        report.append("")

        # 카테고리별 결과
        categories = {
            "생성 커맨드 (Create)": ["task", "meeting", "document"],
            "조회 커맨드 (Read)": ["status", "help", "search"],
            "통계 커맨드": ["daily_stats", "weekly_stats", "monthly_stats", "user_stats", "team_stats", "trends", "task_stats"],
            "유틸리티": ["fetch_page", "watch_page"]
        }

        for category, command_types in categories.items():
            category_results = [r for r in suite.results if r.command_type in command_types]
            if category_results:
                passed = sum(1 for r in category_results if r.success)
                total = len(category_results)
                rate = (passed / total) * 100

                report.append(f"📂 {category}: {passed}/{total} 성공 ({rate:.1f}%)")

                for result in category_results:
                    status = "✅" if result.success else "❌"
                    report.append(f"  {status} {result.command_name} ({result.execution_time:.2f}s)")
                    if not result.success and result.error_message:
                        report.append(f"    💥 오류: {result.error_message}")

                report.append("")

        # 실패한 테스트 상세
        failed_tests = [r for r in suite.results if not r.success]
        if failed_tests:
            report.append("❌ 실패한 테스트 상세:")
            report.append("-" * 40)

            for result in failed_tests:
                report.append(f"테스트: {result.command_name}")
                report.append(f"커맨드: {result.command_type}")
                report.append(f"파라미터: {result.parameters}")
                if result.error_message:
                    report.append(f"오류: {result.error_message}")
                if result.response_content:
                    report.append(f"응답: {result.response_content[:200]}...")
                report.append("")

        report_text = "\n".join(report)

        # 파일로 저장
        if save_to_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/Users/leejungbin/Downloads/dinobot/test_results_{timestamp}.txt"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(report_text)

            logger.info(f"📄 테스트 리포트 저장: {filename}")

        return report_text


# 전역 테스터 인스턴스
comprehensive_tester = ComprehensiveCommandTester()


async def run_comprehensive_tests(cleanup: bool = True) -> TestSuite:
    """종합 테스트 실행 및 정리"""
    # 테스트 실행
    suite = await comprehensive_tester.run_all_tests()

    # 리포트 생성
    report = comprehensive_tester.generate_report(suite)
    print(report)

    # 테스트 페이지 정리
    if cleanup:
        await comprehensive_tester.cleanup_test_pages()

    return suite


if __name__ == "__main__":
    # 테스트 실행
    asyncio.run(run_comprehensive_tests())