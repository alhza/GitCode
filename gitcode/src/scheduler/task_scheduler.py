"""
任务调度器

管理定时任务和事件驱动任务的执行。
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
import logging

from ..utils.logger import get_logger

# 暂时注释掉schedule和trigger_manager的导入，稍后实现
# import schedule
# from .trigger_manager import TriggerManager

logger = get_logger(__name__)


class TaskScheduler:
    """任务调度器类"""

    def __init__(self):
        """初始化任务调度器"""
        # self.trigger_manager = TriggerManager()  # 暂时注释
        self.scheduled_jobs: Dict[str, Any] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}

        # 调度器状态
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # 任务统计
        self.task_stats = {
            'total_executed': 0,
            'successful': 0,
            'failed': 0,
            'last_execution': None
        }

        logger.info("任务调度器初始化完成")
    
    def schedule_periodic(self, task_id: str, func: Callable, 
                         interval_type: str, interval_value: int,
                         time_str: str = None, **kwargs) -> bool:
        """
        调度周期性任务
        
        Args:
            task_id: 任务ID
            func: 要执行的函数
            interval_type: 间隔类型 ('minutes', 'hours', 'days', 'weeks')
            interval_value: 间隔值
            time_str: 执行时间 (HH:MM格式，仅对daily有效)
            **kwargs: 传递给函数的参数
            
        Returns:
            是否调度成功
        """
        try:
            # 取消现有任务
            if task_id in self.scheduled_jobs:
                self.cancel_task(task_id)
            
            # 创建新任务
            if interval_type == 'minutes':
                job = schedule.every(interval_value).minutes.do(
                    self._execute_task, task_id, func, **kwargs
                )
            elif interval_type == 'hours':
                job = schedule.every(interval_value).hours.do(
                    self._execute_task, task_id, func, **kwargs
                )
            elif interval_type == 'days':
                if time_str:
                    job = schedule.every(interval_value).days.at(time_str).do(
                        self._execute_task, task_id, func, **kwargs
                    )
                else:
                    job = schedule.every(interval_value).days.do(
                        self._execute_task, task_id, func, **kwargs
                    )
            elif interval_type == 'weeks':
                job = schedule.every(interval_value).weeks.do(
                    self._execute_task, task_id, func, **kwargs
                )
            else:
                logger.error(f"不支持的间隔类型: {interval_type}")
                return False
            
            # 记录任务信息
            self.scheduled_jobs[task_id] = {
                'job': job,
                'func': func,
                'interval_type': interval_type,
                'interval_value': interval_value,
                'time_str': time_str,
                'kwargs': kwargs,
                'created_at': datetime.now(),
                'last_run': None,
                'run_count': 0
            }
            
            logger.info(f"任务调度成功: {task_id} ({interval_type}={interval_value})")
            return True
            
        except Exception as e:
            logger.error(f"调度任务失败: {e}")
            return False
    
    def schedule_daily(self, task_id: str, func: Callable, 
                      time_str: str, **kwargs) -> bool:
        """
        调度每日任务
        
        Args:
            task_id: 任务ID
            func: 要执行的函数
            time_str: 执行时间 (HH:MM格式)
            **kwargs: 传递给函数的参数
            
        Returns:
            是否调度成功
        """
        return self.schedule_periodic(task_id, func, 'days', 1, time_str, **kwargs)
    
    def schedule_weekly(self, task_id: str, func: Callable, 
                       day_of_week: str, time_str: str, **kwargs) -> bool:
        """
        调度每周任务
        
        Args:
            task_id: 任务ID
            func: 要执行的函数
            day_of_week: 星期几 ('monday', 'tuesday', etc.)
            time_str: 执行时间 (HH:MM格式)
            **kwargs: 传递给函数的参数
            
        Returns:
            是否调度成功
        """
        try:
            # 取消现有任务
            if task_id in self.scheduled_jobs:
                self.cancel_task(task_id)
            
            # 创建每周任务
            job = getattr(schedule.every(), day_of_week.lower()).at(time_str).do(
                self._execute_task, task_id, func, **kwargs
            )
            
            # 记录任务信息
            self.scheduled_jobs[task_id] = {
                'job': job,
                'func': func,
                'interval_type': 'weekly',
                'day_of_week': day_of_week,
                'time_str': time_str,
                'kwargs': kwargs,
                'created_at': datetime.now(),
                'last_run': None,
                'run_count': 0
            }
            
            logger.info(f"每周任务调度成功: {task_id} ({day_of_week} {time_str})")
            return True
            
        except Exception as e:
            logger.error(f"调度每周任务失败: {e}")
            return False
    
    def schedule_on_change(self, task_id: str, func: Callable, 
                          repo_path: str, **kwargs) -> bool:
        """
        调度文件变更触发任务
        
        Args:
            task_id: 任务ID
            func: 要执行的函数
            repo_path: 监控的仓库路径
            **kwargs: 传递给函数的参数
            
        Returns:
            是否调度成功
        """
        try:
            # 创建变更触发器
            trigger_func = lambda changes: self._execute_task(
                task_id, func, changes=changes, **kwargs
            )
            
            success = self.trigger_manager.add_file_trigger(
                task_id, repo_path, trigger_func
            )
            
            if success:
                # 记录任务信息
                self.scheduled_jobs[task_id] = {
                    'type': 'file_change',
                    'func': func,
                    'repo_path': repo_path,
                    'kwargs': kwargs,
                    'created_at': datetime.now(),
                    'last_run': None,
                    'run_count': 0
                }
                
                logger.info(f"文件变更任务调度成功: {task_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"调度文件变更任务失败: {e}")
            return False
    
    def _execute_task(self, task_id: str, func: Callable, **kwargs):
        """
        执行任务
        
        Args:
            task_id: 任务ID
            func: 要执行的函数
            **kwargs: 传递给函数的参数
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始执行任务: {task_id}")
            
            # 更新任务统计
            self.task_stats['total_executed'] += 1
            self.task_stats['last_execution'] = start_time
            
            if task_id in self.scheduled_jobs:
                self.scheduled_jobs[task_id]['last_run'] = start_time
                self.scheduled_jobs[task_id]['run_count'] += 1
            
            # 执行任务
            result = func(**kwargs)
            
            # 记录成功
            self.task_stats['successful'] += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"任务执行成功: {task_id} (耗时: {execution_time:.2f}秒)")
            
            return result
            
        except Exception as e:
            # 记录失败
            self.task_stats['failed'] += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.error(f"任务执行失败: {task_id} (耗时: {execution_time:.2f}秒) - {e}")
            
        finally:
            # 清理运行中的任务记录
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def execute_once(self, task_id: str, func: Callable, **kwargs) -> bool:
        """
        立即执行一次任务
        
        Args:
            task_id: 任务ID
            func: 要执行的函数
            **kwargs: 传递给函数的参数
            
        Returns:
            是否启动成功
        """
        try:
            if task_id in self.running_tasks:
                logger.warning(f"任务 {task_id} 正在运行中")
                return False
            
            # 在新线程中执行任务
            thread = threading.Thread(
                target=self._execute_task,
                args=(task_id, func),
                kwargs=kwargs,
                name=f"Task-{task_id}"
            )
            
            self.running_tasks[task_id] = thread
            thread.start()
            
            logger.info(f"任务已启动: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"启动任务失败: {e}")
            return False
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        try:
            success = False
            
            # 取消定时任务
            if task_id in self.scheduled_jobs:
                job_info = self.scheduled_jobs[task_id]
                
                if 'job' in job_info:
                    # 定时任务
                    schedule.cancel_job(job_info['job'])
                    success = True
                elif job_info.get('type') == 'file_change':
                    # 文件变更任务
                    success = self.trigger_manager.remove_trigger(task_id)
                
                del self.scheduled_jobs[task_id]
            
            # 停止运行中的任务
            if task_id in self.running_tasks:
                thread = self.running_tasks[task_id]
                if thread.is_alive():
                    # 注意：Python线程无法强制终止，只能等待自然结束
                    logger.warning(f"任务 {task_id} 正在运行，无法强制停止")
                del self.running_tasks[task_id]
                success = True
            
            if success:
                logger.info(f"任务已取消: {task_id}")
            else:
                logger.warning(f"任务不存在: {task_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False
    
    def start_scheduler(self) -> bool:
        """
        启动调度器
        
        Returns:
            是否启动成功
        """
        try:
            if self.is_running:
                logger.warning("调度器已在运行")
                return True
            
            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._run_scheduler,
                name="TaskScheduler"
            )
            self.scheduler_thread.start()
            self.is_running = True
            
            # 启动触发器管理器
            self.trigger_manager.start()
            
            logger.info("任务调度器已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            return False
    
    def stop_scheduler(self) -> bool:
        """
        停止调度器
        
        Returns:
            是否停止成功
        """
        try:
            if not self.is_running:
                logger.warning("调度器未在运行")
                return True
            
            # 停止调度器线程
            self.stop_event.set()
            if self.scheduler_thread:
                self.scheduler_thread.join(timeout=5.0)
            
            # 停止触发器管理器
            self.trigger_manager.stop()
            
            self.is_running = False
            logger.info("任务调度器已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
            return False
    
    def _run_scheduler(self):
        """调度器主循环"""
        logger.info("调度器主循环开始")
        
        while not self.stop_event.is_set():
            try:
                # 运行待执行的任务
                schedule.run_pending()
                
                # 短暂休眠
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"调度器运行错误: {e}")
                time.sleep(5)  # 错误后稍长休眠
        
        logger.info("调度器主循环结束")
    
    def get_task_list(self) -> List[Dict[str, Any]]:
        """
        获取任务列表
        
        Returns:
            任务信息列表
        """
        tasks = []
        
        for task_id, job_info in self.scheduled_jobs.items():
            task_info = {
                'id': task_id,
                'created_at': job_info['created_at'],
                'last_run': job_info['last_run'],
                'run_count': job_info['run_count'],
                'is_running': task_id in self.running_tasks
            }
            
            if 'job' in job_info:
                # 定时任务
                task_info.update({
                    'type': 'scheduled',
                    'interval_type': job_info['interval_type'],
                    'interval_value': job_info.get('interval_value'),
                    'time_str': job_info.get('time_str'),
                    'next_run': job_info['job'].next_run
                })
            elif job_info.get('type') == 'file_change':
                # 文件变更任务
                task_info.update({
                    'type': 'file_change',
                    'repo_path': job_info['repo_path']
                })
            
            tasks.append(task_info)
        
        return tasks
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        获取调度器状态
        
        Returns:
            状态信息字典
        """
        return {
            'is_running': self.is_running,
            'scheduled_tasks': len(self.scheduled_jobs),
            'running_tasks': len(self.running_tasks),
            'statistics': self.task_stats.copy(),
            'trigger_manager_status': self.trigger_manager.get_status()
        }
    
    def clear_statistics(self):
        """清空任务统计"""
        self.task_stats = {
            'total_executed': 0,
            'successful': 0,
            'failed': 0,
            'last_execution': None
        }
        logger.info("任务统计已清空")
