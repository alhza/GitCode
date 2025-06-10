"""
Git操作处理器

负责Git仓库的基本操作，包括状态检查、文件添加、提交、推送等。
"""

import os
import git
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from ..utils.logger import get_logger
from .conflict_resolver import ConflictResolver

logger = get_logger(__name__)


class GitHandler:
    """Git操作处理器类"""

    def __init__(self, repo_path: str):
        """
        初始化Git处理器

        Args:
            repo_path: 仓库本地路径
        """
        self.repo_path = Path(repo_path)
        self.repo = None
        self.conflict_resolver = ConflictResolver()
        self._last_status_check = 0
        self._status_cache = None

        try:
            # 尝试打开现有仓库
            self.repo = git.Repo(self.repo_path)
            # 减少日志频率，只在首次初始化时记录
            if not hasattr(GitHandler, '_initialized_repos'):
                GitHandler._initialized_repos = set()

            if str(self.repo_path) not in GitHandler._initialized_repos:
                logger.info(f"Git仓库初始化成功: {self.repo_path}")
                GitHandler._initialized_repos.add(str(self.repo_path))

        except git.exc.InvalidGitRepositoryError:
            logger.warning(f"路径 {self.repo_path} 不是有效的Git仓库")
        except Exception as e:
            logger.error(f"Git仓库初始化失败: {e}")

    def __del__(self):
        """析构函数，确保资源释放"""
        try:
            if self.repo:
                self.repo.close()
        except Exception:
            pass
    
    def is_valid_repo(self) -> bool:
        """
        检查是否为有效的Git仓库
        
        Returns:
            是否为有效仓库
        """
        return self.repo is not None and not self.repo.bare
    
    def init_repo(self) -> bool:
        """
        初始化Git仓库
        
        Returns:
            是否初始化成功
        """
        try:
            if self.is_valid_repo():
                logger.info("仓库已存在，无需初始化")
                return True
            
            self.repo = git.Repo.init(self.repo_path)
            logger.info(f"Git仓库初始化成功: {self.repo_path}")
            return True
            
        except Exception as e:
            logger.error(f"初始化Git仓库失败: {e}")
            return False
    
    def check_status(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        检查仓库状态（带缓存机制）

        Args:
            use_cache: 是否使用缓存

        Returns:
            状态信息字典
        """
        if not self.is_valid_repo():
            return {"error": "无效的Git仓库"}

        # 检查缓存是否有效（5秒内）
        import time
        current_time = time.time()
        if use_cache and self._status_cache and (current_time - self._last_status_check) < 5:
            return self._status_cache.copy()

        try:
            status = {
                "branch": self.get_current_branch(),
                "is_dirty": self.repo.is_dirty(),
                "untracked_files": self.repo.untracked_files,
                "modified_files": [item.a_path for item in self.repo.index.diff(None)],
                "staged_files": [],
                "ahead": 0,
                "behind": 0,
                "last_commit": None
            }

            # 获取暂存文件列表
            try:
                if self.repo.head.is_valid():
                    status["staged_files"] = [item.a_path for item in self.repo.index.diff("HEAD")]
                else:
                    # 初始仓库，检查暂存区
                    status["staged_files"] = [item.a_path for item in self.repo.index.diff(None, cached=True)]
            except Exception:
                status["staged_files"] = []
            
            # 获取最后一次提交信息
            try:
                if self.repo.head.is_valid():
                    last_commit = self.repo.head.commit
                    status["last_commit"] = {
                        "hash": last_commit.hexsha[:8],
                        "message": last_commit.message.strip(),
                        "author": str(last_commit.author),
                        "date": datetime.fromtimestamp(last_commit.committed_date)
                    }
                else:
                    status["last_commit"] = None
            except Exception:
                status["last_commit"] = None
            
            # 获取与远程的差异
            try:
                if self.repo.head.is_valid():
                    remote_branch = f"origin/{status['branch']}"
                    if remote_branch in [ref.name for ref in self.repo.refs]:
                        ahead_behind = self.repo.git.rev_list(
                            '--left-right', '--count',
                            f"HEAD...{remote_branch}"
                        ).split('\t')
                        status["ahead"] = int(ahead_behind[0])
                        status["behind"] = int(ahead_behind[1])
            except Exception:
                pass

            # 更新缓存
            self._status_cache = status.copy()
            self._last_status_check = current_time

            return status

        except Exception as e:
            logger.error(f"检查仓库状态失败: {e}")
            error_result = {"error": str(e)}
            # 即使出错也缓存结果，避免频繁重试
            self._status_cache = error_result.copy()
            self._last_status_check = current_time
            return error_result
    
    def get_current_branch(self) -> str:
        """
        获取当前分支名
        
        Returns:
            分支名
        """
        if not self.is_valid_repo():
            return "unknown"
        
        try:
            return self.repo.active_branch.name
        except Exception:
            return "detached"
    
    def add_files(self, files: Optional[List[str]] = None) -> bool:
        """
        添加文件到暂存区
        
        Args:
            files: 文件列表，None表示添加所有变更
            
        Returns:
            是否添加成功
        """
        if not self.is_valid_repo():
            logger.error("无效的Git仓库")
            return False
        
        try:
            if files is None:
                # 添加所有变更文件
                self.repo.git.add(A=True)
                logger.info("已添加所有变更文件到暂存区")
            else:
                # 添加指定文件
                for file_path in files:
                    if Path(self.repo_path / file_path).exists():
                        self.repo.index.add([file_path])
                    else:
                        logger.warning(f"文件不存在: {file_path}")
                
                logger.info(f"已添加 {len(files)} 个文件到暂存区")
            
            return True
            
        except Exception as e:
            logger.error(f"添加文件到暂存区失败: {e}")
            return False
    
    def create_commit(self, message: str, author_name: str = None, 
                     author_email: str = None) -> bool:
        """
        创建提交
        
        Args:
            message: 提交消息
            author_name: 作者姓名
            author_email: 作者邮箱
            
        Returns:
            是否提交成功
        """
        if not self.is_valid_repo():
            logger.error("无效的Git仓库")
            return False
        
        try:
            # 检查是否有暂存的文件
            try:
                staged_files = self.repo.index.diff("HEAD")
            except:
                # 如果没有HEAD（初始提交），检查暂存区是否有文件
                staged_files = self.repo.index.diff(None, cached=True)

            if not staged_files:
                logger.warning("没有暂存的文件，无法创建提交")
                return False
            
            # 设置作者信息
            if author_name and author_email:
                actor = git.Actor(author_name, author_email)
                commit = self.repo.index.commit(message, author=actor, committer=actor)
            else:
                commit = self.repo.index.commit(message)
            
            logger.info(f"提交创建成功: {commit.hexsha[:8]} - {message}")
            return True
            
        except Exception as e:
            logger.error(f"创建提交失败: {e}")
            return False
    
    def push_changes(self, remote: str = "origin", 
                    branch: str = None) -> bool:
        """
        推送变更到远程仓库
        
        Args:
            remote: 远程仓库名
            branch: 分支名，None表示当前分支
            
        Returns:
            是否推送成功
        """
        if not self.is_valid_repo():
            logger.error("无效的Git仓库")
            return False
        
        try:
            if branch is None:
                branch = self.get_current_branch()
            
            # 检查远程仓库是否存在
            if remote not in [r.name for r in self.repo.remotes]:
                logger.error(f"远程仓库 {remote} 不存在")
                return False
            
            # 推送到远程
            origin = self.repo.remote(remote)
            push_info = origin.push(branch)
            
            # 检查推送结果
            for info in push_info:
                if info.flags & info.ERROR:
                    logger.error(f"推送失败: {info.summary}")
                    return False
                elif info.flags & info.REJECTED:
                    logger.error(f"推送被拒绝: {info.summary}")
                    return False
            
            logger.info(f"推送成功: {remote}/{branch}")
            return True
            
        except Exception as e:
            logger.error(f"推送变更失败: {e}")
            return False
    
    def pull_latest(self, remote: str = "origin", 
                   branch: str = None) -> bool:
        """
        拉取最新代码
        
        Args:
            remote: 远程仓库名
            branch: 分支名，None表示当前分支
            
        Returns:
            是否拉取成功
        """
        if not self.is_valid_repo():
            logger.error("无效的Git仓库")
            return False
        
        try:
            if branch is None:
                branch = self.get_current_branch()
            
            # 检查远程仓库是否存在
            if remote not in [r.name for r in self.repo.remotes]:
                logger.error(f"远程仓库 {remote} 不存在")
                return False
            
            # 拉取最新代码
            origin = self.repo.remote(remote)
            pull_info = origin.pull(branch)
            
            logger.info(f"拉取成功: {remote}/{branch}")
            return True
            
        except git.exc.GitCommandError as e:
            if "merge conflict" in str(e).lower():
                logger.warning("拉取时发生冲突，需要手动解决")
                return False
            else:
                logger.error(f"拉取失败: {e}")
                return False
        except Exception as e:
            logger.error(f"拉取最新代码失败: {e}")
            return False
    
    def get_diff(self, file_path: str = None) -> str:
        """
        获取文件差异
        
        Args:
            file_path: 文件路径，None表示所有文件
            
        Returns:
            差异内容
        """
        if not self.is_valid_repo():
            return "无效的Git仓库"
        
        try:
            if file_path:
                # 获取指定文件的差异
                return self.repo.git.diff(file_path)
            else:
                # 获取所有文件的差异
                return self.repo.git.diff()
                
        except Exception as e:
            logger.error(f"获取文件差异失败: {e}")
            return f"获取差异失败: {e}"
    
    def get_commit_history(self, max_count: int = 10) -> List[Dict[str, Any]]:
        """
        获取提交历史
        
        Args:
            max_count: 最大提交数量
            
        Returns:
            提交历史列表
        """
        if not self.is_valid_repo():
            return []
        
        try:
            commits = []
            for commit in self.repo.iter_commits(max_count=max_count):
                commits.append({
                    "hash": commit.hexsha[:8],
                    "full_hash": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": datetime.fromtimestamp(commit.committed_date),
                    "files_changed": len(commit.stats.files)
                })
            
            return commits
            
        except Exception as e:
            logger.error(f"获取提交历史失败: {e}")
            return []
    
    def rollback(self, commit_hash: str = None) -> bool:
        """
        回滚到指定提交
        
        Args:
            commit_hash: 提交哈希，None表示回滚到上一次提交
            
        Returns:
            是否回滚成功
        """
        if not self.is_valid_repo():
            logger.error("无效的Git仓库")
            return False
        
        try:
            if commit_hash is None:
                # 回滚到上一次提交
                self.repo.git.reset('--hard', 'HEAD~1')
                logger.info("已回滚到上一次提交")
            else:
                # 回滚到指定提交
                self.repo.git.reset('--hard', commit_hash)
                logger.info(f"已回滚到提交: {commit_hash}")
            
            return True
            
        except Exception as e:
            logger.error(f"回滚失败: {e}")
            return False
    
    def set_remote_url(self, remote: str, url: str) -> bool:
        """
        设置远程仓库URL
        
        Args:
            remote: 远程仓库名
            url: 远程仓库URL
            
        Returns:
            是否设置成功
        """
        if not self.is_valid_repo():
            logger.error("无效的Git仓库")
            return False
        
        try:
            if remote in [r.name for r in self.repo.remotes]:
                # 更新现有远程仓库
                self.repo.remote(remote).set_url(url)
                logger.info(f"远程仓库 {remote} URL已更新: {url}")
            else:
                # 添加新的远程仓库
                self.repo.create_remote(remote, url)
                logger.info(f"远程仓库 {remote} 已添加: {url}")
            
            return True
            
        except Exception as e:
            logger.error(f"设置远程仓库URL失败: {e}")
            return False
    
    def has_conflicts(self) -> bool:
        """
        检查是否有冲突
        
        Returns:
            是否有冲突
        """
        if not self.is_valid_repo():
            return False
        
        try:
            # 检查是否有未解决的冲突
            status = self.repo.git.status('--porcelain')
            return 'UU' in status or 'AA' in status or 'DD' in status
            
        except Exception as e:
            logger.error(f"检查冲突状态失败: {e}")
            return False
    
    def get_conflicted_files(self) -> List[str]:
        """
        获取有冲突的文件列表
        
        Returns:
            冲突文件列表
        """
        if not self.is_valid_repo():
            return []
        
        try:
            conflicted_files = []
            status_lines = self.repo.git.status('--porcelain').split('\n')
            
            for line in status_lines:
                if line.startswith('UU') or line.startswith('AA') or line.startswith('DD'):
                    file_path = line[3:].strip()
                    conflicted_files.append(file_path)
            
            return conflicted_files
            
        except Exception as e:
            logger.error(f"获取冲突文件列表失败: {e}")
            return []
