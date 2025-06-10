"""
变更检测器

分析文件变更模式，提供智能的变更分类和处理建议。
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set, Optional, Tuple
from datetime import datetime, timedelta
import logging

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ChangeDetector:
    """变更检测器类"""
    
    def __init__(self):
        """初始化变更检测器"""
        self.file_hashes: Dict[str, str] = {}
        self.change_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # 文件类型分类
        self.file_categories = {
            'source': ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go'],
            'config': ['.json', '.yaml', '.yml', '.ini', '.conf', '.cfg', '.env'],
            'docs': ['.md', '.txt', '.rst', '.doc', '.docx', '.pdf'],
            'web': ['.html', '.css', '.scss', '.less', '.vue', '.jsx', '.tsx'],
            'data': ['.sql', '.csv', '.xml', '.xlsx', '.db'],
            'media': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.mp4', '.mp3'],
            'build': ['Makefile', 'Dockerfile', '.gitignore', 'requirements.txt', 'package.json']
        }
        
        logger.info("变更检测器初始化完成")
    
    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """
        计算文件哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件哈希值或None
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {e}")
            return None
    
    def detect_changes(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        检测文件变更
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            变更检测结果
        """
        try:
            changes = {
                'modified': [],
                'added': [],
                'deleted': [],
                'unchanged': [],
                'summary': {}
            }
            
            current_files = set()
            
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    # 文件已删除
                    if file_path in self.file_hashes:
                        changes['deleted'].append(file_path)
                        del self.file_hashes[file_path]
                    continue
                
                current_files.add(file_path)
                current_hash = self.calculate_file_hash(file_path)
                
                if current_hash is None:
                    continue
                
                if file_path in self.file_hashes:
                    # 检查是否修改
                    if self.file_hashes[file_path] != current_hash:
                        changes['modified'].append(file_path)
                        self.file_hashes[file_path] = current_hash
                    else:
                        changes['unchanged'].append(file_path)
                else:
                    # 新文件
                    changes['added'].append(file_path)
                    self.file_hashes[file_path] = current_hash
            
            # 检查已删除的文件
            stored_files = set(self.file_hashes.keys())
            for file_path in stored_files - current_files:
                if not os.path.exists(file_path):
                    changes['deleted'].append(file_path)
                    del self.file_hashes[file_path]
            
            # 生成摘要
            changes['summary'] = self._generate_change_summary(changes)
            
            # 记录变更历史
            self._record_change_history(changes)
            
            return changes
            
        except Exception as e:
            logger.error(f"检测文件变更失败: {e}")
            return {
                'modified': [],
                'added': [],
                'deleted': [],
                'unchanged': [],
                'summary': {},
                'error': str(e)
            }
    
    def _generate_change_summary(self, changes: Dict[str, List[str]]) -> Dict[str, Any]:
        """生成变更摘要"""
        summary = {
            'total_changes': len(changes['modified']) + len(changes['added']) + len(changes['deleted']),
            'modified_count': len(changes['modified']),
            'added_count': len(changes['added']),
            'deleted_count': len(changes['deleted']),
            'categories': {},
            'change_type': 'mixed'
        }
        
        # 按文件类型分类
        all_changed_files = changes['modified'] + changes['added'] + changes['deleted']
        for file_path in all_changed_files:
            category = self._get_file_category(file_path)
            summary['categories'][category] = summary['categories'].get(category, 0) + 1
        
        # 确定主要变更类型
        if summary['added_count'] > 0 and summary['modified_count'] == 0 and summary['deleted_count'] == 0:
            summary['change_type'] = 'addition'
        elif summary['modified_count'] > 0 and summary['added_count'] == 0 and summary['deleted_count'] == 0:
            summary['change_type'] = 'modification'
        elif summary['deleted_count'] > 0 and summary['added_count'] == 0 and summary['modified_count'] == 0:
            summary['change_type'] = 'deletion'
        elif summary['added_count'] > summary['modified_count'] + summary['deleted_count']:
            summary['change_type'] = 'feature'
        else:
            summary['change_type'] = 'mixed'
        
        return summary
    
    def _get_file_category(self, file_path: str) -> str:
        """获取文件类别"""
        path = Path(file_path)
        ext = path.suffix.lower()
        name = path.name.lower()
        
        for category, extensions in self.file_categories.items():
            if ext in extensions or name in extensions:
                return category
        
        return 'other'
    
    def _record_change_history(self, changes: Dict[str, Any]):
        """记录变更历史"""
        history_entry = {
            'timestamp': datetime.now(),
            'summary': changes['summary'].copy(),
            'files': {
                'modified': len(changes['modified']),
                'added': len(changes['added']),
                'deleted': len(changes['deleted'])
            }
        }
        
        self.change_history.append(history_entry)
        
        # 限制历史记录大小
        if len(self.change_history) > self.max_history_size:
            self.change_history = self.change_history[-self.max_history_size:]
    
    def analyze_change_pattern(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        分析变更模式
        
        Args:
            time_window_hours: 时间窗口（小时）
            
        Returns:
            变更模式分析结果
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            recent_changes = [
                change for change in self.change_history
                if change['timestamp'] > cutoff_time
            ]
            
            if not recent_changes:
                return {'pattern': 'no_activity', 'confidence': 1.0}
            
            # 分析变更频率
            total_changes = sum(
                change['summary']['total_changes'] 
                for change in recent_changes
            )
            
            avg_changes_per_hour = total_changes / time_window_hours
            
            # 分析变更类型分布
            type_counts = {}
            for change in recent_changes:
                change_type = change['summary']['change_type']
                type_counts[change_type] = type_counts.get(change_type, 0) + 1
            
            dominant_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else 'mixed'
            
            # 确定模式
            if avg_changes_per_hour > 10:
                pattern = 'high_activity'
            elif avg_changes_per_hour > 3:
                pattern = 'moderate_activity'
            elif avg_changes_per_hour > 0.5:
                pattern = 'low_activity'
            else:
                pattern = 'minimal_activity'
            
            return {
                'pattern': pattern,
                'dominant_type': dominant_type,
                'avg_changes_per_hour': avg_changes_per_hour,
                'total_changes': total_changes,
                'change_sessions': len(recent_changes),
                'confidence': min(len(recent_changes) / 10, 1.0)
            }
            
        except Exception as e:
            logger.error(f"分析变更模式失败: {e}")
            return {'pattern': 'unknown', 'confidence': 0.0, 'error': str(e)}
    
    def suggest_commit_strategy(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        建议提交策略
        
        Args:
            changes: 变更信息
            
        Returns:
            提交策略建议
        """
        try:
            summary = changes.get('summary', {})
            total_changes = summary.get('total_changes', 0)
            change_type = summary.get('change_type', 'mixed')
            categories = summary.get('categories', {})
            
            # 基于变更数量的建议
            if total_changes == 0:
                return {
                    'strategy': 'no_commit',
                    'reason': '没有变更需要提交',
                    'confidence': 1.0
                }
            elif total_changes > 50:
                return {
                    'strategy': 'batch_commit',
                    'reason': '变更文件过多，建议分批提交',
                    'confidence': 0.8,
                    'suggested_batches': (total_changes + 19) // 20  # 每批20个文件
                }
            
            # 基于变更类型的建议
            if change_type == 'addition' and 'source' in categories:
                return {
                    'strategy': 'feature_commit',
                    'reason': '检测到新功能开发',
                    'confidence': 0.9,
                    'suggested_message_type': 'feat'
                }
            elif change_type == 'modification' and len(categories) == 1:
                category = list(categories.keys())[0]
                return {
                    'strategy': 'focused_commit',
                    'reason': f'专注于{category}文件的修改',
                    'confidence': 0.8,
                    'suggested_message_type': 'fix' if category == 'source' else 'chore'
                }
            elif 'docs' in categories and len(categories) == 1:
                return {
                    'strategy': 'docs_commit',
                    'reason': '仅文档变更',
                    'confidence': 0.9,
                    'suggested_message_type': 'docs'
                }
            elif 'config' in categories and total_changes <= 5:
                return {
                    'strategy': 'config_commit',
                    'reason': '配置文件变更',
                    'confidence': 0.8,
                    'suggested_message_type': 'chore'
                }
            else:
                return {
                    'strategy': 'standard_commit',
                    'reason': '标准提交',
                    'confidence': 0.7,
                    'suggested_message_type': 'chore'
                }
                
        except Exception as e:
            logger.error(f"建议提交策略失败: {e}")
            return {
                'strategy': 'standard_commit',
                'reason': '默认策略',
                'confidence': 0.5,
                'error': str(e)
            }
    
    def get_change_statistics(self) -> Dict[str, Any]:
        """
        获取变更统计信息
        
        Returns:
            统计信息字典
        """
        try:
            if not self.change_history:
                return {
                    'total_sessions': 0,
                    'total_changes': 0,
                    'avg_changes_per_session': 0,
                    'most_active_category': None,
                    'change_trend': 'stable'
                }
            
            total_sessions = len(self.change_history)
            total_changes = sum(
                change['summary']['total_changes'] 
                for change in self.change_history
            )
            
            # 计算类别统计
            category_counts = {}
            for change in self.change_history:
                for category, count in change['summary'].get('categories', {}).items():
                    category_counts[category] = category_counts.get(category, 0) + count
            
            most_active_category = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None
            
            # 分析趋势（最近10次 vs 之前10次）
            recent_changes = self.change_history[-10:]
            previous_changes = self.change_history[-20:-10] if len(self.change_history) >= 20 else []
            
            recent_avg = sum(c['summary']['total_changes'] for c in recent_changes) / len(recent_changes) if recent_changes else 0
            previous_avg = sum(c['summary']['total_changes'] for c in previous_changes) / len(previous_changes) if previous_changes else 0
            
            if recent_avg > previous_avg * 1.2:
                trend = 'increasing'
            elif recent_avg < previous_avg * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            return {
                'total_sessions': total_sessions,
                'total_changes': total_changes,
                'avg_changes_per_session': total_changes / total_sessions if total_sessions > 0 else 0,
                'most_active_category': most_active_category,
                'category_distribution': category_counts,
                'change_trend': trend,
                'recent_activity': recent_avg,
                'tracked_files': len(self.file_hashes)
            }
            
        except Exception as e:
            logger.error(f"获取变更统计失败: {e}")
            return {
                'total_sessions': 0,
                'total_changes': 0,
                'error': str(e)
            }
    
    def clear_history(self):
        """清空变更历史"""
        self.change_history.clear()
        logger.info("变更历史已清空")
    
    def reset_file_tracking(self):
        """重置文件跟踪"""
        self.file_hashes.clear()
        logger.info("文件跟踪已重置")
