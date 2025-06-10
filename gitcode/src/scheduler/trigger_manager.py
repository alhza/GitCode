"""
触发器管理器

管理各种事件触发器，如文件变更触发器等。
"""

import threading
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import logging

from ..utils.logger import get_logger
from ..monitor.file_watcher import FileWatcher

logger = get_logger(__name__)


class TriggerManager:
    """触发器管理器类"""
    
    def __init__(self):
        """初始化触发器管理器"""
        self.file_watchers: Dict[str, FileWatcher] = {}
        self.triggers: Dict[str, Dict[str, Any]] = {}
        self.is_running = False
        
        logger.info("触发器管理器初始化完成")
    
    def add_file_trigger(self, trigger_id: str, repo_path: str, 
                        callback: Callable, ignore_patterns: List[str] = None,
                        debounce_seconds: float = 5.0) -> bool:
        """
        添加文件变更触发器
        
        Args:
            trigger_id: 触发器ID
            repo_path: 仓库路径
            callback: 回调函数
            ignore_patterns: 忽略模式列表
            debounce_seconds: 防抖时间
            
        Returns:
            是否添加成功
        """
        try:
            if trigger_id in self.triggers:
                logger.warning(f"触发器 {trigger_id} 已存在，将被替换")
                self.remove_trigger(trigger_id)
            
            # 创建文件监控器
            watcher = FileWatcher(
                repo_path=repo_path,
                ignore_patterns=ignore_patterns,
                debounce_seconds=debounce_seconds
            )
            
            # 启动监控
            if watcher.start_monitoring(callback):
                self.file_watchers[trigger_id] = watcher
                self.triggers[trigger_id] = {
                    'type': 'file_change',
                    'repo_path': repo_path,
                    'callback': callback,
                    'watcher': watcher,
                    'created_at': None  # 可以添加时间戳
                }
                
                logger.info(f"文件触发器添加成功: {trigger_id}")
                return True
            else:
                logger.error(f"启动文件监控失败: {trigger_id}")
                return False
                
        except Exception as e:
            logger.error(f"添加文件触发器失败: {e}")
            return False
    
    def remove_trigger(self, trigger_id: str) -> bool:
        """
        移除触发器
        
        Args:
            trigger_id: 触发器ID
            
        Returns:
            是否移除成功
        """
        try:
            if trigger_id not in self.triggers:
                logger.warning(f"触发器不存在: {trigger_id}")
                return False
            
            trigger_info = self.triggers[trigger_id]
            
            # 停止文件监控器
            if trigger_info['type'] == 'file_change':
                watcher = trigger_info['watcher']
                watcher.stop_monitoring()
                
                if trigger_id in self.file_watchers:
                    del self.file_watchers[trigger_id]
            
            # 移除触发器记录
            del self.triggers[trigger_id]
            
            logger.info(f"触发器已移除: {trigger_id}")
            return True
            
        except Exception as e:
            logger.error(f"移除触发器失败: {e}")
            return False
    
    def start(self) -> bool:
        """
        启动触发器管理器
        
        Returns:
            是否启动成功
        """
        try:
            if self.is_running:
                logger.warning("触发器管理器已在运行")
                return True
            
            # 启动所有文件监控器
            for trigger_id, watcher in self.file_watchers.items():
                if not watcher.is_monitoring:
                    trigger_info = self.triggers[trigger_id]
                    watcher.start_monitoring(trigger_info['callback'])
            
            self.is_running = True
            logger.info("触发器管理器已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动触发器管理器失败: {e}")
            return False
    
    def stop(self) -> bool:
        """
        停止触发器管理器
        
        Returns:
            是否停止成功
        """
        try:
            if not self.is_running:
                logger.warning("触发器管理器未在运行")
                return True
            
            # 停止所有文件监控器
            for watcher in self.file_watchers.values():
                watcher.stop_monitoring()
            
            self.is_running = False
            logger.info("触发器管理器已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止触发器管理器失败: {e}")
            return False
    
    def pause_trigger(self, trigger_id: str) -> bool:
        """
        暂停触发器
        
        Args:
            trigger_id: 触发器ID
            
        Returns:
            是否暂停成功
        """
        try:
            if trigger_id not in self.triggers:
                logger.warning(f"触发器不存在: {trigger_id}")
                return False
            
            trigger_info = self.triggers[trigger_id]
            
            if trigger_info['type'] == 'file_change':
                watcher = trigger_info['watcher']
                watcher.pause_monitoring()
            
            logger.info(f"触发器已暂停: {trigger_id}")
            return True
            
        except Exception as e:
            logger.error(f"暂停触发器失败: {e}")
            return False
    
    def resume_trigger(self, trigger_id: str) -> bool:
        """
        恢复触发器
        
        Args:
            trigger_id: 触发器ID
            
        Returns:
            是否恢复成功
        """
        try:
            if trigger_id not in self.triggers:
                logger.warning(f"触发器不存在: {trigger_id}")
                return False
            
            trigger_info = self.triggers[trigger_id]
            
            if trigger_info['type'] == 'file_change':
                watcher = trigger_info['watcher']
                watcher.resume_monitoring()
            
            logger.info(f"触发器已恢复: {trigger_id}")
            return True
            
        except Exception as e:
            logger.error(f"恢复触发器失败: {e}")
            return False
    
    def get_trigger_list(self) -> List[Dict[str, Any]]:
        """
        获取触发器列表
        
        Returns:
            触发器信息列表
        """
        triggers = []
        
        for trigger_id, trigger_info in self.triggers.items():
            info = {
                'id': trigger_id,
                'type': trigger_info['type'],
                'created_at': trigger_info.get('created_at')
            }
            
            if trigger_info['type'] == 'file_change':
                watcher = trigger_info['watcher']
                status = watcher.get_status()
                info.update({
                    'repo_path': trigger_info['repo_path'],
                    'is_monitoring': status['is_monitoring'],
                    'is_paused': status['is_paused'],
                    'pending_changes': status['pending_changes']
                })
            
            triggers.append(info)
        
        return triggers
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取触发器管理器状态
        
        Returns:
            状态信息字典
        """
        return {
            'is_running': self.is_running,
            'total_triggers': len(self.triggers),
            'file_triggers': len(self.file_watchers),
            'active_watchers': sum(
                1 for watcher in self.file_watchers.values()
                if watcher.is_monitoring
            )
        }
    
    def clear_all_triggers(self):
        """清空所有触发器"""
        try:
            # 停止所有监控器
            for watcher in self.file_watchers.values():
                watcher.stop_monitoring()
            
            # 清空记录
            self.file_watchers.clear()
            self.triggers.clear()
            
            logger.info("所有触发器已清空")
            
        except Exception as e:
            logger.error(f"清空触发器失败: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
