"""
Gitee自动提交工具

一个功能完善的Gitee自动提交工具，支持文件监控、定时提交、智能消息生成等功能。
"""

__version__ = "1.0.0"
__author__ = "Gitee Auto Commit Team"
__email__ = "support@gitee-auto-commit.com"
__description__ = "Gitee自动提交工具 - 提高开发效率的Git自动化工具"

# 导出主要类和函数
from .config.config_manager import ConfigManager
from .git_ops.git_handler import GitHandler

# 尝试导入可选模块
try:
    from .monitor.file_watcher import FileWatcher
    from .scheduler.task_scheduler import TaskScheduler
    MONITOR_AVAILABLE = True
except ImportError:
    MONITOR_AVAILABLE = False
    FileWatcher = None
    TaskScheduler = None

__all__ = [
    "ConfigManager",
    "GitHandler",
]

if MONITOR_AVAILABLE:
    __all__.extend(["FileWatcher", "TaskScheduler"])
