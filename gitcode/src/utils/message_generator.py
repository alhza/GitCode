"""
提交消息生成器

智能生成Git提交消息，支持多种消息格式和模板。
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .logger import get_logger

logger = get_logger(__name__)


class MessageGenerator:
    """提交消息生成器类"""
    
    def __init__(self, template: str = "{type}: {description}"):
        """
        初始化消息生成器
        
        Args:
            template: 消息模板
        """
        self.template = template
        
        # 文件类型映射
        self.file_type_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.h': 'Header',
            '.css': 'CSS',
            '.html': 'HTML',
            '.xml': 'XML',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.sql': 'SQL',
            '.sh': 'Shell',
            '.bat': 'Batch',
            '.ps1': 'PowerShell',
            '.dockerfile': 'Docker',
            '.gitignore': 'Git',
            '.env': 'Environment'
        }
        
        # 提交类型映射
        self.commit_types = {
            'feat': '新功能',
            'fix': '修复',
            'docs': '文档',
            'style': '格式',
            'refactor': '重构',
            'test': '测试',
            'chore': '构建',
            'perf': '性能',
            'ci': '集成',
            'build': '构建',
            'revert': '回滚'
        }
        
        # 常见操作关键词
        self.action_keywords = {
            'add': ['新增', '添加', '创建'],
            'update': ['更新', '修改', '调整'],
            'delete': ['删除', '移除', '清理'],
            'fix': ['修复', '解决', '修正'],
            'improve': ['优化', '改进', '提升'],
            'refactor': ['重构', '重写', '整理']
        }
    
    def generate_message(self, changed_files: List[str], 
                        untracked_files: List[str] = None,
                        custom_message: str = None) -> str:
        """
        生成提交消息
        
        Args:
            changed_files: 已修改文件列表
            untracked_files: 未跟踪文件列表
            custom_message: 自定义消息
            
        Returns:
            生成的提交消息
        """
        try:
            if custom_message:
                return custom_message
            
            if untracked_files is None:
                untracked_files = []
            
            all_files = changed_files + untracked_files
            
            if not all_files:
                return "空提交"
            
            # 分析文件变更
            analysis = self._analyze_changes(changed_files, untracked_files)
            
            # 确定提交类型
            commit_type = self._determine_commit_type(analysis)
            
            # 生成描述
            description = self._generate_description(analysis)
            
            # 应用模板
            message = self.template.format(
                type=commit_type,
                description=description,
                files_count=len(all_files),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            
            return message
            
        except Exception as e:
            logger.error(f"生成提交消息失败: {e}")
            return f"自动提交 - {len(changed_files + (untracked_files or []))} 个文件变更"
    
    def _analyze_changes(self, changed_files: List[str], 
                        untracked_files: List[str]) -> Dict[str, Any]:
        """分析文件变更"""
        analysis = {
            'total_files': len(changed_files) + len(untracked_files),
            'modified_files': len(changed_files),
            'new_files': len(untracked_files),
            'file_types': {},
            'directories': set(),
            'has_config': False,
            'has_docs': False,
            'has_tests': False,
            'has_source': False
        }
        
        all_files = changed_files + untracked_files
        
        for file_path in all_files:
            path = Path(file_path)
            
            # 分析文件类型
            ext = path.suffix.lower()
            file_type = self.file_type_map.get(ext, 'Other')
            analysis['file_types'][file_type] = analysis['file_types'].get(file_type, 0) + 1
            
            # 分析目录
            if path.parent != Path('.'):
                analysis['directories'].add(str(path.parent))
            
            # 分析文件性质
            file_name = path.name.lower()
            file_path_lower = file_path.lower()
            
            if any(keyword in file_path_lower for keyword in ['config', 'setting', '.env', '.ini']):
                analysis['has_config'] = True
            
            if any(keyword in file_path_lower for keyword in ['readme', 'doc', '.md', 'manual']):
                analysis['has_docs'] = True
            
            if any(keyword in file_path_lower for keyword in ['test', 'spec', '__test__']):
                analysis['has_tests'] = True
            
            if ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c']:
                analysis['has_source'] = True
        
        return analysis
    
    def _determine_commit_type(self, analysis: Dict[str, Any]) -> str:
        """确定提交类型"""
        # 根据文件分析确定提交类型
        if analysis['new_files'] > analysis['modified_files']:
            return 'feat'  # 主要是新文件
        
        if analysis['has_docs'] and not analysis['has_source']:
            return 'docs'  # 只有文档变更
        
        if analysis['has_tests'] and not analysis['has_source']:
            return 'test'  # 只有测试变更
        
        if analysis['has_config']:
            return 'chore'  # 配置文件变更
        
        if analysis['has_source']:
            if analysis['new_files'] > 0:
                return 'feat'  # 有新的源代码文件
            else:
                return 'fix'   # 修改现有源代码
        
        return 'chore'  # 默认类型
    
    def _generate_description(self, analysis: Dict[str, Any]) -> str:
        """生成描述"""
        descriptions = []
        
        # 基于文件数量的描述
        if analysis['new_files'] > 0:
            descriptions.append(f"新增{analysis['new_files']}个文件")
        
        if analysis['modified_files'] > 0:
            descriptions.append(f"修改{analysis['modified_files']}个文件")
        
        # 基于文件类型的描述
        main_types = sorted(analysis['file_types'].items(), 
                           key=lambda x: x[1], reverse=True)[:2]
        
        if main_types:
            type_desc = "、".join([f"{count}个{file_type}文件" 
                                 for file_type, count in main_types])
            descriptions.append(f"涉及{type_desc}")
        
        # 基于目录的描述
        if len(analysis['directories']) == 1:
            dir_name = list(analysis['directories'])[0]
            descriptions.append(f"更新{dir_name}模块")
        elif len(analysis['directories']) > 1:
            descriptions.append(f"更新{len(analysis['directories'])}个模块")
        
        # 特殊情况描述
        special_desc = []
        if analysis['has_docs']:
            special_desc.append("文档")
        if analysis['has_tests']:
            special_desc.append("测试")
        if analysis['has_config']:
            special_desc.append("配置")
        
        if special_desc:
            descriptions.append(f"包含{' '.join(special_desc)}更新")
        
        # 组合描述
        if descriptions:
            return "，".join(descriptions[:3])  # 最多3个描述
        else:
            return f"{analysis['total_files']}个文件的更新"
    
    def generate_conventional_message(self, changed_files: List[str],
                                    untracked_files: List[str] = None,
                                    scope: str = None) -> str:
        """
        生成符合Conventional Commits规范的消息
        
        Args:
            changed_files: 已修改文件列表
            untracked_files: 未跟踪文件列表
            scope: 影响范围
            
        Returns:
            符合规范的提交消息
        """
        try:
            if untracked_files is None:
                untracked_files = []
            
            analysis = self._analyze_changes(changed_files, untracked_files)
            commit_type = self._determine_commit_type(analysis)
            
            # 生成简短描述
            if analysis['new_files'] > 0 and analysis['modified_files'] == 0:
                description = f"add {analysis['new_files']} new files"
            elif analysis['modified_files'] > 0 and analysis['new_files'] == 0:
                description = f"update {analysis['modified_files']} files"
            else:
                description = f"modify {analysis['total_files']} files"
            
            # 添加范围
            if scope:
                message = f"{commit_type}({scope}): {description}"
            else:
                # 自动推断范围
                if len(analysis['directories']) == 1:
                    auto_scope = list(analysis['directories'])[0].replace('/', '-')
                    message = f"{commit_type}({auto_scope}): {description}"
                else:
                    message = f"{commit_type}: {description}"
            
            return message
            
        except Exception as e:
            logger.error(f"生成Conventional Commits消息失败: {e}")
            return f"chore: update {len(changed_files + (untracked_files or []))} files"
    
    def set_template(self, template: str) -> None:
        """
        设置消息模板
        
        Args:
            template: 新的消息模板
        """
        self.template = template
        logger.info(f"消息模板已更新: {template}")
    
    def get_available_types(self) -> Dict[str, str]:
        """
        获取可用的提交类型
        
        Returns:
            提交类型字典
        """
        return self.commit_types.copy()
    
    def validate_message(self, message: str) -> bool:
        """
        验证提交消息格式
        
        Args:
            message: 提交消息
            
        Returns:
            是否符合格式要求
        """
        try:
            # 基本长度检查
            if len(message.strip()) < 5:
                return False
            
            # 检查是否包含中文或英文字符
            if not re.search(r'[\u4e00-\u9fff]|[a-zA-Z]', message):
                return False
            
            # 检查是否过长
            if len(message) > 200:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证提交消息失败: {e}")
            return False
