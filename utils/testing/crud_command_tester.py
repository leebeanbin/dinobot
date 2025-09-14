"""
DinoBot CRUD 커맨드 전용 테스터
Create, Read, Update, Delete 기능 체계적 테스트
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.dto.discord.discord_dtos import (
    DiscordCommandRequestDTO,
    DiscordUserDTO,
    DiscordGuildDTO
)
from src.dto.common.enums import CommandType
from src.core.logger import get_logger
from .comprehensive_command_tester import TestResult, TestSuite

logger = get_logger("crud_test")


@dataclass
class CRUDTestFlow:
    """CRUD 흐름 테스트"""
    entity_type: str  # task, meeting, document
    created_id: Optional[str] = None
    create_success: bool = False
    read_success: bool = False
    update_success: bool = False  # 향후 구현
    delete_success: bool = False  # 향후 구현


class CRUDCommandTester:
    """CRUD 전용 커맨드 테스터"""

    def __init__(self):
        self.test_user = DiscordUserDTO(
            user_id=123456789,
            username="CRUD테스터"
        )
        self.test_guild = DiscordGuildDTO(
            guild_id=987654321,
            channel_id=111222333
        )
        self.crud_flows: List[CRUDTestFlow] = []

    async def run_crud_tests(self) -> TestSuite:
        """CRUD 패턴 테스트 실행"""
        start_time = datetime.now()
        results = []

        logger.info("🔄 DinoBot CRUD 패턴 테스트 시작")

        # 1. Create 테스트
        create_results = await self._test_create_operations()
        results.extend(create_results)

        # 2. Read 테스트 (생성된 항목들 검색/조회)
        read_results = await self._test_read_operations()
        results.extend(read_results)

        # 3. Update 테스트 (향후 구현 시)
        # update_results = await self._test_update_operations()
        # results.extend(update_results)

        # 4. Delete 테스트 (향후 구현 시)
        # delete_results = await self._test_delete_operations()
        # results.extend(delete_results)

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

        logger.info(f"🔄 CRUD 테스트 완료: {passed}/{len(results)} 성공 ({suite.success_rate:.1f}%)")
        return suite

    async def _test_create_operations(self) -> List[TestResult]:
        """Create 연산 테스트"""
        results = []

        # Task 생성 테스트
        task_flow = CRUDTestFlow(entity_type="task")
        task_result = await self._create_test_entity(
            CommandType.TASK,
            {
                "title": f"CRUD 테스트 태스크 {datetime.now().strftime('%H%M%S')}",
                "person": "정빈",
                "priority": "Medium",
                "days": 7
            },
            "Task Create 테스트"
        )
        results.append(task_result)

        task_flow.create_success = task_result.success
        task_flow.created_id = task_result.created_page_id
        self.crud_flows.append(task_flow)

        # Meeting 생성 테스트
        meeting_flow = CRUDTestFlow(entity_type="meeting")
        meeting_result = await self._create_test_entity(
            CommandType.MEETING,
            {
                "title": f"CRUD 테스트 회의 {datetime.now().strftime('%H%M%S')}",
                "meeting_date": "오늘 15:00",
                "participants": ["정빈", "소현"],
                "meeting_type": "프로젝트 회의"
            },
            "Meeting Create 테스트"
        )
        results.append(meeting_result)

        meeting_flow.create_success = meeting_result.success
        meeting_flow.created_id = meeting_result.created_page_id
        self.crud_flows.append(meeting_flow)

        # Document 생성 테스트
        document_flow = CRUDTestFlow(entity_type="document")
        document_result = await self._create_test_entity(
            CommandType.DOCUMENT,
            {
                "title": f"CRUD 테스트 문서 {datetime.now().strftime('%H%M%S')}",
                "doc_type": "개발 문서"
            },
            "Document Create 테스트"
        )
        results.append(document_result)

        document_flow.create_success = document_result.success
        document_flow.created_id = document_result.created_page_id
        self.crud_flows.append(document_flow)

        return results

    async def _test_read_operations(self) -> List[TestResult]:
        """Read 연산 테스트"""
        results = []

        # 1. 전체 검색 테스트
        search_result = await self._execute_command_test(
            CommandType.SEARCH,
            {"query": "CRUD 테스트", "days": 1},
            "CRUD 엔티티 검색 테스트"
        )
        results.append(search_result)

        # 2. 각 타입별 검색
        for entity_type in ["task", "meeting", "document"]:
            type_search_result = await self._execute_command_test(
                CommandType.SEARCH,
                {"query": "CRUD 테스트", "page_type": entity_type, "days": 1},
                f"{entity_type} 타입 검색 테스트"
            )
            results.append(type_search_result)

        # 3. 생성된 항목들 개별 조회 (fetch 명령)
        for flow in self.crud_flows:
            if flow.created_id and flow.create_success:
                fetch_result = await self._execute_command_test(
                    CommandType.FETCH_PAGE,
                    {"page_id": flow.created_id},
                    f"{flow.entity_type} 개별 조회 테스트"
                )
                results.append(fetch_result)
                flow.read_success = fetch_result.success

        return results

    async def _create_test_entity(
        self,
        command_type: CommandType,
        parameters: Dict[str, Any],
        test_name: str
    ) -> TestResult:
        """테스트 엔티티 생성"""
        return await self._execute_command_test(command_type, parameters, test_name)

    async def _execute_command_test(
        self,
        command_type: CommandType,
        parameters: Dict[str, Any],
        test_name: str
    ) -> TestResult:
        """커맨드 테스트 실행"""
        start_time = datetime.now()

        try:
            request = DiscordCommandRequestDTO(
                command_type=command_type,
                user=self.test_user,
                guild=self.test_guild,
                parameters=parameters
            )

            from main import app
            response = await app._process_command_business_logic(request)

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            success = not (response.message_type.value.startswith("ERROR")
                          if hasattr(response.message_type, 'value')
                          else "❌" in str(response.content))

            page_id = self._extract_page_id(response.content)

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

        import re
        pattern = r"notion\.so/([a-f0-9]{32})"
        match = re.search(pattern, response_content)
        return match.group(1) if match else None

    def generate_crud_report(self, suite: TestSuite) -> str:
        """CRUD 테스트 리포트 생성"""
        report = []

        report.append("=" * 50)
        report.append("🔄 DinoBot CRUD 패턴 테스트 리포트")
        report.append("=" * 50)
        report.append(f"📅 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📊 전체 성공률: {suite.success_rate:.1f}% ({suite.passed_tests}/{suite.total_tests})")
        report.append("")

        # CRUD 플로우별 상태
        report.append("📋 CRUD 플로우 상태:")
        report.append("-" * 30)

        for flow in self.crud_flows:
            create_status = "✅" if flow.create_success else "❌"
            read_status = "✅" if flow.read_success else "❌"
            update_status = "⏳"  # 향후 구현
            delete_status = "⏳"  # 향후 구현

            report.append(f"{flow.entity_type.upper()}:")
            report.append(f"  Create: {create_status}")
            report.append(f"  Read:   {read_status}")
            report.append(f"  Update: {update_status} (향후 구현)")
            report.append(f"  Delete: {delete_status} (향후 구현)")
            if flow.created_id:
                report.append(f"  Page ID: {flow.created_id}")
            report.append("")

        # 연산별 통계
        create_results = [r for r in suite.results if "Create" in r.command_name]
        read_results = [r for r in suite.results if ("검색" in r.command_name or "조회" in r.command_name)]

        if create_results:
            create_success = sum(1 for r in create_results if r.success)
            report.append(f"📝 Create 연산: {create_success}/{len(create_results)} 성공")

        if read_results:
            read_success = sum(1 for r in read_results if r.success)
            report.append(f"🔍 Read 연산: {read_success}/{len(read_results)} 성공")

        report.append("")
        report.append("💡 CRUD 완성도를 위한 제안:")
        report.append("- Update 커맨드 추가 필요 (예: /update_task, /update_meeting)")
        report.append("- Delete 커맨드 추가 필요 (예: /delete_task, /archive_page)")
        report.append("- Bulk 연산 지원 (예: /bulk_update, /bulk_delete)")

        return "\n".join(report)

    async def cleanup_crud_test_data(self):
        """CRUD 테스트로 생성된 데이터 정리"""
        from src.core.service_manager import service_manager
        notion_service = service_manager.get_service("notion")

        cleaned_count = 0
        for flow in self.crud_flows:
            if flow.created_id and flow.create_success:
                try:
                    success = await notion_service.archive_page(flow.created_id)
                    if success:
                        cleaned_count += 1
                        logger.info(f"🗑️ CRUD 테스트 데이터 정리: {flow.entity_type} - {flow.created_id}")
                except Exception as e:
                    logger.error(f"❌ CRUD 데이터 정리 실패: {flow.created_id} - {str(e)}")

        logger.info(f"🧹 CRUD 테스트 데이터 정리 완료: {cleaned_count}개")


# 전역 CRUD 테스터 인스턴스
crud_tester = CRUDCommandTester()


async def run_crud_tests(cleanup: bool = True) -> TestSuite:
    """CRUD 테스트 실행"""
    suite = await crud_tester.run_crud_tests()

    report = crud_tester.generate_crud_report(suite)
    print(report)

    if cleanup:
        await crud_tester.cleanup_crud_test_data()

    return suite


if __name__ == "__main__":
    asyncio.run(run_crud_tests())