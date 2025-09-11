#!/usr/bin/env python3
"""
Discord 봇 설정 확인 스크립트
.env 파일의 설정값들이 올바르게 로드되는지 확인합니다.
"""

import os
from dotenv import load_dotenv


def check_config():
    """환경 변수 설정 상태 확인"""
    load_dotenv()

    print("🔍 DinoBot 설정 확인\n")

    required_vars = {
        "DISCORD_TOKEN": "Discord 봇 토큰",
        "DISCORD_APP_ID": "Discord 애플리케이션 ID",
        "DISCORD_GUILD_ID": "Discord 서버 ID",
        "NOTION_TOKEN": "Notion 통합 토큰",
        "FACTORY_TRACKER_DB_ID": "Notion 데이터베이스 ID",
        "BOARD_DB_ID": "Notion 보드 데이터베이스 ID",
    }

    optional_vars = {
        "DEFAULT_DISCORD_CHANNEL_ID": "기본 Discord 채널 ID",
        "MONGODB_URL": "MongoDB 연결 URL",
        "MONGODB_DB_NAME": "MongoDB 데이터베이스 이름",
        "HOST": "서버 호스트",
        "PORT": "서버 포트",
    }

    print("📋 필수 설정값:")
    all_ok = True
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value and not value.startswith(("YOUR_", "dummy_", "secret_dummy")):
            print(f"✅ {var}: {desc} - 설정됨")
        else:
            print(f"❌ {var}: {desc} - 설정 필요!")
            all_ok = False

    print("\n📋 선택적 설정값:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {desc} - {value}")
        else:
            print(f"⚪ {var}: {desc} - 기본값 사용")

    print("\n" + "=" * 50)
    if all_ok:
        print("🎉 모든 필수 설정이 완료되었습니다!")
        print("   이제 'python main.py'로 애플리케이션을 실행할 수 있습니다.")
    else:
        print("⚠️  일부 필수 설정이 누락되었습니다.")
        print("   .env 파일을 확인하고 필요한 값들을 설정해주세요.")

    print("\n📝 Discord 봇 설정 가이드:")
    print("1. https://discord.com/developers/applications 에서 봇 생성")
    print("2. Bot 탭에서 토큰 복사 → DISCORD_TOKEN")
    print("3. General Information 탭에서 Application ID 복사 → DISCORD_APP_ID")
    print("4. 봇을 서버에 초대 후 서버 ID 복사 → DISCORD_GUILD_ID")


if __name__ == "__main__":
    check_config()
