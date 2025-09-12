"""
토큰 암호화/복호화 유틸리티
WEBHOOK_SECRET을 키로 사용하여 민감한 설정을 암호화합니다.
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class TokenEncryption:
    """토큰 암호화/복호화 클래스"""
    
    def __init__(self, secret_key: str):
        """
        암호화 객체 초기화
        
        Args:
            secret_key: WEBHOOK_SECRET 또는 다른 마스터 키
        """
        self.secret_key = secret_key.encode('utf-8')
        
    def _derive_key(self, salt: bytes = None) -> bytes:
        """암호화 키 생성"""
        if salt is None:
            salt = b'dinobot_salt_2024'  # 고정 salt (실제로는 랜덤 생성 권장)
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key))
        return key
    
    def encrypt_token(self, token: str) -> str:
        """
        토큰 암호화
        
        Args:
            token: 암호화할 토큰
            
        Returns:
            str: 암호화된 토큰 (base64 인코딩됨)
        """
        try:
            if not token:
                return ""
                
            key = self._derive_key()
            fernet = Fernet(key)
            encrypted_token = fernet.encrypt(token.encode('utf-8'))
            
            # base64로 인코딩해서 문자열로 반환
            return base64.urlsafe_b64encode(encrypted_token).decode('utf-8')
            
        except Exception as e:
            logger.error(f"토큰 암호화 실패: {e}")
            raise
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """
        토큰 복호화
        
        Args:
            encrypted_token: 암호화된 토큰 (base64 인코딩됨)
            
        Returns:
            str: 복호화된 원본 토큰
        """
        try:
            if not encrypted_token:
                return ""
                
            key = self._derive_key()
            fernet = Fernet(key)
            
            # base64 디코딩
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode('utf-8'))
            
            # 복호화
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"토큰 복호화 실패: {e}")
            raise
    
    def is_encrypted(self, value: str) -> bool:
        """
        값이 암호화되어 있는지 확인
        
        Args:
            value: 확인할 값
            
        Returns:
            bool: 암호화된 값이면 True
        """
        try:
            # 암호화된 토큰은 base64 형태이고 특정 길이를 가짐
            if not value or len(value) < 50:  # 암호화된 토큰은 보통 50자 이상
                return False
                
            # base64 디코딩이 가능한지 확인
            base64.urlsafe_b64decode(value.encode('utf-8'))
            return True
            
        except Exception:
            return False


# 전역 암호화 객체 (config_manager 초기화 후 설정됨)
_token_encryption = None


def get_token_encryption():
    """전역 토큰 암호화 객체 반환"""
    global _token_encryption
    return _token_encryption


def initialize_token_encryption(webhook_secret: str):
    """토큰 암호화 시스템 초기화"""
    global _token_encryption
    _token_encryption = TokenEncryption(webhook_secret)
    logger.info("✅ 토큰 암호화 시스템 초기화 완료")


def encrypt_sensitive_config(value: str) -> str:
    """민감한 설정값 암호화"""
    if not _token_encryption:
        logger.warning("토큰 암호화 시스템이 초기화되지 않음")
        return value
        
    return _token_encryption.encrypt_token(value)


def decrypt_sensitive_config(encrypted_value: str) -> str:
    """민감한 설정값 복호화"""
    if not _token_encryption:
        logger.warning("토큰 암호화 시스템이 초기화되지 않음")
        return encrypted_value
        
    return _token_encryption.decrypt_token(encrypted_value)


def is_encrypted_value(value: str) -> bool:
    """값이 암호화되어 있는지 확인"""
    if not _token_encryption:
        return False
        
    return _token_encryption.is_encrypted(value)