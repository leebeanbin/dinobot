#!/usr/bin/env python3
"""
간단한 Task 생성 테스트 - Person 매핑 확인
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.core.logger import initialize_logging_system
from src.core.service_manager import service_manager
from src.dto.discord.discord_dtos import DiscordCommandRequestDTO, DiscordUserDTO, DiscordGuildDTO
from src.dto.common.enums import CommandType

async def test_person_mapping():
    """Person 매핑 테스트"""
    try:
        # 시스템 초기화
        initialize_logging_system()
        await service_manager.initialize()
        print("✅ 시스템 초기화 완료")

        # 테스트 요청 생성
        test_user = DiscordUserDTO(user_id=123456789, username="테스트봇")
        test_guild = DiscordGuildDTO(guild_id=987654321, channel_id=111222333)

        request = DiscordCommandRequestDTO(
            command_type=CommandType.TASK,
            user=test_user,
            guild=test_guild,
            parameters={
                "title": "Person 매핑 테스트",
                "person": "정빈",  # person 파라미터 사용
                "priority": "High",
                "days": 1
            }
        )

        print("🚀 Task 생성 테스트 시작...")

        # main.py의 비즈니스 로직 호출
        from main import app
        response = await app._process_command_business_logic(request)

        print(f"📊 응답: {response.content}")

        if "✅" in str(response.content):
            print("🎉 테스트 성공: Person 매핑이 정상 작동!")
        else:
            print("❌ 테스트 실패: 응답 확인 필요")

    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await service_manager.shutdown()
        print("✅ 테스트 완료")

if __name__ == "__main__":
    asyncio.run(test_person_mapping())