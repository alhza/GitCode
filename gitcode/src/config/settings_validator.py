"""
配置验证器

负责验证配置文件的格式和内容是否正确。
"""

import re
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SettingsValidator:
    """配置验证器类"""
    
    def __init__(self):
        """初始化验证器"""
        # 有效的日志级别
        self.valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        # 有效的调度模式
        self.valid_schedule_modes = ["daily", "weekly", "hourly", "on_change"]
        
        # 时间格式正则表达式
        self.time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
        
        # URL格式正则表达式
        self.url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        # 邮箱格式正则表达式
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        验证完整配置
        
        Args:
            config: 配置字典
            
        Returns:
            是否验证通过
        """
        try:
            # 验证全局配置
            if not self._validate_global_config(config.get("global", {})):
                return False
            
            # 验证仓库配置
            repositories = config.get("repositories", [])
            if not isinstance(repositories, list):
                logger.error("repositories必须是列表类型")
                return False
            
            for repo in repositories:
                if not self.validate_repo_config(repo):
                    return False
            
            # 验证提交配置
            if not self._validate_commit_config(config.get("commit", {})):
                return False
            
            # 验证调度配置
            if not self._validate_schedule_config(config.get("schedule", {})):
                return False
            
            # 验证监控配置
            if not self._validate_monitoring_config(config.get("monitoring", {})):
                return False
            
            logger.info("配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False
    
    def validate_repo_config(self, repo_config: Dict[str, Any]) -> bool:
        """
        验证仓库配置
        
        Args:
            repo_config: 仓库配置字典
            
        Returns:
            是否验证通过
        """
        try:
            # 必需字段检查
            required_fields = ["name", "local_path", "remote_url", "branch"]
            for field in required_fields:
                if field not in repo_config:
                    logger.error(f"仓库配置缺少必需字段: {field}")
                    return False
                
                if not repo_config[field] or not isinstance(repo_config[field], str):
                    logger.error(f"仓库配置字段 {field} 不能为空且必须是字符串")
                    return False
            
            # 验证仓库名称
            name = repo_config["name"]
            if not re.match(r'^[a-zA-Z0-9_-]+$', name):
                logger.error(f"仓库名称 {name} 格式不正确，只能包含字母、数字、下划线和连字符")
                return False
            
            # 验证本地路径
            local_path = repo_config["local_path"]
            if not self._validate_path(local_path):
                logger.error(f"本地路径 {local_path} 不存在或不可访问")
                return False
            
            # 验证远程URL
            remote_url = repo_config["remote_url"]
            if not self._validate_git_url(remote_url):
                logger.error(f"远程URL {remote_url} 格式不正确")
                return False
            
            # 验证分支名称
            branch = repo_config["branch"]
            if not re.match(r'^[a-zA-Z0-9/_-]+$', branch):
                logger.error(f"分支名称 {branch} 格式不正确")
                return False
            
            # 验证可选字段
            if "enabled" in repo_config:
                if not isinstance(repo_config["enabled"], bool):
                    logger.error("enabled字段必须是布尔类型")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"仓库配置验证失败: {e}")
            return False
    
    def _validate_global_config(self, global_config: Dict[str, Any]) -> bool:
        """验证全局配置"""
        try:
            # 验证日志级别
            log_level = global_config.get("log_level", "INFO")
            if log_level not in self.valid_log_levels:
                logger.error(f"无效的日志级别: {log_level}")
                return False
            
            # 验证最大日志文件数
            max_log_files = global_config.get("max_log_files", 10)
            if not isinstance(max_log_files, int) or max_log_files < 1:
                logger.error("max_log_files必须是大于0的整数")
                return False
            
            # 验证自动保存设置
            auto_save = global_config.get("auto_save", True)
            if not isinstance(auto_save, bool):
                logger.error("auto_save必须是布尔类型")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"全局配置验证失败: {e}")
            return False
    
    def _validate_commit_config(self, commit_config: Dict[str, Any]) -> bool:
        """验证提交配置"""
        try:
            # 验证消息模板
            message_template = commit_config.get("message_template", "")
            if not isinstance(message_template, str):
                logger.error("message_template必须是字符串类型")
                return False
            
            # 验证自动消息设置
            auto_message = commit_config.get("auto_message", True)
            if not isinstance(auto_message, bool):
                logger.error("auto_message必须是布尔类型")
                return False
            
            # 验证最大文件数
            max_files = commit_config.get("max_files_per_commit", 50)
            if not isinstance(max_files, int) or max_files < 1:
                logger.error("max_files_per_commit必须是大于0的整数")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"提交配置验证失败: {e}")
            return False
    
    def _validate_schedule_config(self, schedule_config: Dict[str, Any]) -> bool:
        """验证调度配置"""
        try:
            # 验证启用状态
            enabled = schedule_config.get("enabled", False)
            if not isinstance(enabled, bool):
                logger.error("schedule.enabled必须是布尔类型")
                return False
            
            # 如果启用了调度，验证其他字段
            if enabled:
                # 验证调度模式
                mode = schedule_config.get("mode", "daily")
                if mode not in self.valid_schedule_modes:
                    logger.error(f"无效的调度模式: {mode}")
                    return False
                
                # 验证时间格式
                time_str = schedule_config.get("time", "18:00")
                if not self.time_pattern.match(time_str):
                    logger.error(f"时间格式不正确: {time_str}，应为HH:MM格式")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"调度配置验证失败: {e}")
            return False
    
    def _validate_monitoring_config(self, monitoring_config: Dict[str, Any]) -> bool:
        """验证监控配置"""
        try:
            # 验证启用状态
            enabled = monitoring_config.get("enabled", True)
            if not isinstance(enabled, bool):
                logger.error("monitoring.enabled必须是布尔类型")
                return False
            
            # 验证防抖时间
            debounce_seconds = monitoring_config.get("debounce_seconds", 5)
            if not isinstance(debounce_seconds, (int, float)) or debounce_seconds < 0:
                logger.error("debounce_seconds必须是非负数")
                return False
            
            # 验证忽略模式
            ignore_patterns = monitoring_config.get("ignore_patterns", [])
            if not isinstance(ignore_patterns, list):
                logger.error("ignore_patterns必须是列表类型")
                return False
            
            for pattern in ignore_patterns:
                if not isinstance(pattern, str):
                    logger.error("ignore_patterns中的每个元素必须是字符串")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"监控配置验证失败: {e}")
            return False
    
    def _validate_path(self, path: str) -> bool:
        """验证路径是否存在"""
        try:
            return Path(path).exists()
        except Exception:
            return False
    
    def _validate_git_url(self, url: str) -> bool:
        """验证Git URL格式"""
        try:
            # 支持HTTP/HTTPS和SSH格式
            if url.startswith(('http://', 'https://')):
                return bool(self.url_pattern.match(url))
            elif url.startswith('git@'):
                # SSH格式: git@hostname:username/repository.git
                ssh_pattern = re.compile(r'^git@[a-zA-Z0-9.-]+:[a-zA-Z0-9._/-]+\.git$')
                return bool(ssh_pattern.match(url))
            else:
                return False
        except Exception:
            return False
    
    def validate_auth_info(self, username: str, email: str, token: str) -> bool:
        """
        验证认证信息
        
        Args:
            username: 用户名
            email: 邮箱
            token: 访问令牌
            
        Returns:
            是否验证通过
        """
        try:
            # 验证用户名
            if not username or not isinstance(username, str):
                logger.error("用户名不能为空")
                return False
            
            if not re.match(r'^[a-zA-Z0-9_-]+$', username):
                logger.error("用户名格式不正确")
                return False
            
            # 验证邮箱
            if not email or not isinstance(email, str):
                logger.error("邮箱不能为空")
                return False
            
            if not self.email_pattern.match(email):
                logger.error("邮箱格式不正确")
                return False
            
            # 验证访问令牌
            if not token or not isinstance(token, str):
                logger.error("访问令牌不能为空")
                return False
            
            if len(token) < 10:
                logger.error("访问令牌长度不足")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"认证信息验证失败: {e}")
            return False
    
    def get_validation_errors(self, config: Dict[str, Any]) -> List[str]:
        """
        获取配置验证错误列表
        
        Args:
            config: 配置字典
            
        Returns:
            错误信息列表
        """
        errors = []
        
        # 这里可以实现更详细的错误收集逻辑
        # 暂时返回空列表，后续可以扩展
        
        return errors
