"""
文件监控器

使用watchdog库实现实时文件系统监控，支持文件过滤和防抖处理。
"""

import os
import time
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import fnmatch
import logging

from ..utils.logger import get_logger
from .change_detector import ChangeDetector

logger = get_logger(__name__)


class GitFileEventHandler(FileSystemEventHandler):
    """Git文件事件处理器"""
    
    def __init__(self, file_watcher: 'FileWatcher'):
        """
        初始化事件处理器
        
        Args:
            file_watcher: 文件监控器实例
        """
        super().__init__()
        self.file_watcher = file_watcher
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def on_any_event(self, event: FileSystemEvent):
        """处理任何文件系统事件"""
        if event.is_directory:
            return
        
        # 过滤文件
        if not self.file_watcher.should_monitor_file(event.src_path):
            return
        
        self.logger.debug(f"文件事件: {event.event_type} - {event.src_path}")
        
        # 添加到变更队列
        self.file_watcher.add_change(event.src_path, event.event_type)
    
    def on_moved(self, event):
        """处理文件移动事件"""
        if event.is_directory:
            return
        
        # 处理源文件和目标文件
        if hasattr(event, 'dest_path'):
            if self.file_watcher.should_monitor_file(event.src_path):
                self.file_watcher.add_change(event.src_path, 'deleted')
            
            if self.file_watcher.should_monitor_file(event.dest_path):
                self.file_watcher.add_change(event.dest_path, 'created')


class FileWatcher:
    """文件监控器类"""
    
    def __init__(self, repo_path: str, ignore_patterns: List[str] = None,
                 debounce_seconds: float = 5.0):
        """
        初始化文件监控器
        
        Args:
            repo_path: 仓库路径
            ignore_patterns: 忽略模式列表
            debounce_seconds: 防抖时间（秒）
        """
        self.repo_path = Path(repo_path)
        self.ignore_patterns = ignore_patterns or []
        self.debounce_seconds = debounce_seconds
        
        # 添加默认忽略模式
        self.ignore_patterns.extend([
            '.git/*',
            '.git/**/*',
            '*.pyc',
            '__pycache__/*',
            '__pycache__/**/*',
            '*.log',
            '*.tmp',
            '.DS_Store',
            'Thumbs.db'
        ])
        
        self.observer = Observer()
        self.event_handler = GitFileEventHandler(self)
        self.change_detector = ChangeDetector()
        
        # 变更管理
        self.pending_changes: Dict[str, Dict[str, Any]] = {}
        self.change_lock = threading.Lock()
        self.debounce_timer: Optional[threading.Timer] = None
        
        # 回调函数
        self.on_changes_callback: Optional[Callable] = None
        
        # 状态管理
        self.is_monitoring = False
        self.is_paused = False
        
        logger.info(f"文件监控器初始化: {self.repo_path}")
    
    def should_monitor_file(self, file_path: str) -> bool:
        """
        检查是否应该监控指定文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否应该监控
        """
        try:
            # 转换为相对路径
            rel_path = os.path.relpath(file_path, self.repo_path)
            
            # 检查忽略模式
            for pattern in self.ignore_patterns:
                if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(file_path, pattern):
                    return False
            
            # 检查是否在Git仓库内
            if not str(Path(file_path)).startswith(str(self.repo_path)):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查文件监控条件失败: {e}")
            return False
    
    def add_change(self, file_path: str, event_type: str):
        """
        添加文件变更到队列
        
        Args:
            file_path: 文件路径
            event_type: 事件类型
        """
        if self.is_paused:
            return
        
        with self.change_lock:
            # 记录变更信息
            self.pending_changes[file_path] = {
                'event_type': event_type,
                'timestamp': time.time(),
                'path': file_path
            }
            
            # 重置防抖计时器
            if self.debounce_timer:
                self.debounce_timer.cancel()
            
            self.debounce_timer = threading.Timer(
                self.debounce_seconds, 
                self._process_changes
            )
            self.debounce_timer.start()
    
    def _process_changes(self):
        """处理累积的文件变更"""
        with self.change_lock:
            if not self.pending_changes:
                return
            
            changes = list(self.pending_changes.values())
            self.pending_changes.clear()
            
            logger.info(f"处理 {len(changes)} 个文件变更")
            
            # 调用回调函数
            if self.on_changes_callback:
                try:
                    self.on_changes_callback(changes)
                except Exception as e:
                    logger.error(f"处理变更回调失败: {e}")
    
    def start_monitoring(self, callback: Optional[Callable] = None) -> bool:
        """
        开始监控文件变更
        
        Args:
            callback: 变更回调函数
            
        Returns:
            是否启动成功
        """
        try:
            if self.is_monitoring:
                logger.warning("文件监控已在运行")
                return True
            
            if not self.repo_path.exists():
                logger.error(f"监控路径不存在: {self.repo_path}")
                return False
            
            self.on_changes_callback = callback
            
            # 启动监控
            self.observer.schedule(
                self.event_handler,
                str(self.repo_path),
                recursive=True
            )
            self.observer.start()
            self.is_monitoring = True
            
            logger.info(f"文件监控已启动: {self.repo_path}")
            return True
            
        except Exception as e:
            logger.error(f"启动文件监控失败: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """
        停止监控文件变更
        
        Returns:
            是否停止成功
        """
        try:
            if not self.is_monitoring:
                logger.warning("文件监控未在运行")
                return True
            
            # 停止观察者
            self.observer.stop()
            self.observer.join(timeout=5.0)
            
            # 取消防抖计时器
            if self.debounce_timer:
                self.debounce_timer.cancel()
                self.debounce_timer = None
            
            # 处理剩余变更
            self._process_changes()
            
            self.is_monitoring = False
            logger.info("文件监控已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止文件监控失败: {e}")
            return False
    
    def pause_monitoring(self):
        """暂停监控"""
        self.is_paused = True
        logger.info("文件监控已暂停")
    
    def resume_monitoring(self):
        """恢复监控"""
        self.is_paused = False
        logger.info("文件监控已恢复")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取监控状态
        
        Returns:
            状态信息字典
        """
        with self.change_lock:
            return {
                'is_monitoring': self.is_monitoring,
                'is_paused': self.is_paused,
                'repo_path': str(self.repo_path),
                'pending_changes': len(self.pending_changes),
                'ignore_patterns': self.ignore_patterns.copy(),
                'debounce_seconds': self.debounce_seconds
            }
    
    def get_pending_changes(self) -> List[Dict[str, Any]]:
        """
        获取待处理的变更列表
        
        Returns:
            变更列表
        """
        with self.change_lock:
            return list(self.pending_changes.values())
    
    def clear_pending_changes(self):
        """清空待处理的变更"""
        with self.change_lock:
            self.pending_changes.clear()
            if self.debounce_timer:
                self.debounce_timer.cancel()
                self.debounce_timer = None
        
        logger.info("已清空待处理的变更")
    
    def add_ignore_pattern(self, pattern: str):
        """
        添加忽略模式
        
        Args:
            pattern: 忽略模式
        """
        if pattern not in self.ignore_patterns:
            self.ignore_patterns.append(pattern)
            logger.info(f"添加忽略模式: {pattern}")
    
    def remove_ignore_pattern(self, pattern: str):
        """
        移除忽略模式
        
        Args:
            pattern: 忽略模式
        """
        if pattern in self.ignore_patterns:
            self.ignore_patterns.remove(pattern)
            logger.info(f"移除忽略模式: {pattern}")
    
    def set_debounce_time(self, seconds: float):
        """
        设置防抖时间
        
        Args:
            seconds: 防抖时间（秒）
        """
        self.debounce_seconds = seconds
        logger.info(f"防抖时间设置为: {seconds}秒")
    
    def force_process_changes(self):
        """强制处理当前的变更"""
        if self.debounce_timer:
            self.debounce_timer.cancel()
        self._process_changes()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_monitoring()
