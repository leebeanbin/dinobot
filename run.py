#!/usr/bin/env python3
"""
DinoBot - Discord Notion Integration Bot
Main entry point for the application
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 DinoBot 서비스 종료 중...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ DinoBot 시작 실패: {e}")
        sys.exit(1)