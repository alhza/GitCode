"""
主窗口

Gitee自动提交工具的主图形界面窗口。
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem, QListWidget,
        QListWidgetItem, QTextEdit, QLabel, QPushButton, QProgressBar,
        QMenuBar, QMenu, QAction, QStatusBar, QMessageBox, QFileDialog,
        QInputDialog, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
        QCheckBox, QComboBox, QSpinBox, QGroupBox, QFrame, QScrollArea,
        QSystemTrayIcon, QApplication
    )
    from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
    from PyQt5.QtGui import QIcon, QFont, QPixmap, QPalette, QColor
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    # 创建占位符类
    class QMainWindow: pass
    class QWidget: pass
    class QTimer: pass
    class QThread: pass
    class pyqtSignal: pass

# 添加src目录到路径
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

from src.auto_committer import AutoCommitter
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


class WorkerThread(QThread):
    """工作线程，用于执行后台任务"""

    # 信号定义
    status_updated = pyqtSignal(str, dict)  # 状态更新信号
    commit_completed = pyqtSignal(str, bool, str)  # 提交完成信号
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, auto_committer: AutoCommitter):
        super().__init__()
        self.auto_committer = auto_committer
        self.running = False

    def run(self):
        """线程主循环"""
        self.running = True
        while self.running:
            try:
                # 获取所有仓库状态
                repos = self.auto_committer.get_all_repo_status()
                for repo in repos:
                    if not self.running:
                        break

                    repo_name = repo['name']
                    status = self.auto_committer.check_repo_changes(repo_name)
                    self.status_updated.emit(repo_name, status)

                # 休眠5秒
                self.msleep(5000)

            except Exception as e:
                self.error_occurred.emit(str(e))
                self.msleep(1000)

    def stop(self):
        """停止线程"""
        self.running = False


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()

        if not GUI_AVAILABLE:
            raise ImportError("PyQt5 not available. Please install: pip install PyQt5")

        # 初始化自动提交器
        self.auto_committer = AutoCommitter()

        # 工作线程
        self.worker_thread = None

        # 状态缓存
        self.repo_status_cache: Dict[str, Dict[str, Any]] = {}

        # 初始化界面
        self.init_ui()
        self.init_connections()
        self.load_repositories()

        # 启动状态更新
        self.start_status_updates()

        logger.info("主窗口初始化完成")

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("Gitee自动提交工具 v1.0")
        self.setGeometry(100, 100, 1200, 800)

        # 设置窗口图标（如果有的话）
        # self.setWindowIcon(QIcon("icon.png"))

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QHBoxLayout(central_widget)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧面板 - 仓库列表
        self.create_left_panel(splitter)

        # 右侧面板 - 详细信息
        self.create_right_panel(splitter)

        # 设置分割器比例
        splitter.setSizes([300, 900])

        # 创建菜单栏
        self.create_menu_bar()

        # 创建状态栏
        self.create_status_bar()

        # 应用样式
        self.apply_styles()

    def create_left_panel(self, parent):
        """创建左侧面板"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 仓库列表标题
        title_label = QLabel("📁 Git仓库")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(title_label)

        # 仓库树形控件
        self.repo_tree = QTreeWidget()
        self.repo_tree.setHeaderLabels(["仓库", "状态"])
        self.repo_tree.setRootIsDecorated(True)
        self.repo_tree.setAlternatingRowColors(True)
        left_layout.addWidget(self.repo_tree)

        # 操作按钮
        button_layout = QVBoxLayout()

        self.add_repo_btn = QPushButton("➕ 添加仓库")
        self.remove_repo_btn = QPushButton("➖ 移除仓库")
        self.refresh_btn = QPushButton("🔄 刷新状态")

        button_layout.addWidget(self.add_repo_btn)
        button_layout.addWidget(self.remove_repo_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()

        left_layout.addLayout(button_layout)

        parent.addWidget(left_widget)

    def create_right_panel(self, parent):
        """创建右侧面板"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 创建选项卡
        self.tab_widget = QTabWidget()
        right_layout.addWidget(self.tab_widget)

        # 仓库状态选项卡
        self.create_status_tab()

        # 文件变更选项卡
        self.create_changes_tab()

        # 提交历史选项卡
        self.create_history_tab()

        # 实时日志选项卡
        self.create_log_tab()

        # 快速操作面板
        self.create_quick_actions(right_layout)

        parent.addWidget(right_widget)

    def create_status_tab(self):
        """创建状态选项卡"""
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)

        # 仓库信息
        info_group = QGroupBox("📊 仓库信息")
        info_layout = QGridLayout(info_group)

        self.repo_name_label = QLabel("未选择仓库")
        self.repo_path_label = QLabel("-")
        self.repo_branch_label = QLabel("-")
        self.repo_url_label = QLabel("-")

        info_layout.addWidget(QLabel("仓库名称:"), 0, 0)
        info_layout.addWidget(self.repo_name_label, 0, 1)
        info_layout.addWidget(QLabel("本地路径:"), 1, 0)
        info_layout.addWidget(self.repo_path_label, 1, 1)
        info_layout.addWidget(QLabel("当前分支:"), 2, 0)
        info_layout.addWidget(self.repo_branch_label, 2, 1)
        info_layout.addWidget(QLabel("远程URL:"), 3, 0)
        info_layout.addWidget(self.repo_url_label, 3, 1)

        status_layout.addWidget(info_group)

        # 变更统计
        stats_group = QGroupBox("📈 变更统计")
        stats_layout = QGridLayout(stats_group)

        self.modified_count_label = QLabel("0")
        self.untracked_count_label = QLabel("0")
        self.staged_count_label = QLabel("0")
        self.total_changes_label = QLabel("0")

        stats_layout.addWidget(QLabel("已修改:"), 0, 0)
        stats_layout.addWidget(self.modified_count_label, 0, 1)
        stats_layout.addWidget(QLabel("未跟踪:"), 0, 2)
        stats_layout.addWidget(self.untracked_count_label, 0, 3)
        stats_layout.addWidget(QLabel("已暂存:"), 1, 0)
        stats_layout.addWidget(self.staged_count_label, 1, 1)
        stats_layout.addWidget(QLabel("总变更:"), 1, 2)
        stats_layout.addWidget(self.total_changes_label, 1, 3)

        status_layout.addWidget(stats_group)

        # 最后提交信息
        commit_group = QGroupBox("📝 最后提交")
        commit_layout = QGridLayout(commit_group)

        self.last_commit_hash_label = QLabel("-")
        self.last_commit_message_label = QLabel("-")
        self.last_commit_author_label = QLabel("-")
        self.last_commit_date_label = QLabel("-")

        commit_layout.addWidget(QLabel("提交哈希:"), 0, 0)
        commit_layout.addWidget(self.last_commit_hash_label, 0, 1)
        commit_layout.addWidget(QLabel("提交消息:"), 1, 0)
        commit_layout.addWidget(self.last_commit_message_label, 1, 1)
        commit_layout.addWidget(QLabel("作者:"), 2, 0)
        commit_layout.addWidget(self.last_commit_author_label, 2, 1)
        commit_layout.addWidget(QLabel("日期:"), 3, 0)
        commit_layout.addWidget(self.last_commit_date_label, 3, 1)

        status_layout.addWidget(commit_group)
        status_layout.addStretch()

        self.tab_widget.addTab(status_widget, "📊 仓库状态")

    def create_changes_tab(self):
        """创建文件变更选项卡"""
        changes_widget = QWidget()
        changes_layout = QVBoxLayout(changes_widget)

        # 变更文件列表
        self.changes_list = QListWidget()
        self.changes_list.setAlternatingRowColors(True)
        changes_layout.addWidget(QLabel("📝 文件变更列表:"))
        changes_layout.addWidget(self.changes_list)

        self.tab_widget.addTab(changes_widget, "📝 文件变更")

    def create_history_tab(self):
        """创建提交历史选项卡"""
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)

        # 提交历史列表
        self.history_list = QListWidget()
        self.history_list.setAlternatingRowColors(True)
        history_layout.addWidget(QLabel("📚 提交历史:"))
        history_layout.addWidget(self.history_list)

        self.tab_widget.addTab(history_widget, "📚 提交历史")

    def create_log_tab(self):
        """创建日志选项卡"""
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(QLabel("📋 实时日志:"))
        log_layout.addWidget(self.log_text)

        # 日志控制按钮
        log_button_layout = QHBoxLayout()
        self.clear_log_btn = QPushButton("🗑️ 清空日志")
        self.export_log_btn = QPushButton("💾 导出日志")
        log_button_layout.addWidget(self.clear_log_btn)
        log_button_layout.addWidget(self.export_log_btn)
        log_button_layout.addStretch()

        log_layout.addLayout(log_button_layout)

        self.tab_widget.addTab(log_widget, "📋 实时日志")

    def create_quick_actions(self, parent_layout):
        """创建快速操作面板"""
        actions_group = QGroupBox("⚡ 快速操作")
        actions_layout = QHBoxLayout(actions_group)

        self.commit_btn = QPushButton("💾 立即提交")
        self.commit_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")

        self.start_monitor_btn = QPushButton("🔍 开始监控")
        self.start_monitor_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")

        self.stop_monitor_btn = QPushButton("⏹️ 停止监控")
        self.stop_monitor_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
        self.stop_monitor_btn.setEnabled(False)

        self.settings_btn = QPushButton("⚙️ 设置")

        actions_layout.addWidget(self.commit_btn)
        actions_layout.addWidget(self.start_monitor_btn)
        actions_layout.addWidget(self.stop_monitor_btn)
        actions_layout.addWidget(self.settings_btn)
        actions_layout.addStretch()

        parent_layout.addWidget(actions_group)

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')

        add_repo_action = QAction('➕ 添加仓库', self)
        add_repo_action.setShortcut('Ctrl+N')
        add_repo_action.triggered.connect(self.add_repository)
        file_menu.addAction(add_repo_action)

        file_menu.addSeparator()

        exit_action = QAction('退出(&X)', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu('编辑(&E)')

        settings_action = QAction('⚙️ 设置', self)
        settings_action.setShortcut('Ctrl+,')
        settings_action.triggered.connect(self.open_settings)
        edit_menu.addAction(settings_action)

        # 视图菜单
        view_menu = menubar.addMenu('视图(&V)')

        refresh_action = QAction('🔄 刷新', self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self.refresh_all)
        view_menu.addAction(refresh_action)

        # 工具菜单
        tools_menu = menubar.addMenu('工具(&T)')

        commit_action = QAction('💾 立即提交', self)
        commit_action.setShortcut('Ctrl+Enter')
        commit_action.triggered.connect(self.commit_selected_repo)
        tools_menu.addAction(commit_action)

        monitor_action = QAction('🔍 开始监控', self)
        monitor_action.setShortcut('Ctrl+M')
        monitor_action.triggered.connect(self.start_monitoring)
        tools_menu.addAction(monitor_action)

        # 帮助菜单
        help_menu = menubar.addMenu('帮助(&H)')

        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = self.statusBar()

        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # 监控状态
        self.monitor_status_label = QLabel("监控: 未启动")
        self.status_bar.addPermanentWidget(self.monitor_status_label)

    def apply_styles(self):
        """应用样式"""
        # 设置整体样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
                border-color: #999999;
            }
            QPushButton:pressed {
                background-color: #d4d4d4;
            }
            QTreeWidget, QListWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #e6e6e6;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom-color: #ffffff;
            }
        """)

    def init_connections(self):
        """初始化信号连接"""
        # 仓库树选择事件
        self.repo_tree.itemSelectionChanged.connect(self.on_repo_selected)

        # 按钮事件
        self.add_repo_btn.clicked.connect(self.add_repository)
        self.remove_repo_btn.clicked.connect(self.remove_repository)
        self.refresh_btn.clicked.connect(self.refresh_all)
        self.commit_btn.clicked.connect(self.commit_selected_repo)
        self.start_monitor_btn.clicked.connect(self.start_monitoring)
        self.stop_monitor_btn.clicked.connect(self.stop_monitoring)
        self.settings_btn.clicked.connect(self.open_settings)
        self.clear_log_btn.clicked.connect(self.clear_log)
        self.export_log_btn.clicked.connect(self.export_log)

    def load_repositories(self):
        """加载仓库列表"""
        try:
            repos = self.auto_committer.get_all_repo_status()
            self.repo_tree.clear()

            for repo in repos:
                item = QTreeWidgetItem(self.repo_tree)
                item.setText(0, repo['name'])

                # 设置状态图标和文本
                if repo.get('error'):
                    item.setText(1, "❌ 错误")
                    item.setToolTip(1, repo['error'])
                elif repo['has_changes']:
                    item.setText(1, f"📝 {repo['total_changes']} 变更")
                else:
                    item.setText(1, "✅ 无变更")

                # 存储仓库数据
                item.setData(0, Qt.UserRole, repo)

            self.status_label.setText(f"已加载 {len(repos)} 个仓库")

        except Exception as e:
            logger.error(f"加载仓库列表失败: {e}")
            self.show_error("加载仓库失败", str(e))

    def on_repo_selected(self):
        """仓库选择事件处理"""
        current_item = self.repo_tree.currentItem()
        if not current_item:
            return

        repo_data = current_item.data(0, Qt.UserRole)
        if not repo_data:
            return

        repo_name = repo_data['name']
        self.update_repo_details(repo_name)

    def update_repo_details(self, repo_name: str):
        """更新仓库详细信息"""
        try:
            # 获取仓库配置
            repo_config = self.auto_committer.config_manager.get_repo_config(repo_name)
            if not repo_config:
                return

            # 更新基本信息
            self.repo_name_label.setText(repo_name)
            self.repo_path_label.setText(repo_config.get('local_path', '-'))
            self.repo_url_label.setText(repo_config.get('remote_url', '-'))

            # 获取Git状态
            git_handler = self.auto_committer.get_git_handler(repo_name)
            if git_handler:
                status = git_handler.check_status()

                # 更新分支信息
                self.repo_branch_label.setText(status.get('branch', '-'))

                # 更新变更统计
                self.modified_count_label.setText(str(len(status.get('modified_files', []))))
                self.untracked_count_label.setText(str(len(status.get('untracked_files', []))))
                self.staged_count_label.setText(str(len(status.get('staged_files', []))))

                total_changes = (len(status.get('modified_files', [])) +
                               len(status.get('untracked_files', [])))
                self.total_changes_label.setText(str(total_changes))

                # 更新最后提交信息
                last_commit = status.get('last_commit')
                if last_commit:
                    self.last_commit_hash_label.setText(last_commit.get('hash', '-'))
                    self.last_commit_message_label.setText(last_commit.get('message', '-'))
                    self.last_commit_author_label.setText(last_commit.get('author', '-'))

                    commit_date = last_commit.get('date')
                    if commit_date:
                        self.last_commit_date_label.setText(commit_date.strftime('%Y-%m-%d %H:%M:%S'))
                    else:
                        self.last_commit_date_label.setText('-')
                else:
                    self.last_commit_hash_label.setText('-')
                    self.last_commit_message_label.setText('-')
                    self.last_commit_author_label.setText('-')
                    self.last_commit_date_label.setText('-')

                # 更新文件变更列表
                self.update_changes_list(status)

                # 更新提交历史
                self.update_history_list(git_handler)

        except Exception as e:
            logger.error(f"更新仓库详情失败: {e}")
            self.show_error("更新详情失败", str(e))

    def update_changes_list(self, status: Dict[str, Any]):
        """更新文件变更列表"""
        self.changes_list.clear()

        # 添加修改的文件
        for file_path in status.get('modified_files', []):
            item = QListWidgetItem(f"📝 {file_path}")
            item.setToolTip(f"已修改: {file_path}")
            self.changes_list.addItem(item)

        # 添加未跟踪的文件
        for file_path in status.get('untracked_files', []):
            item = QListWidgetItem(f"➕ {file_path}")
            item.setToolTip(f"新文件: {file_path}")
            self.changes_list.addItem(item)

        # 添加已暂存的文件
        for file_path in status.get('staged_files', []):
            item = QListWidgetItem(f"✅ {file_path}")
            item.setToolTip(f"已暂存: {file_path}")
            self.changes_list.addItem(item)

    def update_history_list(self, git_handler):
        """更新提交历史列表"""
        self.history_list.clear()

        try:
            history = git_handler.get_commit_history(max_count=20)

            for commit in history:
                commit_text = f"{commit['hash']} - {commit['message'][:50]}..."
                item = QListWidgetItem(commit_text)

                # 设置详细信息
                tooltip = (f"哈希: {commit['full_hash']}\n"
                          f"消息: {commit['message']}\n"
                          f"作者: {commit['author']}\n"
                          f"日期: {commit['date']}\n"
                          f"文件变更: {commit['files_changed']} 个")
                item.setToolTip(tooltip)

                self.history_list.addItem(item)

        except Exception as e:
            logger.error(f"更新提交历史失败: {e}")

    def start_status_updates(self):
        """启动状态更新"""
        if not self.worker_thread:
            self.worker_thread = WorkerThread(self.auto_committer)
            self.worker_thread.status_updated.connect(self.on_status_updated)
            self.worker_thread.error_occurred.connect(self.on_error_occurred)
            self.worker_thread.start()

    def stop_status_updates(self):
        """停止状态更新"""
        if self.worker_thread:
            self.worker_thread.stop()
            self.worker_thread.wait()
            self.worker_thread = None

    def on_status_updated(self, repo_name: str, status: Dict[str, Any]):
        """状态更新回调"""
        self.repo_status_cache[repo_name] = status

        # 更新树形控件中的状态
        for i in range(self.repo_tree.topLevelItemCount()):
            item = self.repo_tree.topLevelItem(i)
            repo_data = item.data(0, Qt.UserRole)

            if repo_data and repo_data['name'] == repo_name:
                if status.get('has_changes'):
                    item.setText(1, f"📝 {status.get('total_changes', 0)} 变更")
                else:
                    item.setText(1, "✅ 无变更")
                break

        # 如果当前选中的是这个仓库，更新详细信息
        current_item = self.repo_tree.currentItem()
        if current_item:
            current_repo = current_item.data(0, Qt.UserRole)
            if current_repo and current_repo['name'] == repo_name:
                self.update_repo_details(repo_name)

    def on_error_occurred(self, error_message: str):
        """错误发生回调"""
        self.append_log(f"❌ 错误: {error_message}")

    def add_repository(self):
        """添加仓库对话框"""
        from .dialogs.repo_dialog import RepoDialog

        dialog = RepoDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            repo_config = dialog.get_repo_config()

            # 添加到配置
            if self.auto_committer.config_manager.add_repository(repo_config):
                self.append_log(f"✅ 仓库 '{repo_config['name']}' 添加成功")
                self.load_repositories()
            else:
                self.show_error("添加仓库失败", "无法添加仓库，请检查配置")

    def remove_repository(self):
        """移除选中的仓库"""
        current_item = self.repo_tree.currentItem()
        if not current_item:
            self.show_warning("请选择仓库", "请先选择要移除的仓库")
            return

        repo_data = current_item.data(0, Qt.UserRole)
        repo_name = repo_data['name']

        # 确认对话框
        reply = QMessageBox.question(
            self, "确认移除",
            f"确定要移除仓库 '{repo_name}' 吗？\n这不会删除本地文件。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.auto_committer.config_manager.remove_repository(repo_name):
                self.append_log(f"✅ 仓库 '{repo_name}' 已移除")
                self.load_repositories()
            else:
                self.show_error("移除失败", f"无法移除仓库 '{repo_name}'")

    def refresh_all(self):
        """刷新所有数据"""
        self.append_log("🔄 刷新所有数据...")
        self.load_repositories()

        # 如果有选中的仓库，更新其详细信息
        current_item = self.repo_tree.currentItem()
        if current_item:
            repo_data = current_item.data(0, Qt.UserRole)
            if repo_data:
                self.update_repo_details(repo_data['name'])

    def commit_selected_repo(self):
        """提交选中的仓库"""
        current_item = self.repo_tree.currentItem()
        if not current_item:
            self.show_warning("请选择仓库", "请先选择要提交的仓库")
            return

        repo_data = current_item.data(0, Qt.UserRole)
        repo_name = repo_data['name']

        # 检查是否有变更
        changes = self.auto_committer.check_repo_changes(repo_name)
        if not changes.get('has_changes'):
            self.show_info("无需提交", f"仓库 '{repo_name}' 没有需要提交的变更")
            return

        # 确认提交
        reply = QMessageBox.question(
            self, "确认提交",
            f"确定要提交仓库 '{repo_name}' 的 {changes.get('total_changes', 0)} 个变更吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            self.perform_commit(repo_name)

    def perform_commit(self, repo_name: str):
        """执行提交操作"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.status_label.setText(f"正在提交 {repo_name}...")

        try:
            success = self.auto_committer.auto_commit_repo(repo_name)

            if success:
                self.append_log(f"✅ 仓库 '{repo_name}' 提交成功")
                self.show_info("提交成功", f"仓库 '{repo_name}' 已成功提交")
                self.refresh_all()
            else:
                self.append_log(f"❌ 仓库 '{repo_name}' 提交失败")
                self.show_error("提交失败", f"仓库 '{repo_name}' 提交失败，请查看日志")

        except Exception as e:
            logger.error(f"提交操作失败: {e}")
            self.append_log(f"❌ 提交异常: {e}")
            self.show_error("提交异常", str(e))

        finally:
            self.progress_bar.setVisible(False)
            self.status_label.setText("就绪")

    def start_monitoring(self):
        """开始监控"""
        try:
            if self.auto_committer.start_monitoring(interval=30):
                self.append_log("🔍 监控已启动")
                self.monitor_status_label.setText("监控: 运行中")
                self.start_monitor_btn.setEnabled(False)
                self.stop_monitor_btn.setEnabled(True)
                self.show_info("监控启动", "文件监控已启动，将自动检测变更")
            else:
                self.show_error("监控启动失败", "无法启动文件监控")

        except Exception as e:
            logger.error(f"启动监控失败: {e}")
            self.show_error("监控启动异常", str(e))

    def stop_monitoring(self):
        """停止监控"""
        try:
            if self.auto_committer.stop_monitoring():
                self.append_log("⏹️ 监控已停止")
                self.monitor_status_label.setText("监控: 未启动")
                self.start_monitor_btn.setEnabled(True)
                self.stop_monitor_btn.setEnabled(False)
                self.show_info("监控停止", "文件监控已停止")
            else:
                self.show_error("监控停止失败", "无法停止文件监控")

        except Exception as e:
            logger.error(f"停止监控失败: {e}")
            self.show_error("监控停止异常", str(e))

    def open_settings(self):
        """打开设置对话框"""
        try:
            # 检查GUI是否可用
            if not GUI_AVAILABLE:
                self.show_error("功能不可用", "PyQt5未安装，无法打开设置对话框。\n请运行: pip install PyQt5")
                return

            # 动态导入设置对话框
            from .dialogs.settings_dialog import SettingsDialog

            # 创建并显示设置对话框
            dialog = SettingsDialog(self, self.auto_committer.config_manager)
            if dialog.exec_() == QDialog.Accepted:
                self.append_log("⚙️ 设置已更新")
                self.refresh_all()

        except ImportError as e:
            logger.error(f"导入设置对话框失败: {e}")
            self.show_error("导入错误", f"无法导入设置对话框:\n{str(e)}\n\n请确保PyQt5已正确安装。")

        except Exception as e:
            logger.error(f"打开设置对话框失败: {e}")
            self.show_error("设置错误", f"打开设置对话框时发生错误:\n{str(e)}")
            self.append_log(f"❌ 设置对话框打开失败: {e}")

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.append_log("🗑️ 日志已清空")

    def export_log(self):
        """导出日志"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出日志",
            f"gitee_auto_commit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件 (*.txt);;所有文件 (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())

                self.append_log(f"💾 日志已导出到: {file_path}")
                self.show_info("导出成功", f"日志已导出到:\n{file_path}")

            except Exception as e:
                logger.error(f"导出日志失败: {e}")
                self.show_error("导出失败", str(e))

    def append_log(self, message: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        self.log_text.append(log_message)

        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def show_info(self, title: str, message: str):
        """显示信息对话框"""
        QMessageBox.information(self, title, message)

    def show_warning(self, title: str, message: str):
        """显示警告对话框"""
        QMessageBox.warning(self, title, message)

    def show_error(self, title: str, message: str):
        """显示错误对话框"""
        QMessageBox.critical(self, title, message)

    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>Gitee自动提交工具 v1.0</h2>
        <p>一个功能完善的Git自动化工具</p>

        <h3>主要功能:</h3>
        <ul>
        <li>🔄 自动监控文件变更</li>
        <li>💾 智能提交消息生成</li>
        <li>📊 实时仓库状态显示</li>
        <li>⚙️ 灵活的配置管理</li>
        <li>🔒 安全的认证信息存储</li>
        </ul>

        <p><b>开发者:</b> Gitee Auto Commit Team</p>
        <p><b>技术栈:</b> Python, PyQt5, GitPython</p>
        """

        QMessageBox.about(self, "关于", about_text)

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止监控
        if self.auto_committer.is_monitoring:
            self.auto_committer.stop_monitoring()

        # 停止状态更新线程
        self.stop_status_updates()

        # 保存窗口状态（可选）

        event.accept()


def main():
    """GUI主函数"""
    if not GUI_AVAILABLE:
        print("❌ PyQt5 未安装，请运行: pip install PyQt5")
        return False

    # 初始化日志系统
    setup_logging(log_level="INFO")

    # 创建应用程序
    app = QApplication(sys.argv)
    app.setApplicationName("Gitee自动提交工具")
    app.setApplicationVersion("1.0")

    try:
        # 创建主窗口
        window = MainWindow()
        window.show()

        # 运行应用程序
        return app.exec_()

    except Exception as e:
        logger.error(f"GUI启动失败: {e}")
        QMessageBox.critical(None, "启动失败", f"GUI启动失败:\n{e}")
        return False


if __name__ == "__main__":
    sys.exit(main())