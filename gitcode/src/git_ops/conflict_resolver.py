"""
Git冲突解决器

提供自动和半自动的Git冲突解决功能。
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConflictResolver:
    """Git冲突解决器类"""
    
    def __init__(self):
        """初始化冲突解决器"""
        # 冲突标记模式
        self.conflict_start_pattern = re.compile(r'^<{7} (.+)$', re.MULTILINE)
        self.conflict_middle_pattern = re.compile(r'^={7}$', re.MULTILINE)
        self.conflict_end_pattern = re.compile(r'^>{7} (.+)$', re.MULTILINE)
        
        # 简单冲突解决策略
        self.resolution_strategies = {
            'ours': self._resolve_with_ours,
            'theirs': self._resolve_with_theirs,
            'both': self._resolve_with_both,
            'smart': self._resolve_smart
        }
    
    def detect_conflicts(self, file_path: str) -> bool:
        """
        检测文件是否有冲突
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否有冲突
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return bool(self.conflict_start_pattern.search(content))
            
        except Exception as e:
            logger.error(f"检测冲突失败: {e}")
            return False
    
    def parse_conflicts(self, file_path: str) -> List[Dict[str, Any]]:
        """
        解析文件中的冲突
        
        Args:
            file_path: 文件路径
            
        Returns:
            冲突信息列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            conflicts = []
            lines = content.split('\n')
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # 查找冲突开始标记
                start_match = self.conflict_start_pattern.match(line)
                if start_match:
                    conflict = {
                        'start_line': i,
                        'ours_branch': start_match.group(1),
                        'ours_content': [],
                        'theirs_content': [],
                        'theirs_branch': None,
                        'end_line': None
                    }
                    
                    i += 1
                    
                    # 收集我们的内容
                    while i < len(lines) and not self.conflict_middle_pattern.match(lines[i]):
                        conflict['ours_content'].append(lines[i])
                        i += 1
                    
                    # 跳过分隔符
                    if i < len(lines) and self.conflict_middle_pattern.match(lines[i]):
                        i += 1
                    
                    # 收集他们的内容
                    while i < len(lines):
                        end_match = self.conflict_end_pattern.match(lines[i])
                        if end_match:
                            conflict['theirs_branch'] = end_match.group(1)
                            conflict['end_line'] = i
                            break
                        conflict['theirs_content'].append(lines[i])
                        i += 1
                    
                    conflicts.append(conflict)
                
                i += 1
            
            return conflicts
            
        except Exception as e:
            logger.error(f"解析冲突失败: {e}")
            return []
    
    def resolve_conflict(self, file_path: str, strategy: str = 'smart') -> bool:
        """
        解决文件冲突
        
        Args:
            file_path: 文件路径
            strategy: 解决策略 ('ours', 'theirs', 'both', 'smart')
            
        Returns:
            是否解决成功
        """
        try:
            if not self.detect_conflicts(file_path):
                logger.info(f"文件 {file_path} 没有冲突")
                return True
            
            conflicts = self.parse_conflicts(file_path)
            if not conflicts:
                logger.warning(f"无法解析文件 {file_path} 的冲突")
                return False
            
            # 选择解决策略
            resolver = self.resolution_strategies.get(strategy, self._resolve_smart)
            
            # 读取原文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 应用解决策略
            resolved_content = resolver(content, conflicts)
            
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(resolved_content)
            
            logger.info(f"冲突解决成功: {file_path} (策略: {strategy})")
            return True
            
        except Exception as e:
            logger.error(f"解决冲突失败: {e}")
            return False
    
    def _resolve_with_ours(self, content: str, conflicts: List[Dict[str, Any]]) -> str:
        """使用我们的版本解决冲突"""
        lines = content.split('\n')
        result_lines = []
        
        conflict_ranges = [(c['start_line'], c['end_line']) for c in conflicts]
        
        i = 0
        while i < len(lines):
            # 检查是否在冲突范围内
            in_conflict = False
            current_conflict = None
            
            for start, end in conflict_ranges:
                if start <= i <= end:
                    in_conflict = True
                    current_conflict = next(c for c in conflicts 
                                          if c['start_line'] == start)
                    break
            
            if in_conflict:
                # 添加我们的内容
                result_lines.extend(current_conflict['ours_content'])
                # 跳到冲突结束
                i = current_conflict['end_line'] + 1
            else:
                result_lines.append(lines[i])
                i += 1
        
        return '\n'.join(result_lines)
    
    def _resolve_with_theirs(self, content: str, conflicts: List[Dict[str, Any]]) -> str:
        """使用他们的版本解决冲突"""
        lines = content.split('\n')
        result_lines = []
        
        conflict_ranges = [(c['start_line'], c['end_line']) for c in conflicts]
        
        i = 0
        while i < len(lines):
            # 检查是否在冲突范围内
            in_conflict = False
            current_conflict = None
            
            for start, end in conflict_ranges:
                if start <= i <= end:
                    in_conflict = True
                    current_conflict = next(c for c in conflicts 
                                          if c['start_line'] == start)
                    break
            
            if in_conflict:
                # 添加他们的内容
                result_lines.extend(current_conflict['theirs_content'])
                # 跳到冲突结束
                i = current_conflict['end_line'] + 1
            else:
                result_lines.append(lines[i])
                i += 1
        
        return '\n'.join(result_lines)
    
    def _resolve_with_both(self, content: str, conflicts: List[Dict[str, Any]]) -> str:
        """保留双方的内容"""
        lines = content.split('\n')
        result_lines = []
        
        conflict_ranges = [(c['start_line'], c['end_line']) for c in conflicts]
        
        i = 0
        while i < len(lines):
            # 检查是否在冲突范围内
            in_conflict = False
            current_conflict = None
            
            for start, end in conflict_ranges:
                if start <= i <= end:
                    in_conflict = True
                    current_conflict = next(c for c in conflicts 
                                          if c['start_line'] == start)
                    break
            
            if in_conflict:
                # 添加我们的内容
                result_lines.extend(current_conflict['ours_content'])
                # 添加他们的内容
                result_lines.extend(current_conflict['theirs_content'])
                # 跳到冲突结束
                i = current_conflict['end_line'] + 1
            else:
                result_lines.append(lines[i])
                i += 1
        
        return '\n'.join(result_lines)
    
    def _resolve_smart(self, content: str, conflicts: List[Dict[str, Any]]) -> str:
        """智能解决冲突"""
        lines = content.split('\n')
        result_lines = []
        
        conflict_ranges = [(c['start_line'], c['end_line']) for c in conflicts]
        
        i = 0
        while i < len(lines):
            # 检查是否在冲突范围内
            in_conflict = False
            current_conflict = None
            
            for start, end in conflict_ranges:
                if start <= i <= end:
                    in_conflict = True
                    current_conflict = next(c for c in conflicts 
                                          if c['start_line'] == start)
                    break
            
            if in_conflict:
                # 智能选择策略
                resolution = self._smart_resolve_conflict(current_conflict)
                result_lines.extend(resolution)
                # 跳到冲突结束
                i = current_conflict['end_line'] + 1
            else:
                result_lines.append(lines[i])
                i += 1
        
        return '\n'.join(result_lines)
    
    def _smart_resolve_conflict(self, conflict: Dict[str, Any]) -> List[str]:
        """智能解决单个冲突"""
        ours = conflict['ours_content']
        theirs = conflict['theirs_content']
        
        # 如果一方为空，选择非空的一方
        if not ours and theirs:
            return theirs
        if not theirs and ours:
            return ours
        
        # 如果内容相同，选择任意一方
        if ours == theirs:
            return ours
        
        # 如果一方是另一方的子集，选择更完整的一方
        ours_text = '\n'.join(ours)
        theirs_text = '\n'.join(theirs)
        
        if ours_text in theirs_text:
            return theirs
        if theirs_text in ours_text:
            return ours
        
        # 检查是否是简单的添加操作
        if self._is_simple_addition(ours, theirs):
            return self._merge_additions(ours, theirs)
        
        # 默认保留双方内容
        result = []
        result.extend(ours)
        if ours and theirs:  # 如果都有内容，添加分隔注释
            result.append('# --- 合并内容 ---')
        result.extend(theirs)
        
        return result
    
    def _is_simple_addition(self, ours: List[str], theirs: List[str]) -> bool:
        """检查是否是简单的添加操作"""
        # 简单启发式：如果一方包含另一方的所有行，认为是添加操作
        ours_set = set(line.strip() for line in ours if line.strip())
        theirs_set = set(line.strip() for line in theirs if line.strip())
        
        return ours_set.issubset(theirs_set) or theirs_set.issubset(ours_set)
    
    def _merge_additions(self, ours: List[str], theirs: List[str]) -> List[str]:
        """合并添加操作"""
        # 保留所有唯一的行，保持相对顺序
        seen = set()
        result = []
        
        for line in ours + theirs:
            stripped = line.strip()
            if stripped and stripped not in seen:
                seen.add(stripped)
                result.append(line)
            elif not stripped:  # 保留空行
                result.append(line)
        
        return result
    
    def get_conflict_summary(self, file_path: str) -> Dict[str, Any]:
        """
        获取冲突摘要信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            冲突摘要字典
        """
        try:
            conflicts = self.parse_conflicts(file_path)
            
            summary = {
                'file_path': file_path,
                'has_conflicts': len(conflicts) > 0,
                'conflict_count': len(conflicts),
                'conflicts': []
            }
            
            for i, conflict in enumerate(conflicts):
                conflict_info = {
                    'index': i,
                    'ours_branch': conflict['ours_branch'],
                    'theirs_branch': conflict['theirs_branch'],
                    'ours_lines': len(conflict['ours_content']),
                    'theirs_lines': len(conflict['theirs_content']),
                    'line_range': (conflict['start_line'], conflict['end_line'])
                }
                summary['conflicts'].append(conflict_info)
            
            return summary
            
        except Exception as e:
            logger.error(f"获取冲突摘要失败: {e}")
            return {
                'file_path': file_path,
                'has_conflicts': False,
                'conflict_count': 0,
                'conflicts': [],
                'error': str(e)
            }
