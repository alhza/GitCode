"""
仓库配置对话框

用于添加和编辑Git仓库配置。
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
        QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
        QFileDialog, QMessageBox, QDialogButtonBox, QGroupBox,
        QTextEdit, QSpacerItem, QSizePolicy
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    class QDialog: pass

from ...utils.logger import get_logger

logger = get_logger(__name__)


class RepoDialog(QDialog):
    """仓库配置对话框"""
    
    def __init__(self, parent=None, repo_config: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        
        if not GUI_AVAILABLE:
            raise ImportError("PyQt5 not available")
        
        self.repo_config = repo_config or {}
        self.is_edit_mode = bool(repo_config)
        
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """初始化用户界面"""
        title = "编辑仓库" if self.is_edit_mode else "添加仓库"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 400)
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 基本信息组
        basic_group = QGroupBox("📁 基本信息")
        basic_layout = QFormLayout(basic_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: my-project")
        basic_layout.addRow("仓库名称 *:", self.name_edit)
        
        # 本地路径选择
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择Git仓库的本地路径")
        self.browse_btn = QPushButton("📁 浏览")
        self.browse_btn.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        basic_layout.addRow("本地路径 *:", path_layout)
        
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://gitee.com/username/repository.git")
        basic_layout.addRow("远程URL *:", self.url_edit)
        
        self.branch_edit = QLineEdit()
        self.branch_edit.setText("main")
        self.branch_edit.setPlaceholderText("main")
        basic_layout.addRow("分支名称:", self.branch_edit)
        
        layout.addWidget(basic_group)
        
        # 选项组
        options_group = QGroupBox("⚙️ 选项")
        options_layout = QFormLayout(options_group)
        
        self.enabled_checkbox = QCheckBox("启用此仓库")
        self.enabled_checkbox.setChecked(True)
        options_layout.addRow("", self.enabled_checkbox)
        
        layout.addWidget(options_group)
        
        # 认证信息组
        auth_group = QGroupBox("🔐 认证信息 (可选)")
        auth_layout = QFormLayout(auth_group)
        
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Git用户名")
        auth_layout.addRow("用户名:", self.username_edit)
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("user@example.com")
        auth_layout.addRow("邮箱:", self.email_edit)
        
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.Password)
        self.token_edit.setPlaceholderText("访问令牌 (用于HTTPS认证)")
        auth_layout.addRow("访问令牌:", self.token_edit)
        
        layout.addWidget(auth_group)
        
        # 测试连接按钮
        test_layout = QHBoxLayout()
        self.test_btn = QPushButton("🔗 测试连接")
        self.test_btn.clicked.connect(self.test_connection)
        test_layout.addWidget(self.test_btn)
        test_layout.addStretch()
        layout.addLayout(test_layout)
        
        # 按钮组
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal
        )
        button_box.accepted.connect(self.accept_dialog)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        # 设置样式
        self.setStyleSheet("""
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
            QLineEdit {
                padding: 8px;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
            }
        """)
    
    def load_data(self):
        """加载数据到表单"""
        if self.repo_config:
            self.name_edit.setText(self.repo_config.get('name', ''))
            self.path_edit.setText(self.repo_config.get('local_path', ''))
            self.url_edit.setText(self.repo_config.get('remote_url', ''))
            self.branch_edit.setText(self.repo_config.get('branch', 'main'))
            self.enabled_checkbox.setChecked(self.repo_config.get('enabled', True))
            
            # 如果是编辑模式，禁用名称编辑
            if self.is_edit_mode:
                self.name_edit.setEnabled(False)
    
    def browse_folder(self):
        """浏览文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self, "选择Git仓库目录",
            self.path_edit.text() or os.path.expanduser("~")
        )
        
        if folder:
            self.path_edit.setText(folder)
            
            # 尝试自动填充仓库名称
            if not self.name_edit.text():
                folder_name = Path(folder).name
                self.name_edit.setText(folder_name)
    
    def test_connection(self):
        """测试Git连接"""
        local_path = self.path_edit.text().strip()
        
        if not local_path:
            QMessageBox.warning(self, "警告", "请先选择本地路径")
            return
        
        if not os.path.exists(local_path):
            QMessageBox.warning(self, "警告", "本地路径不存在")
            return
        
        try:
            # 检查是否是Git仓库
            git_dir = Path(local_path) / ".git"
            if not git_dir.exists():
                reply = QMessageBox.question(
                    self, "不是Git仓库",
                    "选择的目录不是Git仓库，是否要初始化为Git仓库？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    import subprocess
                    result = subprocess.run(
                        ["git", "init"], 
                        cwd=local_path,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        QMessageBox.information(self, "成功", "Git仓库初始化成功")
                    else:
                        QMessageBox.critical(self, "失败", f"Git初始化失败:\n{result.stderr}")
                        return
                else:
                    return
            
            # 测试Git状态
            import subprocess
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=local_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                QMessageBox.information(self, "连接成功", "Git仓库连接正常")
            else:
                QMessageBox.warning(self, "连接失败", f"Git状态检查失败:\n{result.stderr}")
                
        except Exception as e:
            QMessageBox.critical(self, "测试失败", f"连接测试失败:\n{str(e)}")
    
    def validate_input(self) -> bool:
        """验证输入"""
        # 检查必填字段
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入仓库名称")
            self.name_edit.setFocus()
            return False
        
        if not self.path_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请选择本地路径")
            self.path_edit.setFocus()
            return False
        
        if not self.url_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入远程URL")
            self.url_edit.setFocus()
            return False
        
        # 检查路径是否存在
        local_path = self.path_edit.text().strip()
        if not os.path.exists(local_path):
            QMessageBox.warning(self, "验证失败", "本地路径不存在")
            return False
        
        # 检查仓库名称格式
        name = self.name_edit.text().strip()
        if not name.replace('-', '').replace('_', '').isalnum():
            QMessageBox.warning(self, "验证失败", "仓库名称只能包含字母、数字、下划线和连字符")
            return False
        
        # 检查URL格式
        url = self.url_edit.text().strip()
        if not (url.startswith('http://') or url.startswith('https://') or url.startswith('git@')):
            QMessageBox.warning(self, "验证失败", "远程URL格式不正确")
            return False
        
        return True
    
    def accept_dialog(self):
        """接受对话框"""
        if self.validate_input():
            self.accept()
    
    def get_repo_config(self) -> Dict[str, Any]:
        """获取仓库配置"""
        config = {
            'name': self.name_edit.text().strip(),
            'local_path': self.path_edit.text().strip(),
            'remote_url': self.url_edit.text().strip(),
            'branch': self.branch_edit.text().strip() or 'main',
            'enabled': self.enabled_checkbox.isChecked()
        }
        
        return config
    
    def get_auth_info(self) -> Optional[Dict[str, str]]:
        """获取认证信息"""
        username = self.username_edit.text().strip()
        email = self.email_edit.text().strip()
        token = self.token_edit.text().strip()
        
        if username or email or token:
            return {
                'username': username,
                'email': email,
                'token': token
            }
        
        return None
