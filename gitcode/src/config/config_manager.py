"""
配置管理器

负责配置文件的加载、保存、验证和管理。
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
import logging

from .settings_validator import SettingsValidator
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """配置管理器类"""

    def __init__(self, config_dir: str = "config"):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        self.settings_file = self.config_dir / "settings.yaml"
        self.repos_file = self.config_dir / "repositories.yaml"
        self.secrets_file = self.config_dir / ".secrets"

        self.validator = SettingsValidator()
        self._encryption_key = self._get_or_create_key()
        self._cipher = Fernet(self._encryption_key)

        # 添加缓存机制
        self._config_cache = None
        self._cache_timestamp = 0
        
        # 默认配置
        self._default_config = {
            "global": {
                "log_level": "INFO",
                "max_log_files": 10,
                "auto_save": True
            },
            "repositories": [],
            "commit": {
                "message_template": "{type}: {description}",
                "auto_message": True,
                "max_files_per_commit": 50
            },
            "schedule": {
                "enabled": False,
                "mode": "daily",
                "time": "18:00"
            },
            "monitoring": {
                "enabled": True,
                "debounce_seconds": 5,
                "ignore_patterns": [
                    "*.log", "*.tmp", "node_modules/", 
                    ".git/", "__pycache__/", "*.pyc"
                ]
            }
        }
    
    def _get_or_create_key(self) -> bytes:
        """获取或创建加密密钥"""
        key_file = self.config_dir / ".key"
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            # 设置文件权限（仅所有者可读写）
            os.chmod(key_file, 0o600)
            return key
    
    def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        加载配置文件（带缓存机制）

        Args:
            force_reload: 是否强制重新加载

        Returns:
            配置字典
        """
        try:
            # 检查缓存是否有效
            if not force_reload and self._is_cache_valid():
                return self._config_cache.copy()

            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}

                # 合并默认配置
                merged_config = self._merge_config(self._default_config, config)

                # 验证配置
                if self.validator.validate_config(merged_config):
                    # 更新缓存
                    self._update_cache(merged_config)
                    if force_reload:  # 只在强制重新加载时记录日志
                        logger.info("配置文件重新加载成功")
                    return merged_config
                else:
                    logger.warning("配置文件验证失败，使用默认配置")
                    self._update_cache(self._default_config.copy())
                    return self._default_config.copy()
            else:
                logger.info("配置文件不存在，创建默认配置")
                self.save_config(self._default_config)
                self._update_cache(self._default_config.copy())
                return self._default_config.copy()

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            fallback_config = self._default_config.copy()
            self._update_cache(fallback_config)
            return fallback_config
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置文件

        Args:
            config: 配置字典

        Returns:
            是否保存成功
        """
        try:
            # 验证配置
            if not self.validator.validate_config(config):
                logger.error("配置验证失败，无法保存")
                return False

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False,
                         allow_unicode=True, indent=2)

            # 更新缓存
            self._update_cache(config)
            logger.info("配置文件保存成功")
            return True

        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def get_repo_config(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定仓库的配置
        
        Args:
            repo_name: 仓库名称
            
        Returns:
            仓库配置字典或None
        """
        config = self.load_config()
        repositories = config.get("repositories", [])
        
        for repo in repositories:
            if repo.get("name") == repo_name:
                return repo
        
        return None
    
    def add_repository(self, repo_config: Dict[str, Any]) -> bool:
        """
        添加仓库配置
        
        Args:
            repo_config: 仓库配置字典
            
        Returns:
            是否添加成功
        """
        try:
            config = self.load_config()
            repositories = config.get("repositories", [])
            
            # 检查是否已存在同名仓库
            for repo in repositories:
                if repo.get("name") == repo_config.get("name"):
                    logger.warning(f"仓库 {repo_config.get('name')} 已存在")
                    return False
            
            # 验证仓库配置
            if not self.validator.validate_repo_config(repo_config):
                logger.error("仓库配置验证失败")
                return False
            
            repositories.append(repo_config)
            config["repositories"] = repositories
            
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"添加仓库配置失败: {e}")
            return False
    
    def remove_repository(self, repo_name: str) -> bool:
        """
        移除仓库配置
        
        Args:
            repo_name: 仓库名称
            
        Returns:
            是否移除成功
        """
        try:
            config = self.load_config()
            repositories = config.get("repositories", [])
            
            # 查找并移除仓库
            original_count = len(repositories)
            repositories = [repo for repo in repositories 
                          if repo.get("name") != repo_name]
            
            if len(repositories) == original_count:
                logger.warning(f"仓库 {repo_name} 不存在")
                return False
            
            config["repositories"] = repositories
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"移除仓库配置失败: {e}")
            return False
    
    def update_auth_info(self, repo_name: str, username: str, 
                        email: str, token: str) -> bool:
        """
        更新仓库认证信息
        
        Args:
            repo_name: 仓库名称
            username: 用户名
            email: 邮箱
            token: 访问令牌
            
        Returns:
            是否更新成功
        """
        try:
            # 加密敏感信息
            encrypted_token = self._cipher.encrypt(token.encode()).decode()
            
            auth_info = {
                "username": username,
                "email": email,
                "token": encrypted_token
            }
            
            # 保存到secrets文件
            secrets = self._load_secrets()
            secrets[repo_name] = auth_info
            
            return self._save_secrets(secrets)
            
        except Exception as e:
            logger.error(f"更新认证信息失败: {e}")
            return False
    
    def get_auth_info(self, repo_name: str) -> Optional[Dict[str, str]]:
        """
        获取仓库认证信息
        
        Args:
            repo_name: 仓库名称
            
        Returns:
            认证信息字典或None
        """
        try:
            secrets = self._load_secrets()
            auth_info = secrets.get(repo_name)
            
            if auth_info:
                # 解密token
                encrypted_token = auth_info["token"]
                decrypted_token = self._cipher.decrypt(
                    encrypted_token.encode()).decode()
                
                return {
                    "username": auth_info["username"],
                    "email": auth_info["email"],
                    "token": decrypted_token
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取认证信息失败: {e}")
            return None
    
    def _load_secrets(self) -> Dict[str, Any]:
        """加载secrets文件"""
        try:
            if self.secrets_file.exists():
                with open(self.secrets_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception:
            return {}
    
    def _save_secrets(self, secrets: Dict[str, Any]) -> bool:
        """保存secrets文件"""
        try:
            with open(self.secrets_file, 'w', encoding='utf-8') as f:
                json.dump(secrets, f, indent=2)
            
            # 设置文件权限（仅所有者可读写）
            os.chmod(self.secrets_file, 0o600)
            return True
        except Exception as e:
            logger.error(f"保存secrets文件失败: {e}")
            return False
    
    def _merge_config(self, default: Dict[str, Any], 
                     user: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并默认配置和用户配置
        
        Args:
            default: 默认配置
            user: 用户配置
            
        Returns:
            合并后的配置
        """
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if self._config_cache is None:
            return False

        try:
            # 检查文件修改时间
            if self.settings_file.exists():
                file_mtime = self.settings_file.stat().st_mtime
                return file_mtime <= self._cache_timestamp
            return True
        except Exception:
            return False

    def _update_cache(self, config: Dict[str, Any]):
        """更新配置缓存"""
        import time
        self._config_cache = config.copy()
        self._cache_timestamp = time.time()

    def reset_to_default(self) -> bool:
        """
        重置为默认配置
        
        Returns:
            是否重置成功
        """
        try:
            return self.save_config(self._default_config.copy())
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False
    
    def export_config(self, export_path: str) -> bool:
        """
        导出配置文件
        
        Args:
            export_path: 导出路径
            
        Returns:
            是否导出成功
        """
        try:
            config = self.load_config()
            
            with open(export_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            logger.info(f"配置文件导出成功: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出配置文件失败: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """
        导入配置文件
        
        Args:
            import_path: 导入路径
            
        Returns:
            是否导入成功
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if self.validator.validate_config(config):
                return self.save_config(config)
            else:
                logger.error("导入的配置文件验证失败")
                return False
                
        except Exception as e:
            logger.error(f"导入配置文件失败: {e}")
            return False
