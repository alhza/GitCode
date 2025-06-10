"""
加密管理模块

提供数据加密和解密功能，用于保护敏感信息。
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional
import logging

from .logger import get_logger

logger = get_logger(__name__)


class CryptoManager:
    """加密管理器类"""
    
    def __init__(self, password: str = None):
        """
        初始化加密管理器
        
        Args:
            password: 加密密码，如果不提供则使用默认密码
        """
        if password is None:
            password = "gitee_auto_commit_default_key"
        
        self.password = password.encode()
        self.salt = b'gitee_auto_commit_salt'  # 在生产环境中应该使用随机salt
        self._cipher = self._create_cipher()
    
    def _create_cipher(self) -> Fernet:
        """创建加密器"""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.password))
            return Fernet(key)
        except Exception as e:
            logger.error(f"创建加密器失败: {e}")
            raise
    
    def encrypt(self, data: str) -> str:
        """
        加密字符串
        
        Args:
            data: 要加密的字符串
            
        Returns:
            加密后的字符串（Base64编码）
        """
        try:
            encrypted_data = self._cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        解密字符串
        
        Args:
            encrypted_data: 加密的字符串（Base64编码）
            
        Returns:
            解密后的字符串
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise
    
    def encrypt_file(self, file_path: str, output_path: str = None) -> bool:
        """
        加密文件
        
        Args:
            file_path: 要加密的文件路径
            output_path: 输出文件路径，如果不指定则覆盖原文件
            
        Returns:
            是否加密成功
        """
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            encrypted_data = self._cipher.encrypt(data)
            
            if output_path is None:
                output_path = file_path
            
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            logger.info(f"文件加密成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"文件加密失败: {e}")
            return False
    
    def decrypt_file(self, file_path: str, output_path: str = None) -> bool:
        """
        解密文件
        
        Args:
            file_path: 要解密的文件路径
            output_path: 输出文件路径，如果不指定则覆盖原文件
            
        Returns:
            是否解密成功
        """
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._cipher.decrypt(encrypted_data)
            
            if output_path is None:
                output_path = file_path
            
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            logger.info(f"文件解密成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"文件解密失败: {e}")
            return False
    
    @staticmethod
    def generate_key() -> str:
        """
        生成随机加密密钥
        
        Returns:
            Base64编码的密钥字符串
        """
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode()
    
    @staticmethod
    def generate_salt() -> str:
        """
        生成随机盐值
        
        Returns:
            Base64编码的盐值字符串
        """
        salt = os.urandom(16)
        return base64.urlsafe_b64encode(salt).decode()


def encrypt_string(data: str, password: str = None) -> str:
    """
    快速加密字符串的便捷函数
    
    Args:
        data: 要加密的字符串
        password: 加密密码
        
    Returns:
        加密后的字符串
    """
    crypto = CryptoManager(password)
    return crypto.encrypt(data)


def decrypt_string(encrypted_data: str, password: str = None) -> str:
    """
    快速解密字符串的便捷函数
    
    Args:
        encrypted_data: 加密的字符串
        password: 解密密码
        
    Returns:
        解密后的字符串
    """
    crypto = CryptoManager(password)
    return crypto.decrypt(encrypted_data)
