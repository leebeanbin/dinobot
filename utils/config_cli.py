"""
DinoBot 설정 관리 CLI 도구
- 명령줄에서 설정 관리
- 설정 추가/수정/조회 기능
- 설정 검증 및 내보내기
"""

import argparse
import sys
import json
from typing import Dict, Any, List
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.config_manager import config_manager, ConfigType


class ConfigCLI:
    """설정 관리 CLI 클래스"""
    
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="DinoBot 설정 관리 도구",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
사용 예시:
  python utils/config_cli.py list                    # 모든 설정 조회
  python utils/config_cli.py get DISCORD_TOKEN      # 특정 설정 조회
  python utils/config_cli.py set DISCORD_TOKEN abc123  # 설정 값 설정
  python utils/config_cli.py validate DISCORD_TOKEN abc123  # 설정 검증
  python utils/config_cli.py export                 # .env 파일로 내보내기
  python utils/config_cli.py status                 # 설정 상태 조회
  python utils/config_cli.py add-schema             # 새 설정 스키마 추가
            """
        )
        
        subparsers = self.parser.add_subparsers(dest='command', help='사용 가능한 명령어')
        
        # 설정 조회 명령어
        list_parser = subparsers.add_parser('list', help='모든 설정 조회')
        list_parser.add_argument('--category', help='카테고리별 조회')
        list_parser.add_argument('--missing', action='store_true', help='누락된 필수 설정만 조회')
        
        # 특정 설정 조회
        get_parser = subparsers.add_parser('get', help='특정 설정 조회')
        get_parser.add_argument('key', help='설정 키')
        
        # 설정 값 설정
        set_parser = subparsers.add_parser('set', help='설정 값 설정')
        set_parser.add_argument('key', help='설정 키')
        set_parser.add_argument('value', help='설정 값')
        
        # 설정 검증
        validate_parser = subparsers.add_parser('validate', help='설정 값 검증')
        validate_parser.add_argument('key', help='설정 키')
        validate_parser.add_argument('value', help='검증할 값')
        
        # 설정 내보내기
        export_parser = subparsers.add_parser('export', help='설정을 .env 파일로 내보내기')
        export_parser.add_argument('--file', help='출력 파일 경로 (기본: .env)')
        
        # 설정 상태
        status_parser = subparsers.add_parser('status', help='설정 상태 조회')
        
        # 새 설정 스키마 추가
        add_schema_parser = subparsers.add_parser('add-schema', help='새 설정 스키마 추가')
        add_schema_parser.add_argument('--interactive', action='store_true', help='대화형 모드')
        
        # 설정 스키마 제거
        remove_parser = subparsers.add_parser('remove-schema', help='설정 스키마 제거')
        remove_parser.add_argument('key', help='제거할 설정 키')
    
    def run(self, args=None):
        """CLI 실행"""
        if args is None:
            args = sys.argv[1:]
        
        parsed_args = self.parser.parse_args(args)
        
        if not parsed_args.command:
            self.parser.print_help()
            return
        
        try:
            if parsed_args.command == 'list':
                self.list_configs(parsed_args)
            elif parsed_args.command == 'get':
                self.get_config(parsed_args.key)
            elif parsed_args.command == 'set':
                self.set_config(parsed_args.key, parsed_args.value)
            elif parsed_args.command == 'validate':
                self.validate_config(parsed_args.key, parsed_args.value)
            elif parsed_args.command == 'export':
                self.export_configs(parsed_args.file)
            elif parsed_args.command == 'status':
                self.show_status()
            elif parsed_args.command == 'add-schema':
                if parsed_args.interactive:
                    self.add_schema_interactive()
                else:
                    print("대화형 모드로 실행하려면 --interactive 옵션을 사용하세요.")
            elif parsed_args.command == 'remove-schema':
                self.remove_schema(parsed_args.key)
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            sys.exit(1)
    
    def list_configs(self, args):
        """설정 목록 조회"""
        if args.missing:
            missing = config_manager.get_missing_required_configs()
            if missing:
                print("🚨 누락된 필수 설정:")
                for key in missing:
                    schema = config_manager.schemas.get(key)
                    if schema:
                        print(f"  - {key}: {schema.name} ({schema.description})")
            else:
                print("✅ 모든 필수 설정이 완료되었습니다!")
            return
        
        if args.category:
            configs = config_manager.get_configs_by_category(args.category)
            print(f"📋 {args.category} 카테고리 설정:")
            for key, value in configs.items():
                schema = config_manager.schemas.get(key)
                name = schema.name if schema else key
                print(f"  {key}: {value} ({name})")
        else:
            configs = config_manager.get_all_configs()
            print("📋 모든 설정:")
            for key, value in configs.items():
                schema = config_manager.schemas.get(key)
                name = schema.name if schema else key
                required = " [필수]" if schema and schema.required else ""
                print(f"  {key}: {value} ({name}){required}")
    
    def get_config(self, key: str):
        """특정 설정 조회"""
        value = config_manager.get(key)
        schema = config_manager.schemas.get(key)
        
        if schema:
            print(f"📋 설정: {schema.name}")
            print(f"키: {key}")
            print(f"값: {value}")
            print(f"타입: {schema.type.value}")
            print(f"설명: {schema.description}")
            print(f"필수: {'예' if schema.required else '아니오'}")
            print(f"카테고리: {schema.category}")
        else:
            print(f"❌ 알 수 없는 설정 키: {key}")
    
    def set_config(self, key: str, value: str):
        """설정 값 설정"""
        success = config_manager.set(key, value)
        if success:
            print(f"✅ 설정 '{key}' 업데이트 완료: {value}")
        else:
            print(f"❌ 설정 '{key}' 업데이트 실패")
    
    def validate_config(self, key: str, value: str):
        """설정 값 검증"""
        if key not in config_manager.schemas:
            print(f"❌ 알 수 없는 설정 키: {key}")
            return
        
        schema = config_manager.schemas[key]
        valid = config_manager._validate_value(value, schema)
        
        if valid:
            converted_value = config_manager._convert_value(value, schema.type)
            print(f"✅ 설정 값이 유효합니다")
            print(f"변환된 값: {converted_value}")
        else:
            print(f"❌ 설정 값이 유효하지 않습니다")
            print(f"타입: {schema.type.value}")
            if schema.validation_rules:
                print(f"검증 규칙: {schema.validation_rules}")
    
    def export_configs(self, file_path: str = None):
        """설정 내보내기"""
        success = config_manager.export_to_env(file_path)
        if success:
            output_file = file_path or ".env"
            print(f"✅ 설정을 {output_file} 파일로 내보내기 완료")
        else:
            print("❌ 설정 내보내기 실패")
    
    def show_status(self):
        """설정 상태 조회"""
        all_configs = config_manager.get_all_configs()
        missing_configs = config_manager.get_missing_required_configs()
        
        print("📊 DinoBot 설정 상태")
        print("=" * 50)
        print(f"전체 설정: {len(config_manager.schemas)}개")
        print(f"설정 완료: {len([k for k, v in all_configs.items() if v is not None])}개")
        print(f"미설정: {len([k for k, v in all_configs.items() if v is None])}개")
        print(f"필수 미설정: {len(missing_configs)}개")
        
        if missing_configs:
            print("\n🚨 누락된 필수 설정:")
            for key in missing_configs:
                schema = config_manager.schemas.get(key)
                if schema:
                    print(f"  - {key}: {schema.name}")
        
        # 카테고리별 통계
        categories = {}
        for schema in config_manager.schemas.values():
            if schema.category not in categories:
                categories[schema.category] = {'total': 0, 'configured': 0}
            categories[schema.category]['total'] += 1
            if config_manager.get(schema.key) is not None:
                categories[schema.category]['configured'] += 1
        
        print("\n📋 카테고리별 설정 상태:")
        for category, stats in categories.items():
            print(f"  {category}: {stats['configured']}/{stats['total']}")
        
        if len(missing_configs) == 0:
            print("\n🎉 모든 필수 설정이 완료되었습니다!")
        else:
            print(f"\n⚠️  {len(missing_configs)}개의 필수 설정이 누락되었습니다.")
    
    def add_schema_interactive(self):
        """대화형 설정 스키마 추가"""
        print("🔧 새 설정 스키마 추가")
        print("=" * 30)
        
        key = input("설정 키: ").strip()
        if not key:
            print("❌ 설정 키는 필수입니다.")
            return
        
        if key in config_manager.schemas:
            print(f"❌ 이미 존재하는 설정 키입니다: {key}")
            return
        
        name = input("설정 이름: ").strip()
        if not name:
            name = key
        
        description = input("설명: ").strip()
        if not description:
            description = f"{name} 설정"
        
        print("\n사용 가능한 타입:")
        for i, config_type in enumerate(ConfigType, 1):
            print(f"  {i}. {config_type.value}")
        
        type_choice = input("타입 번호 (1-7): ").strip()
        try:
            type_index = int(type_choice) - 1
            if 0 <= type_index < len(ConfigType):
                config_type = list(ConfigType)[type_index]
            else:
                print("❌ 잘못된 타입 번호입니다.")
                return
        except ValueError:
            print("❌ 숫자를 입력해주세요.")
            return
        
        category = input("카테고리 (기본: custom): ").strip()
        if not category:
            category = "custom"
        
        required = input("필수 설정인가요? (y/N): ").strip().lower() == 'y'
        sensitive = input("민감한 정보인가요? (y/N): ").strip().lower() == 'y'
        
        default_value = input("기본값 (선택사항): ").strip()
        if not default_value:
            default_value = None
        
        # 스키마 생성 및 추가
        from src.core.config_manager import ConfigSchema
        schema = ConfigSchema(
            key=key,
            name=name,
            description=description,
            type=config_type,
            required=required,
            default_value=default_value,
            category=category,
            sensitive=sensitive
        )
        
        success = config_manager.add_schema(schema)
        if success:
            print(f"✅ 설정 스키마 '{key}' 추가 완료")
        else:
            print(f"❌ 설정 스키마 '{key}' 추가 실패")
    
    def remove_schema(self, key: str):
        """설정 스키마 제거"""
        if key not in config_manager.schemas:
            print(f"❌ 존재하지 않는 설정 키: {key}")
            return
        
        confirm = input(f"설정 스키마 '{key}'를 제거하시겠습니까? (y/N): ").strip().lower()
        if confirm == 'y':
            success = config_manager.remove_schema(key)
            if success:
                print(f"✅ 설정 스키마 '{key}' 제거 완료")
            else:
                print(f"❌ 설정 스키마 '{key}' 제거 실패")
        else:
            print("취소되었습니다.")


def main():
    """메인 함수"""
    cli = ConfigCLI()
    cli.run()


if __name__ == "__main__":
    main()
