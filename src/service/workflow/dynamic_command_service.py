"""
동적 명령어 처리 서비스
- DB 프로퍼티를 기반으로 한 동적 명령어 처리
- 스키마 기반 자동 속성 설정
- 명령어별 동적 프로퍼티 매핑
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import re

from src.core.dynamic_config import dynamic_config_manager, CommandMapping
from src.service.notion.notion_service import NotionService
from src.service.discord.discord_service import DiscordService
from src.dto.discord.discord_dtos import DiscordMessageResponseDTO
from src.dto.common.enums import ResponseType, MessageType

logger = logging.getLogger(__name__)


class DynamicCommandService:
    """동적 명령어 처리 서비스"""

    def __init__(self):
        self.notion_service: Optional[NotionService] = None
        self.discord_service: Optional[DiscordService] = None
        self.command_handlers: Dict[str, callable] = {}

        # 명령어 패턴 정의
        self.command_patterns = {
            "meeting": r"/meeting\s+title:(.+?)(?:\s+meeting_date:(.+?))?(?:\s+participants:(.+?))?(?:\s+(.+))?$",
            "board": r"/board\s+title:(.+?)(?:\s+doc_type:(.+?))?(?:\s+(.+))?$",
            "factory": r"/factory\s+title:(.+?)(?:\s+priority:(.+?))?(?:\s+assignee:(.+?))?(?:\s+(.+))?$",
        }

    async def initialize(
        self, notion_service: NotionService, discord_service: DiscordService
    ):
        """서비스 초기화"""
        self.notion_service = notion_service
        self.discord_service = discord_service

        # 명령어 핸들러 등록
        self.command_handlers = {
            "meeting": self._handle_meeting_command,
            "board": self._handle_board_command,
            "factory": self._handle_factory_command,
        }

        logger.info("동적 명령어 서비스 초기화 완료")

    async def process_command(
        self, command_text: str, user_id: str, channel_id: str
    ) -> DiscordMessageResponseDTO:
        """명령어 처리"""
        try:
            # 명령어 파싱
            parsed_command = self._parse_command(command_text)
            if not parsed_command:
                return DiscordMessageResponseDTO(
                    content="❌ 잘못된 명령어 형식입니다. `/help`를 입력하여 사용법을 확인하세요.",
                    message_type=MessageType.ERROR_NOTIFICATION,
                )

            command_name = parsed_command["command"]
            parameters = parsed_command["parameters"]

            # 명령어 핸들러 실행
            if command_name in self.command_handlers:
                return await self.command_handlers[command_name](
                    parameters, user_id, channel_id
                )
            else:
                return DiscordMessageResponseDTO(
                    content=f"❌ 알 수 없는 명령어: `{command_name}`",
                    message_type=MessageType.ERROR_NOTIFICATION,
                )

        except Exception as e:
            logger.error(f"명령어 처리 실패: {e}")
            return DiscordMessageResponseDTO(
                content=f"❌ 명령어 처리 중 오류가 발생했습니다: {str(e)}",
                message_type=MessageType.ERROR_NOTIFICATION,
            )

    def _parse_command(self, command_text: str) -> Optional[Dict[str, Any]]:
        """명령어 파싱"""
        command_text = command_text.strip()

        for command_name, pattern in self.command_patterns.items():
            match = re.match(pattern, command_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                parameters = {}

                if command_name == "meeting":
                    parameters = {
                        "title": groups[0].strip(),
                        "meeting_date": groups[1].strip() if groups[1] else None,
                        "participants": (
                            groups[2].strip().split(",") if groups[2] else []
                        ),
                        "additional": groups[3].strip() if groups[3] else None,
                    }
                elif command_name == "board":
                    parameters = {
                        "title": groups[0].strip(),
                        "doc_type": groups[1].strip() if groups[1] else "개발 문서",
                        "additional": groups[2].strip() if groups[2] else None,
                    }
                elif command_name == "factory":
                    parameters = {
                        "title": groups[0].strip(),
                        "priority": groups[1].strip() if groups[1] else "Medium",
                        "assignee": groups[2].strip() if groups[2] else None,
                        "additional": groups[3].strip() if groups[3] else None,
                    }

                return {"command": command_name, "parameters": parameters}

        return None

    async def _handle_meeting_command(
        self, parameters: Dict[str, Any], user_id: str, channel_id: str
    ) -> DiscordMessageResponseDTO:
        """회의 명령어 처리"""
        try:
            # 명령어 매핑 가져오기
            mapping = dynamic_config_manager.get_command_mapping("meeting")
            if not mapping:
                return DiscordMessageResponseDTO(
                    content="❌ 회의 명령어 설정을 찾을 수 없습니다.",
                    message_type=MessageType.ERROR_NOTIFICATION,
                )

            # 입력 데이터 준비
            input_data = {
                "Name": parameters["title"],
                "Participants": (
                    parameters["participants"] if parameters["participants"] else []
                ),
                "Meeting Time": (
                    parameters["meeting_date"] if parameters["meeting_date"] else None
                ),
            }

            # 입력 검증
            validation_result = dynamic_config_manager.validate_command_input(
                "meeting", input_data
            )
            if not validation_result["valid"]:
                error_message = "❌ 입력 검증 실패:\n" + "\n".join(
                    validation_result["errors"]
                )
                return DiscordMessageResponseDTO(
                    content=error_message, message_type=MessageType.ERROR_NOTIFICATION
                )

            # Notion 페이지 생성
            processed_data = validation_result["processed_data"]
            page_response = await self.notion_service.create_meeting_page(
                title=processed_data["Name"],
                participants=processed_data["Participants"],
            )

            if not page_response:
                return DiscordMessageResponseDTO(
                    content="❌ Notion 페이지 생성에 실패했습니다.",
                    message_type=MessageType.ERROR_NOTIFICATION,
                )

            # Discord 이벤트 생성 (시간이 지정된 경우)
            discord_event_created = False
            if parameters["meeting_date"]:
                try:
                    discord_event_created = await self.discord_service.create_discord_event(
                        title=processed_data["Name"],
                        description=f"Notion 페이지: {page_response.get('url', '')}",
                        start_time=parameters["meeting_date"],
                        end_time=None,  # 기본 1시간 후
                        participants=processed_data["Participants"],
                    )
                except Exception as e:
                    logger.warning(f"Discord 이벤트 생성 실패: {e}")

            # 응답 메시지 생성
            response_content = f"✅ 회의록이 성공적으로 생성되었습니다!\n\n"
            response_content += f"📋 **제목**: {processed_data['Name']}\n"
            response_content += f"👥 **참석자**: {', '.join(processed_data['Participants']) if processed_data['Participants'] else '없음'}\n"
            response_content += (
                f"📄 **Notion 페이지**: {page_response.get('url', '')}\n"
            )

            if discord_event_created:
                response_content += f"📅 **Discord 이벤트**: 생성됨\n"
            elif parameters["meeting_date"]:
                response_content += (
                    f"⚠️ **Discord 이벤트**: 생성 실패 (시간 형식을 확인해주세요)\n"
                )

            return DiscordMessageResponseDTO(
                content=response_content, message_type=MessageType.SUCCESS_NOTIFICATION
            )

        except Exception as e:
            logger.error(f"회의 명령어 처리 실패: {e}")
            return DiscordMessageResponseDTO(
                content=f"❌ 회의록 생성 중 오류가 발생했습니다: {str(e)}",
                message_type=MessageType.ERROR_NOTIFICATION,
            )

    async def _handle_board_command(
        self, parameters: Dict[str, Any], user_id: str, channel_id: str
    ) -> DiscordMessageResponseDTO:
        """보드 명령어 처리"""
        try:
            # 명령어 매핑 가져오기
            mapping = dynamic_config_manager.get_command_mapping("board")
            if not mapping:
                return DiscordMessageResponseDTO(
                    content="❌ 보드 명령어 설정을 찾을 수 없습니다.",
                    message_type=MessageType.ERROR_NOTIFICATION,
                )

            # 입력 데이터 준비
            input_data = {"Name": parameters["title"], "Status": parameters["doc_type"]}

            # 입력 검증
            validation_result = dynamic_config_manager.validate_command_input(
                "board", input_data
            )
            if not validation_result["valid"]:
                error_message = "❌ 입력 검증 실패:\n" + "\n".join(
                    validation_result["errors"]
                )
                return DiscordMessageResponseDTO(
                    content=error_message, message_type=MessageType.ERROR_NOTIFICATION
                )

            # Notion 페이지 생성
            processed_data = validation_result["processed_data"]
            page_response = await self.notion_service.create_board_page(
                title=processed_data["Name"], doc_type=processed_data["Status"]
            )

            if not page_response:
                return DiscordMessageResponseDTO(
                    content="❌ Notion 페이지 생성에 실패했습니다.",
                    message_type=MessageType.ERROR_NOTIFICATION,
                )

            # 응답 메시지 생성
            response_content = f"✅ 문서가 성공적으로 생성되었습니다!\n\n"
            response_content += f"📋 **제목**: {processed_data['Name']}\n"
            response_content += f"📄 **유형**: {processed_data['Status']}\n"
            response_content += (
                f"🔗 **Notion 페이지**: {page_response.get('url', '')}\n"
            )

            return DiscordMessageResponseDTO(
                content=response_content, message_type=MessageType.SUCCESS_NOTIFICATION
            )

        except Exception as e:
            logger.error(f"보드 명령어 처리 실패: {e}")
            return DiscordMessageResponseDTO(
                content=f"❌ 문서 생성 중 오류가 발생했습니다: {str(e)}",
                message_type=MessageType.ERROR_NOTIFICATION,
            )

    async def _handle_factory_command(
        self, parameters: Dict[str, Any], user_id: str, channel_id: str
    ) -> DiscordMessageResponseDTO:
        """팩토리 명령어 처리"""
        try:
            # 명령어 매핑 가져오기
            mapping = dynamic_config_manager.get_command_mapping("factory")
            if not mapping:
                return DiscordMessageResponseDTO(
                    content="❌ 팩토리 명령어 설정을 찾을 수 없습니다.",
                    message_type=MessageType.ERROR_NOTIFICATION,
                )

            # 입력 데이터 준비
            task_title = parameters.get("title") or parameters.get("name")
            if not task_title:
                return DiscordMessageResponseDTO(
                    content="❌ 태스크 제목이 필요합니다. (title 또는 name 파라미터 필요)",
                    message_type=MessageType.ERROR_NOTIFICATION,
                )
            
            input_data = {
                "Task name": task_title,
                "Priority": parameters["priority"],
                "Assignee": parameters["assignee"] if parameters["assignee"] else None,
            }

            # 입력 검증
            validation_result = dynamic_config_manager.validate_command_input(
                "factory", input_data
            )
            if not validation_result["valid"]:
                error_message = "❌ 입력 검증 실패:\n" + "\n".join(
                    validation_result["errors"]
                )
                return DiscordMessageResponseDTO(
                    content=error_message, message_type=MessageType.ERROR_NOTIFICATION
                )

            # Notion 페이지 생성 (팩토리 전용 메서드 필요)
            processed_data = validation_result["processed_data"]

            # Factory Tracker DB에 페이지 생성
            from src.core.config_manager import config_manager
            factory_db_id = await config_manager.get("FACTORY_TRACKER_DB_ID")
            if not factory_db_id:
                return DiscordMessageResponseDTO(
                    content="❌ Factory Tracker Database ID가 설정되지 않았습니다.",
                    message_type=MessageType.ERROR_NOTIFICATION,
                )

            # 데이터 소스 ID 가져오기
            data_source_id = await self.notion_service.get_primary_data_source_id(
                factory_db_id
            )
            if not data_source_id:
                return DiscordMessageResponseDTO(
                    content="❌ Factory Tracker Database의 데이터 소스를 찾을 수 없습니다.",
                    message_type=MessageType.ERROR_NOTIFICATION,
                )

            # 페이지 생성
            page_data = {
                "parent": {"data_source_id": data_source_id},
                "properties": {
                    "Task name": self.notion_service.create_title_value(
                        processed_data["Task name"]
                    ),
                    "Priority": self.notion_service.create_select_value(
                        processed_data["Priority"]
                    ),
                    "Status": self.notion_service.create_status_value("Not started"),
                },
            }

            if processed_data["Assignee"]:
                page_data["properties"]["Assignee"] = (
                    self.notion_service.create_people_value(
                        [processed_data["Assignee"]]
                    )
                )

            page_response = self.notion_service.notion_api_client.pages.create(
                **page_data
            )

            # 응답 메시지 생성
            response_content = f"✅ 작업이 성공적으로 생성되었습니다!\n\n"
            response_content += f"📋 **작업명**: {processed_data['Task name']}\n"
            response_content += f"⚡ **우선순위**: {processed_data['Priority']}\n"
            response_content += f"👤 **담당자**: {processed_data['Assignee'] if processed_data['Assignee'] else '미지정'}\n"
            response_content += (
                f"🔗 **Notion 페이지**: {page_response.get('url', '')}\n"
            )

            return DiscordMessageResponseDTO(
                content=response_content, message_type=MessageType.SUCCESS_NOTIFICATION
            )

        except Exception as e:
            logger.error(f"팩토리 명령어 처리 실패: {e}")
            return DiscordMessageResponseDTO(
                content=f"❌ 작업 생성 중 오류가 발생했습니다: {str(e)}",
                message_type=MessageType.ERROR_NOTIFICATION,
            )

    async def get_command_help(self, command: str = None) -> DiscordMessageResponseDTO:
        """명령어 도움말 생성"""
        try:
            if command:
                # 특정 명령어 도움말
                help_info = await dynamic_config_manager.get_command_help(command)
                if "error" in help_info:
                    return DiscordMessageResponseDTO(
                        content=f"❌ {help_info['error']}",
                        message_type=MessageType.ERROR_NOTIFICATION,
                    )

                content = f"📖 **{command.upper()} 명령어 도움말**\n\n"
                content += f"🗄️ **데이터베이스**: {help_info['database']}\n\n"

                if help_info["required_properties"]:
                    content += "🔴 **필수 프로퍼티**:\n"
                    for prop in help_info["required_properties"]:
                        content += f"  • **{prop['name']}** ({prop['type']}): {prop['description']}\n"
                        if prop["options"]:
                            options = [opt.get("name", "") for opt in prop["options"]]
                            content += f"    옵션: {', '.join(options)}\n"
                    content += "\n"

                if help_info["optional_properties"]:
                    content += "🟡 **선택적 프로퍼티**:\n"
                    for prop in help_info["optional_properties"]:
                        content += f"  • **{prop['name']}** ({prop['type']}): {prop['description']}\n"
                        if prop["options"]:
                            options = [opt.get("name", "") for opt in prop["options"]]
                            content += f"    옵션: {', '.join(options)}\n"
                    content += "\n"

                if help_info["auto_set_properties"]:
                    content += "⚙️ **자동 설정 프로퍼티**:\n"
                    for prop, value in help_info["auto_set_properties"].items():
                        content += f"  • **{prop}**: {value}\n"
                    content += "\n"

                if help_info["examples"]:
                    content += "💡 **사용 예시**:\n"
                    for example in help_info["examples"]:
                        content += f"  • {example['description']}\n"
                        content += f"    `{example['usage']}`\n"
                        content += f"    → {example['result']}\n\n"

                return DiscordMessageResponseDTO(
                    content=content, message_type=MessageType.COMMAND_RESPONSE
                )
            else:
                # 전체 명령어 목록
                content = "📖 **DinoBot 명령어 목록**\n\n"

                for command_name in dynamic_config_manager.command_mappings.keys():
                    help_info = await dynamic_config_manager.get_command_help(command_name)
                    content += (
                        f"🔹 **/{command_name}**: {help_info['database']} 관련 명령어\n"
                    )

                content += "\n💡 특정 명령어의 자세한 사용법을 보려면 `/help {명령어}`를 입력하세요."

                return DiscordMessageResponseDTO(
                    content=content, message_type=MessageType.COMMAND_RESPONSE
                )

        except Exception as e:
            logger.error(f"도움말 생성 실패: {e}")
            return DiscordMessageResponseDTO(
                content=f"❌ 도움말 생성 중 오류가 발생했습니다: {str(e)}",
                message_type=MessageType.ERROR_NOTIFICATION,
            )


# 전역 동적 명령어 서비스 인스턴스
dynamic_command_service = DynamicCommandService()
