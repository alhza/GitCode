"""
设置对话框

用于配置应用程序的全局设置。
"""

from typing import Dict, Any

try:
    from PyQt5.QtWidgets import (
        QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
        QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, QSpinBox,
        QTextEdit, QGroupBox, QDialogButtonBox, QFileDialog, QMessageBox,
        QSlider, QDoubleSpinBox
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    class QDialog: pass
    class QWidget: pass

from ...utils.logger import get_logger

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        
        if not GUI_AVAILABLE:
            raise ImportError("PyQt5 not available")
        
        self.config_manager = config_manager
        self.config = config_manager.load_config() if config_manager else {}
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(600, 500)
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 创建各个选项卡
        self.create_general_tab()
        self.create_commit_tab()
        self.create_monitoring_tab()
        self.create_advanced_tab()
        
        # 按钮组
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults,
            Qt.Horizontal
        )
        button_box.accepted.connect(self.accept_settings)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        
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
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                padding: 6px;
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
    
    def create_general_tab(self):
        """创建常规设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 日志设置组
        log_group = QGroupBox("📋 日志设置")
        log_layout = QFormLayout(log_group)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        log_layout.addRow("日志级别:", self.log_level_combo)
        
        self.max_log_files_spin = QSpinBox()
        self.max_log_files_spin.setRange(1, 100)
        self.max_log_files_spin.setValue(10)
        log_layout.addRow("最大日志文件数:", self.max_log_files_spin)
        
        layout.addWidget(log_group)
        
        # 界面设置组
        ui_group = QGroupBox("🎨 界面设置")
        ui_layout = QFormLayout(ui_group)
        
        self.auto_refresh_checkbox = QCheckBox("自动刷新状态")
        self.auto_refresh_checkbox.setChecked(True)
        ui_layout.addRow("", self.auto_refresh_checkbox)
        
        self.show_notifications_checkbox = QCheckBox("显示系统通知")
        self.show_notifications_checkbox.setChecked(True)
        ui_layout.addRow("", self.show_notifications_checkbox)
        
        self.minimize_to_tray_checkbox = QCheckBox("最小化到系统托盘")
        self.minimize_to_tray_checkbox.setChecked(False)
        ui_layout.addRow("", self.minimize_to_tray_checkbox)
        
        layout.addWidget(ui_group)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "🔧 常规")
    
    def create_commit_tab(self):
        """创建提交设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 提交消息设置组
        message_group = QGroupBox("📝 提交消息")
        message_layout = QFormLayout(message_group)
        
        self.message_template_edit = QLineEdit()
        self.message_template_edit.setPlaceholderText("{type}: {description}")
        message_layout.addRow("消息模板:", self.message_template_edit)
        
        self.auto_message_checkbox = QCheckBox("自动生成提交消息")
        self.auto_message_checkbox.setChecked(True)
        message_layout.addRow("", self.auto_message_checkbox)
        
        self.max_files_spin = QSpinBox()
        self.max_files_spin.setRange(1, 1000)
        self.max_files_spin.setValue(50)
        message_layout.addRow("单次提交最大文件数:", self.max_files_spin)
        
        layout.addWidget(message_group)
        
        # 提交行为设置组
        behavior_group = QGroupBox("⚙️ 提交行为")
        behavior_layout = QFormLayout(behavior_group)
        
        self.auto_push_checkbox = QCheckBox("提交后自动推送")
        self.auto_push_checkbox.setChecked(False)
        behavior_layout.addRow("", self.auto_push_checkbox)
        
        self.confirm_before_commit_checkbox = QCheckBox("提交前确认")
        self.confirm_before_commit_checkbox.setChecked(True)
        behavior_layout.addRow("", self.confirm_before_commit_checkbox)
        
        layout.addWidget(behavior_group)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "💾 提交")
    
    def create_monitoring_tab(self):
        """创建监控设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 监控设置组
        monitor_group = QGroupBox("🔍 文件监控")
        monitor_layout = QFormLayout(monitor_group)
        
        self.monitoring_enabled_checkbox = QCheckBox("启用文件监控")
        self.monitoring_enabled_checkbox.setChecked(True)
        monitor_layout.addRow("", self.monitoring_enabled_checkbox)
        
        self.debounce_spin = QDoubleSpinBox()
        self.debounce_spin.setRange(0.1, 60.0)
        self.debounce_spin.setValue(5.0)
        self.debounce_spin.setSuffix(" 秒")
        monitor_layout.addRow("防抖时间:", self.debounce_spin)
        
        self.check_interval_spin = QSpinBox()
        self.check_interval_spin.setRange(10, 3600)
        self.check_interval_spin.setValue(60)
        self.check_interval_spin.setSuffix(" 秒")
        monitor_layout.addRow("检查间隔:", self.check_interval_spin)
        
        layout.addWidget(monitor_group)
        
        # 忽略模式设置组
        ignore_group = QGroupBox("🚫 忽略模式")
        ignore_layout = QVBoxLayout(ignore_group)
        
        ignore_layout.addWidget(QLabel("忽略的文件模式 (每行一个):"))
        
        self.ignore_patterns_edit = QTextEdit()
        self.ignore_patterns_edit.setMaximumHeight(150)
        default_patterns = [
            "*.log", "*.tmp", "*.pyc", "node_modules/",
            ".git/", "__pycache__/", ".vscode/", ".idea/",
            "*.swp", "*.swo", ".DS_Store", "Thumbs.db"
        ]
        self.ignore_patterns_edit.setPlainText("\n".join(default_patterns))
        ignore_layout.addWidget(self.ignore_patterns_edit)
        
        layout.addWidget(ignore_group)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "🔍 监控")
    
    def create_advanced_tab(self):
        """创建高级设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 性能设置组
        performance_group = QGroupBox("⚡ 性能设置")
        performance_layout = QFormLayout(performance_group)
        
        self.max_history_spin = QSpinBox()
        self.max_history_spin.setRange(10, 10000)
        self.max_history_spin.setValue(1000)
        performance_layout.addRow("最大历史记录数:", self.max_history_spin)
        
        self.cache_enabled_checkbox = QCheckBox("启用状态缓存")
        self.cache_enabled_checkbox.setChecked(True)
        performance_layout.addRow("", self.cache_enabled_checkbox)
        
        layout.addWidget(performance_group)
        
        # 安全设置组
        security_group = QGroupBox("🔒 安全设置")
        security_layout = QFormLayout(security_group)
        
        self.encrypt_config_checkbox = QCheckBox("加密配置文件")
        self.encrypt_config_checkbox.setChecked(True)
        security_layout.addRow("", self.encrypt_config_checkbox)
        
        self.auto_lock_checkbox = QCheckBox("自动锁定敏感操作")
        self.auto_lock_checkbox.setChecked(False)
        security_layout.addRow("", self.auto_lock_checkbox)
        
        layout.addWidget(security_group)
        
        # 备份设置组
        backup_group = QGroupBox("💾 备份设置")
        backup_layout = QFormLayout(backup_group)
        
        self.auto_backup_checkbox = QCheckBox("自动备份配置")
        self.auto_backup_checkbox.setChecked(True)
        backup_layout.addRow("", self.auto_backup_checkbox)
        
        self.backup_interval_spin = QSpinBox()
        self.backup_interval_spin.setRange(1, 30)
        self.backup_interval_spin.setValue(7)
        self.backup_interval_spin.setSuffix(" 天")
        backup_layout.addRow("备份间隔:", self.backup_interval_spin)
        
        layout.addWidget(backup_group)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "🔧 高级")
    
    def load_settings(self):
        """加载设置到界面"""
        try:
            # 常规设置
            global_config = self.config.get('global', {})
            self.log_level_combo.setCurrentText(global_config.get('log_level', 'INFO'))
            self.max_log_files_spin.setValue(global_config.get('max_log_files', 10))
            
            # 提交设置
            commit_config = self.config.get('commit', {})
            self.message_template_edit.setText(commit_config.get('message_template', '{type}: {description}'))
            self.auto_message_checkbox.setChecked(commit_config.get('auto_message', True))
            self.max_files_spin.setValue(commit_config.get('max_files_per_commit', 50))
            self.auto_push_checkbox.setChecked(commit_config.get('auto_push', False))
            
            # 监控设置
            monitoring_config = self.config.get('monitoring', {})
            self.monitoring_enabled_checkbox.setChecked(monitoring_config.get('enabled', True))
            self.debounce_spin.setValue(monitoring_config.get('debounce_seconds', 5.0))
            
            ignore_patterns = monitoring_config.get('ignore_patterns', [])
            if ignore_patterns:
                self.ignore_patterns_edit.setPlainText('\n'.join(ignore_patterns))
            
        except Exception as e:
            logger.error(f"加载设置失败: {e}")
    
    def save_settings(self) -> Dict[str, Any]:
        """保存设置"""
        try:
            # 更新配置
            self.config['global'] = {
                'log_level': self.log_level_combo.currentText(),
                'max_log_files': self.max_log_files_spin.value(),
                'auto_save': True
            }
            
            self.config['commit'] = {
                'message_template': self.message_template_edit.text(),
                'auto_message': self.auto_message_checkbox.isChecked(),
                'max_files_per_commit': self.max_files_spin.value(),
                'auto_push': self.auto_push_checkbox.isChecked()
            }
            
            ignore_patterns = [
                line.strip() for line in self.ignore_patterns_edit.toPlainText().split('\n')
                if line.strip()
            ]
            
            self.config['monitoring'] = {
                'enabled': self.monitoring_enabled_checkbox.isChecked(),
                'debounce_seconds': self.debounce_spin.value(),
                'ignore_patterns': ignore_patterns
            }
            
            return self.config
            
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            return {}
    
    def restore_defaults(self):
        """恢复默认设置"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要恢复所有设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 重置为默认值
            self.log_level_combo.setCurrentText("INFO")
            self.max_log_files_spin.setValue(10)
            self.message_template_edit.setText("{type}: {description}")
            self.auto_message_checkbox.setChecked(True)
            self.max_files_spin.setValue(50)
            self.auto_push_checkbox.setChecked(False)
            self.monitoring_enabled_checkbox.setChecked(True)
            self.debounce_spin.setValue(5.0)
            
            default_patterns = [
                "*.log", "*.tmp", "*.pyc", "node_modules/",
                ".git/", "__pycache__/", ".vscode/", ".idea/",
                "*.swp", "*.swo", ".DS_Store", "Thumbs.db"
            ]
            self.ignore_patterns_edit.setPlainText("\n".join(default_patterns))
    
    def accept_settings(self):
        """接受设置"""
        try:
            config = self.save_settings()
            
            if self.config_manager and config:
                if self.config_manager.save_config(config):
                    QMessageBox.information(self, "成功", "设置已保存")
                    self.accept()
                else:
                    QMessageBox.critical(self, "失败", "保存设置失败")
            else:
                self.accept()
                
        except Exception as e:
            logger.error(f"接受设置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存设置时发生错误:\n{str(e)}")
