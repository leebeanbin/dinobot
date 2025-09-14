"""
완벽한 CRUD 테스트 시스템
Create → Read → Update → Delete(Archive) → Restore 전체 주기 테스트
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
from src.core.logger import get_logger
from src.core.constants import (
    VALID_PERSONS, VALID_DOCUMENT_TYPES, VALID_PRIORITIES,
    config_helper, TestConstants, VALID_MEETING_TYPES
)

logger = get_logger("perfect_crud_test")


@dataclass
class CRUDTestFlow:
    """완전한 CRUD 흐름 테스트"""
    entity_type: str
    entity_id: Optional[str] = None
    create_success: bool = False
    read_success: bool = False
    update_success: bool = False
    delete_success: bool = False
    restore_success: bool = False

    @property
    def completion_rate(self) -> float:
        operations = [self.create_success, self.read_success, self.update_success,
                     self.delete_success, self.restore_success]
        return sum(operations) / len(operations) * 100


@dataclass
class PerfectTestResult:
    """완벽한 테스트 결과"""
    command_name: str
    command_type: str
    parameters: Dict[str, Any]
    success: bool
    execution_time: float
    error_message: Optional[str] = None
    response_content: Optional[str] = None
    created_page_id: Optional[str] = None
    operation_type: str = "create"  # create, read, update, delete, restore


class PerfectCRUDTester:
    """완벽한 CRUD 테스터 - 100% 성공률 목표"""

    def __init__(self):
        self.test_user = DiscordUserDTO(
            user_id=999999999,
            username="완벽테스터"
        )
        self.test_guild = DiscordGuildDTO(
            guild_id=888888888,
            channel_id=777777777
        )
        self.crud_flows: List[CRUDTestFlow] = []
        self.all_results: List[PerfectTestResult] = []

    async def run_perfect_crud_tests(self) -> Dict[str, Any]:
        """완벽한 CRUD 테스트 실행"""
        start_time = datetime.now()
        logger.info("🚀 완벽한 CRUD 테스트 시작 - 100% 성공률 목표")

        # 1. Create → Read → Update → Delete → Restore 전체 사이클
        await self._test_complete_crud_cycle()

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # 결과 분석
        results = self._analyze_results(execution_time)
        report = self._generate_perfect_report(results)

        print(report)
        logger.info(f"✅ 완벽한 CRUD 테스트 완료: {results['overall_success_rate']:.1f}%")

        return results

    async def _test_complete_crud_cycle(self):
        """완전한 CRUD 사이클 테스트"""

        # Task CRUD 사이클
        task_flow = await self._test_task_crud_cycle()
        self.crud_flows.append(task_flow)

        # Meeting CRUD 사이클
        meeting_flow = await self._test_meeting_crud_cycle()
        self.crud_flows.append(meeting_flow)

        # Document CRUD 사이클
        document_flow = await self._test_document_crud_cycle()
        self.crud_flows.append(document_flow)

    async def _test_task_crud_cycle(self) -> CRUDTestFlow:
        """Task 완전 CRUD 사이클"""
        flow = CRUDTestFlow(entity_type="task")
        timestamp = datetime.now().strftime("%H%M%S")

        # 1. CREATE
        create_result = await self._execute_crud_test(
            CommandType.TASK,
            {
                "title": f"완벽테스트태스크_{timestamp}",
                "person": VALID_PERSONS[0],
                "priority": VALID_PRIORITIES[0],
                "days": 7
            },
            "Task 생성 테스트",
            "create"
        )
        flow.create_success = create_result.success
        flow.entity_id = create_result.created_page_id
        self.all_results.append(create_result)

        if not flow.create_success or not flow.entity_id:
            logger.error("❌ Task 생성 실패 - CRUD 사이클 중단")
            return flow

        # 2. READ (Search로 확인)
        read_result = await self._execute_crud_test(
            CommandType.SEARCH,
            {
                "query": f"완벽테스트태스크_{timestamp}",
                "page_type": "task",
                "days": 1
            },
            "Task 검색 테스트",
            "read"
        )
        flow.read_success = read_result.success
        self.all_results.append(read_result)

        # 3. UPDATE
        update_result = await self._execute_crud_test(
            CommandType.UPDATE_TASK,
            {
                "page_id": flow.entity_id,
                "title": f"수정된_완벽테스트태스크_{timestamp}",
                "priority": VALID_PRIORITIES[1],
                "status": "In progress"
            },
            "Task 업데이트 테스트",
            "update"
        )
        flow.update_success = update_result.success
        self.all_results.append(update_result)

        # 4. DELETE (Archive)
        delete_result = await self._execute_crud_test(
            CommandType.ARCHIVE_PAGE,
            {
                "page_id": flow.entity_id
            },
            "Task 아카이브 테스트",
            "delete"
        )
        flow.delete_success = delete_result.success
        self.all_results.append(delete_result)

        # 5. RESTORE
        restore_result = await self._execute_crud_test(
            CommandType.RESTORE_PAGE,
            {
                "page_id": flow.entity_id
            },
            "Task 복구 테스트",
            "restore"
        )
        flow.restore_success = restore_result.success
        self.all_results.append(restore_result)

        # 최종 정리 (다시 아카이브)
        if flow.restore_success:
            await self._execute_crud_test(
                CommandType.ARCHIVE_PAGE,
                {"page_id": flow.entity_id},
                "Task 최종 정리",
                "cleanup"
            )

        return flow

    async def _test_meeting_crud_cycle(self) -> CRUDTestFlow:
        """Meeting 완전 CRUD 사이클"""
        flow = CRUDTestFlow(entity_type="meeting")
        timestamp = datetime.now().strftime("%H%M%S")

        # 1. CREATE
        create_result = await self._execute_crud_test(
            CommandType.MEETING,
            {
                "title": f"완벽테스트회의_{timestamp}",
                "meeting_date": "오늘 15:00",
                "participants": VALID_PERSONS[:2],
                "meeting_type": VALID_MEETING_TYPES[0]
            },
            "Meeting 생성 테스트",
            "create"
        )
        flow.create_success = create_result.success
        flow.entity_id = create_result.created_page_id
        self.all_results.append(create_result)

        if not flow.create_success or not flow.entity_id:
            logger.error("❌ Meeting 생성 실패 - CRUD 사이클 중단")
            return flow

        # 2. READ
        read_result = await self._execute_crud_test(
            CommandType.SEARCH,
            {
                "query": f"완벽테스트회의_{timestamp}",
                "page_type": "meeting",
                "days": 1
            },
            "Meeting 검색 테스트",
            "read"
        )
        flow.read_success = read_result.success
        self.all_results.append(read_result)

        # 3. UPDATE
        update_result = await self._execute_crud_test(
            CommandType.UPDATE_MEETING,
            {
                "page_id": flow.entity_id,
                "title": f"수정된_완벽테스트회의_{timestamp}",
                "participants": VALID_PERSONS,
                "meeting_type": VALID_MEETING_TYPES[1]
            },
            "Meeting 업데이트 테스트",
            "update"
        )
        flow.update_success = update_result.success
        self.all_results.append(update_result)

        # 4. DELETE
        delete_result = await self._execute_crud_test(
            CommandType.ARCHIVE_PAGE,
            {
                "page_id": flow.entity_id
            },
            "Meeting 아카이브 테스트",
            "delete"
        )
        flow.delete_success = delete_result.success
        self.all_results.append(delete_result)

        # 5. RESTORE
        restore_result = await self._execute_crud_test(
            CommandType.RESTORE_PAGE,
            {
                "page_id": flow.entity_id
            },
            "Meeting 복구 테스트",
            "restore"
        )
        flow.restore_success = restore_result.success
        self.all_results.append(restore_result)

        # 최종 정리
        if flow.restore_success:
            await self._execute_crud_test(
                CommandType.ARCHIVE_PAGE,
                {"page_id": flow.entity_id},
                "Meeting 최종 정리",
                "cleanup"
            )

        return flow

    async def _test_document_crud_cycle(self) -> CRUDTestFlow:
        """Document 완전 CRUD 사이클"""
        flow = CRUDTestFlow(entity_type="document")
        timestamp = datetime.now().strftime("%H%M%S")

        # 1. CREATE
        create_result = await self._execute_crud_test(
            CommandType.DOCUMENT,
            {
                "title": f"완벽테스트문서_{timestamp}",
                "doc_type": VALID_DOCUMENT_TYPES[0]
            },
            "Document 생성 테스트",
            "create"
        )
        flow.create_success = create_result.success
        flow.entity_id = create_result.created_page_id
        self.all_results.append(create_result)

        if not flow.create_success or not flow.entity_id:
            logger.error("❌ Document 생성 실패 - CRUD 사이클 중단")
            return flow

        # 2. READ
        read_result = await self._execute_crud_test(
            CommandType.SEARCH,
            {
                "query": f"완벽테스트문서_{timestamp}",
                "page_type": "document",
                "days": 1
            },
            "Document 검색 테스트",
            "read"
        )
        flow.read_success = read_result.success
        self.all_results.append(read_result)

        # 3. UPDATE
        update_result = await self._execute_crud_test(
            CommandType.UPDATE_DOCUMENT,
            {
                "page_id": flow.entity_id,
                "title": f"수정된_완벽테스트문서_{timestamp}",
                "doc_type": VALID_DOCUMENT_TYPES[1]
            },
            "Document 업데이트 테스트",
            "update"
        )
        flow.update_success = update_result.success
        self.all_results.append(update_result)

        # 4. DELETE
        delete_result = await self._execute_crud_test(
            CommandType.ARCHIVE_PAGE,
            {
                "page_id": flow.entity_id
            },
            "Document 아카이브 테스트",
            "delete"
        )
        flow.delete_success = delete_result.success
        self.all_results.append(delete_result)

        # 5. RESTORE
        restore_result = await self._execute_crud_test(
            CommandType.RESTORE_PAGE,
            {
                "page_id": flow.entity_id
            },
            "Document 복구 테스트",
            "restore"
        )
        flow.restore_success = restore_result.success
        self.all_results.append(restore_result)

        # 최종 정리
        if flow.restore_success:
            await self._execute_crud_test(
                CommandType.ARCHIVE_PAGE,
                {"page_id": flow.entity_id},
                "Document 최종 정리",
                "cleanup"
            )

        return flow

    async def _execute_crud_test(
        self,
        command_type: CommandType,
        parameters: Dict[str, Any],
        test_name: str,
        operation_type: str
    ) -> PerfectTestResult:
        """CRUD 테스트 실행"""
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

            # 성공 여부 판단
            success = self._is_successful_response(response, operation_type)

            # 생성된 페이지 ID 추출
            page_id = self._extract_page_id(response.content) if success else None

            status_icon = "✅" if success else "❌"
            logger.info(f"{status_icon} {test_name}: {execution_time:.2f}s")

            return PerfectTestResult(
                command_name=test_name,
                command_type=command_type.value,
                parameters=parameters,
                success=success,
                execution_time=execution_time,
                response_content=str(response.content),
                created_page_id=page_id,
                operation_type=operation_type
            )

        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            logger.error(f"❌ {test_name} 실패: {str(e)}")

            return PerfectTestResult(
                command_name=test_name,
                command_type=command_type.value,
                parameters=parameters,
                success=False,
                execution_time=execution_time,
                error_message=str(e),
                operation_type=operation_type
            )

    def _is_successful_response(self, response, operation_type: str) -> bool:
        """응답 성공 여부 판단"""
        if not response or not response.content:
            return False

        content = str(response.content)

        # ERROR가 포함되어 있으면 실패
        if "❌" in content or "ERROR" in content.upper():
            return False

        # 연산별 성공 키워드 확인
        success_keywords = {
            "create": ["✅", "생성 완료", "생성되었습니다"],
            "read": ["결과", "페이지", "검색"],
            "update": ["✅", "업데이트 완료", "업데이트되었습니다"],
            "delete": ["🗑️", "아카이브 완료", "아카이브되었습니다"],
            "restore": ["🔄", "복구 완료", "복구되었습니다"],
            "cleanup": ["🗑️", "아카이브 완료"]
        }

        keywords = success_keywords.get(operation_type, ["✅"])
        return any(keyword in content for keyword in keywords)

    def _extract_page_id(self, response_content: str) -> Optional[str]:
        """응답에서 Notion 페이지 ID 추출"""
        if not response_content:
            return None

        import re
        # Notion URL에서 페이지 ID 추출
        pattern = r"notion\.so/([a-f0-9]{32})"
        match = re.search(pattern, response_content)
        if match:
            return match.group(1)

        # 페이지 ID 직접 추출
        pattern = r"페이지 ID: ([a-f0-9]{32})"
        match = re.search(pattern, response_content)
        return match.group(1) if match else None

    def _analyze_results(self, execution_time: float) -> Dict[str, Any]:
        """결과 분석"""
        total_tests = len(self.all_results)
        successful_tests = sum(1 for r in self.all_results if r.success)

        # 연산별 통계
        operations_stats = {}
        for op_type in ["create", "read", "update", "delete", "restore"]:
            op_results = [r for r in self.all_results if r.operation_type == op_type]
            op_success = sum(1 for r in op_results if r.success)
            operations_stats[op_type] = {
                "total": len(op_results),
                "success": op_success,
                "rate": (op_success / len(op_results) * 100) if op_results else 0
            }

        # 엔티티별 CRUD 완성도
        entity_completions = {}
        for flow in self.crud_flows:
            entity_completions[flow.entity_type] = {
                "completion_rate": flow.completion_rate,
                "create": flow.create_success,
                "read": flow.read_success,
                "update": flow.update_success,
                "delete": flow.delete_success,
                "restore": flow.restore_success
            }

        return {
            "execution_time": execution_time,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "overall_success_rate": (successful_tests / total_tests * 100) if total_tests else 0,
            "operations_stats": operations_stats,
            "entity_completions": entity_completions,
            "crud_flows": self.crud_flows,
            "all_results": self.all_results
        }

    def _generate_perfect_report(self, results: Dict[str, Any]) -> str:
        """완벽한 테스트 리포트 생성"""
        report = []

        report.append("=" * 70)
        report.append("🎯 완벽한 CRUD 테스트 리포트 - 100% 성공률 목표")
        report.append("=" * 70)
        report.append(f"📅 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"⏱️ 총 실행 시간: {results['execution_time']:.2f}초")
        report.append(f"📊 전체 성공률: {results['overall_success_rate']:.1f}% ({results['successful_tests']}/{results['total_tests']})")
        report.append("")

        # CRUD 연산별 성공률
        report.append("🔄 CRUD 연산별 성공률:")
        report.append("-" * 40)
        for op_type, stats in results['operations_stats'].items():
            icon = "✅" if stats['rate'] == 100 else "❌" if stats['rate'] == 0 else "⚠️"
            report.append(f"  {icon} {op_type.upper():8}: {stats['success']}/{stats['total']} ({stats['rate']:.1f}%)")
        report.append("")

        # 엔티티별 CRUD 완성도
        report.append("📋 엔티티별 CRUD 완성도:")
        report.append("-" * 40)
        for entity_type, completion in results['entity_completions'].items():
            rate = completion['completion_rate']
            icon = "🎯" if rate == 100 else "⚠️" if rate >= 80 else "❌"
            report.append(f"  {icon} {entity_type.upper():10}: {rate:.1f}% 완성")

            # 각 연산별 상태
            operations = ['create', 'read', 'update', 'delete', 'restore']
            status_line = "    "
            for op in operations:
                status_icon = "✅" if completion[op] else "❌"
                status_line += f"{op[0].upper()}{status_icon} "
            report.append(status_line)
        report.append("")

        # 실패한 테스트 상세
        failed_tests = [r for r in results['all_results'] if not r.success]
        if failed_tests:
            report.append("❌ 실패한 테스트 상세:")
            report.append("-" * 40)
            for result in failed_tests:
                report.append(f"  • {result.command_name}")
                report.append(f"    연산: {result.operation_type}")
                if result.error_message:
                    report.append(f"    오류: {result.error_message}")
        else:
            report.append("🎉 모든 테스트 성공!")

        report.append("")
        report.append("💡 CRUD 시스템 상태:")
        overall_rate = results['overall_success_rate']
        if overall_rate == 100:
            report.append("🎯 완벽한 CRUD 시스템! 모든 연산이 정상 동작합니다.")
        elif overall_rate >= 90:
            report.append("✅ 우수한 CRUD 시스템! 일부 개선이 필요합니다.")
        elif overall_rate >= 70:
            report.append("⚠️ 준수한 CRUD 시스템! 여러 부분 개선이 필요합니다.")
        else:
            report.append("❌ CRUD 시스템에 심각한 문제가 있습니다!")

        return "\n".join(report)


# 전역 완벽 테스터 인스턴스
perfect_crud_tester = PerfectCRUDTester()


async def run_perfect_crud_tests() -> Dict[str, Any]:
    """완벽한 CRUD 테스트 실행"""
    return await perfect_crud_tester.run_perfect_crud_tests()


if __name__ == "__main__":
    asyncio.run(run_perfect_crud_tests())