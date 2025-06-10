"""
自动提交器

整合所有功能模块，提供完整的自动提交解决方案。
"""

import time
import threading
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime
import logging

from .config.config_manager import ConfigManager
from .git_ops.git_handler import GitHandler
from .utils.logger import get_logger, setup_logging
from .utils.message_generator import MessageGenerator

logger = get_logger(__name__)


class AutoCommitter:
    """自动提交器类"""
    
    def __init__(self, config_dir: str = "config"):
        """
        初始化自动提交器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_manager = ConfigManager(config_dir)
        self.message_generator = MessageGenerator()
        
        # Git处理器缓存
        self.git_handlers: Dict[str, GitHandler] = {}
        
        # 监控状态
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # 统计信息
        self.stats = {
            'total_commits': 0,
            'successful_commits': 0,
            'failed_commits': 0,
            'last_commit_time': None,
            'monitored_repos': 0
        }
        
        logger.info("自动提交器初始化完成")
    
    def get_git_handler(self, repo_name: str) -> Optional[GitHandler]:
        """
        获取Git处理器
        
        Args:
            repo_name: 仓库名称
            
        Returns:
            Git处理器实例或None
        """
        if repo_name in self.git_handlers:
            return self.git_handlers[repo_name]
        
        repo_config = self.config_manager.get_repo_config(repo_name)
        if not repo_config:
            logger.error(f"仓库配置不存在: {repo_name}")
            return None
        
        repo_path = repo_config.get("local_path")
        if not repo_path:
            logger.error(f"仓库路径未配置: {repo_name}")
            return None
        
        git_handler = GitHandler(repo_path)
        if git_handler.is_valid_repo():
            self.git_handlers[repo_name] = git_handler
            return git_handler
        else:
            logger.error(f"无效的Git仓库: {repo_path}")
            return None
    
    def check_repo_changes(self, repo_name: str) -> Dict[str, Any]:
        """
        检查仓库变更
        
        Args:
            repo_name: 仓库名称
            
        Returns:
            变更信息字典
        """
        git_handler = self.get_git_handler(repo_name)
        if not git_handler:
            return {"error": f"无法获取仓库 {repo_name} 的Git处理器"}
        
        try:
            status = git_handler.check_status()
            
            # 计算变更文件
            changed_files = status.get('modified_files', [])
            untracked_files = status.get('untracked_files', [])
            staged_files = status.get('staged_files', [])
            
            has_changes = bool(changed_files or untracked_files or staged_files)
            
            return {
                'repo_name': repo_name,
                'has_changes': has_changes,
                'changed_files': changed_files,
                'untracked_files': untracked_files,
                'staged_files': staged_files,
                'total_changes': len(changed_files) + len(untracked_files),
                'status': status
            }
            
        except Exception as e:
            logger.error(f"检查仓库变更失败 {repo_name}: {e}")
            return {"error": str(e)}
    
    def auto_commit_repo(self, repo_name: str, custom_message: str = None) -> bool:
        """
        自动提交仓库
        
        Args:
            repo_name: 仓库名称
            custom_message: 自定义提交消息
            
        Returns:
            是否提交成功
        """
        try:
            # 检查变更
            changes = self.check_repo_changes(repo_name)
            if "error" in changes:
                logger.error(f"检查变更失败: {changes['error']}")
                return False
            
            if not changes['has_changes']:
                logger.info(f"仓库 {repo_name} 没有变更")
                return True
            
            git_handler = self.get_git_handler(repo_name)
            if not git_handler:
                return False
            
            # 添加文件到暂存区
            logger.info(f"添加文件到暂存区: {repo_name}")
            if not git_handler.add_files():
                logger.error(f"添加文件失败: {repo_name}")
                self.stats['failed_commits'] += 1
                return False
            
            # 生成提交消息
            if custom_message:
                commit_message = custom_message
            else:
                commit_message = self.message_generator.generate_message(
                    changed_files=changes['changed_files'],
                    untracked_files=changes['untracked_files']
                )
            
            # 获取认证信息（减少频繁调用）
            auth_info = self.config_manager.get_auth_info(repo_name)
            author_name = auth_info.get("username") if auth_info else None
            author_email = auth_info.get("email") if auth_info else None
            
            # 创建提交
            logger.info(f"创建提交: {repo_name} - {commit_message}")
            if git_handler.create_commit(commit_message, author_name, author_email):
                self.stats['successful_commits'] += 1
                self.stats['total_commits'] += 1
                self.stats['last_commit_time'] = datetime.now()
                
                logger.info(f"提交成功: {repo_name}")
                
                # 检查是否需要推送（使用缓存配置）
                config = self.config_manager.load_config(force_reload=False)
                auto_push = config.get('commit', {}).get('auto_push', False)
                
                if auto_push:
                    logger.info(f"自动推送: {repo_name}")
                    if git_handler.push_changes():
                        logger.info(f"推送成功: {repo_name}")
                    else:
                        logger.warning(f"推送失败: {repo_name}")
                
                return True
            else:
                logger.error(f"提交失败: {repo_name}")
                self.stats['failed_commits'] += 1
                return False
                
        except Exception as e:
            logger.error(f"自动提交失败 {repo_name}: {e}")
            self.stats['failed_commits'] += 1
            return False
    
    def start_monitoring(self, interval: int = 60) -> bool:
        """
        开始监控所有启用的仓库
        
        Args:
            interval: 检查间隔（秒）
            
        Returns:
            是否启动成功
        """
        try:
            if self.is_monitoring:
                logger.warning("监控已在运行")
                return True
            
            config = self.config_manager.load_config(force_reload=False)
            repositories = config.get("repositories", [])
            enabled_repos = [r for r in repositories if r.get("enabled", True)]
            
            if not enabled_repos:
                logger.warning("没有启用的仓库")
                return False
            
            self.stats['monitored_repos'] = len(enabled_repos)
            
            # 启动监控线程
            self.stop_event.clear()
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                args=(enabled_repos, interval),
                name="AutoCommitMonitor"
            )
            self.monitor_thread.start()
            self.is_monitoring = True
            
            logger.info(f"开始监控 {len(enabled_repos)} 个仓库，间隔 {interval} 秒")
            return True
            
        except Exception as e:
            logger.error(f"启动监控失败: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """
        停止监控
        
        Returns:
            是否停止成功
        """
        try:
            if not self.is_monitoring:
                logger.warning("监控未在运行")
                return True
            
            # 停止监控线程
            self.stop_event.set()
            if self.monitor_thread:
                self.monitor_thread.join(timeout=10.0)
            
            self.is_monitoring = False
            logger.info("监控已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止监控失败: {e}")
            return False
    
    def _monitor_loop(self, repositories: List[Dict[str, Any]], interval: int):
        """
        监控循环
        
        Args:
            repositories: 仓库列表
            interval: 检查间隔
        """
        logger.info("监控循环开始")
        
        while not self.stop_event.is_set():
            try:
                for repo_config in repositories:
                    if self.stop_event.is_set():
                        break
                    
                    repo_name = repo_config.get("name")
                    
                    # 检查变更
                    changes = self.check_repo_changes(repo_name)
                    
                    if changes.get("has_changes"):
                        logger.info(f"检测到 {repo_name} 有变更，准备自动提交")
                        
                        # 检查自动提交配置（使用缓存）
                        config = self.config_manager.load_config(force_reload=False)
                        auto_commit = config.get('monitoring', {}).get('auto_commit', True)
                        
                        if auto_commit:
                            self.auto_commit_repo(repo_name)
                        else:
                            logger.info(f"自动提交已禁用，跳过 {repo_name}")
                
                # 等待下次检查
                self.stop_event.wait(interval)
                
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                self.stop_event.wait(5)  # 错误后短暂休眠
        
        logger.info("监控循环结束")
    
    def get_all_repo_status(self) -> List[Dict[str, Any]]:
        """
        获取所有仓库状态
        
        Returns:
            仓库状态列表
        """
        config = self.config_manager.load_config(force_reload=False)
        repositories = config.get("repositories", [])
        
        status_list = []
        for repo_config in repositories:
            repo_name = repo_config.get("name")
            changes = self.check_repo_changes(repo_name)
            
            status_info = {
                'name': repo_name,
                'path': repo_config.get("local_path"),
                'enabled': repo_config.get("enabled", True),
                'has_changes': changes.get("has_changes", False),
                'total_changes': changes.get("total_changes", 0)
            }
            
            if "error" in changes:
                status_info['error'] = changes['error']
            
            status_list.append(status_info)
        
        return status_list
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'monitoring_status': self.is_monitoring,
            'monitored_repos': self.stats['monitored_repos'],
            'total_commits': self.stats['total_commits'],
            'successful_commits': self.stats['successful_commits'],
            'failed_commits': self.stats['failed_commits'],
            'success_rate': (
                self.stats['successful_commits'] / self.stats['total_commits'] 
                if self.stats['total_commits'] > 0 else 0
            ),
            'last_commit_time': self.stats['last_commit_time']
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_monitoring()
