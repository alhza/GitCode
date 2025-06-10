"""
日志管理模块

提供统一的日志记录功能，支持文件轮转、格式化输出等。
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    def format(self, record):
        """格式化日志记录"""
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname}"
                f"{self.COLORS['RESET']}"
            )
        
        return super().format(record)


def setup_logging(log_level: str = "INFO", 
                 log_dir: str = "logs",
                 max_files: int = 10,
                 max_size: int = 10 * 1024 * 1024) -> None:
    """
    设置日志系统
    
    Args:
        log_level: 日志级别
        log_dir: 日志目录
        max_files: 最大日志文件数
        max_size: 单个日志文件最大大小（字节）
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建格式化器
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 文件处理器（轮转）
    log_file = log_path / "gitee_auto_commit.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_size,
        backupCount=max_files,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # 添加处理器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 记录启动信息
    logger = logging.getLogger(__name__)
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {log_level}")
    logger.info(f"日志目录: {log_path.absolute()}")


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        日志器实例
    """
    return logging.getLogger(name)


class LogManager:
    """日志管理器"""
    
    def __init__(self, log_dir: str = "logs"):
        """
        初始化日志管理器
        
        Args:
            log_dir: 日志目录
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.logger = get_logger(__name__)
    
    def get_log_files(self) -> list:
        """
        获取所有日志文件
        
        Returns:
            日志文件列表
        """
        try:
            log_files = []
            for file_path in self.log_dir.glob("*.log*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    log_files.append({
                        'name': file_path.name,
                        'path': str(file_path),
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime)
                    })
            
            # 按修改时间排序
            log_files.sort(key=lambda x: x['modified'], reverse=True)
            return log_files
            
        except Exception as e:
            self.logger.error(f"获取日志文件列表失败: {e}")
            return []
    
    def read_log_file(self, file_name: str, lines: int = 100) -> str:
        """
        读取日志文件内容
        
        Args:
            file_name: 日志文件名
            lines: 读取行数（从末尾开始）
            
        Returns:
            日志内容
        """
        try:
            log_file = self.log_dir / file_name
            if not log_file.exists():
                return f"日志文件 {file_name} 不存在"
            
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                
            # 返回最后N行
            if lines > 0:
                return ''.join(all_lines[-lines:])
            else:
                return ''.join(all_lines)
                
        except Exception as e:
            self.logger.error(f"读取日志文件失败: {e}")
            return f"读取日志文件失败: {e}"
    
    def clear_old_logs(self, days: int = 30) -> bool:
        """
        清理旧日志文件
        
        Args:
            days: 保留天数
            
        Returns:
            是否清理成功
        """
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            for file_path in self.log_dir.glob("*.log*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    if datetime.fromtimestamp(stat.st_mtime) < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
            
            self.logger.info(f"清理了 {deleted_count} 个旧日志文件")
            return True
            
        except Exception as e:
            self.logger.error(f"清理旧日志文件失败: {e}")
            return False
    
    def export_logs(self, export_path: str, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> bool:
        """
        导出日志文件
        
        Args:
            export_path: 导出路径
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            是否导出成功
        """
        try:
            import zipfile
            
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in self.log_dir.glob("*.log*"):
                    if file_path.is_file():
                        # 检查日期范围
                        if start_date or end_date:
                            stat = file_path.stat()
                            file_time = datetime.fromtimestamp(stat.st_mtime)
                            
                            if start_date and file_time < start_date:
                                continue
                            if end_date and file_time > end_date:
                                continue
                        
                        zipf.write(file_path, file_path.name)
            
            self.logger.info(f"日志文件导出成功: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出日志文件失败: {e}")
            return False
    
    def get_log_stats(self) -> dict:
        """
        获取日志统计信息
        
        Returns:
            统计信息字典
        """
        try:
            stats = {
                'total_files': 0,
                'total_size': 0,
                'oldest_file': None,
                'newest_file': None,
                'error_count': 0,
                'warning_count': 0
            }
            
            log_files = self.get_log_files()
            if not log_files:
                return stats
            
            stats['total_files'] = len(log_files)
            stats['total_size'] = sum(f['size'] for f in log_files)
            stats['oldest_file'] = log_files[-1]['modified']
            stats['newest_file'] = log_files[0]['modified']
            
            # 统计错误和警告数量（仅主日志文件）
            main_log = self.log_dir / "gitee_auto_commit.log"
            if main_log.exists():
                with open(main_log, 'r', encoding='utf-8') as f:
                    content = f.read()
                    stats['error_count'] = content.count(' - ERROR - ')
                    stats['warning_count'] = content.count(' - WARNING - ')
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取日志统计信息失败: {e}")
            return {
                'total_files': 0,
                'total_size': 0,
                'oldest_file': None,
                'newest_file': None,
                'error_count': 0,
                'warning_count': 0
            }
