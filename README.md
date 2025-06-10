# Gitee自动提交工具

一个功能完善的Gitee自动提交工具，支持文件监控、定时提交、智能消息生成等功能，提高开发效率。

## ✨ 主要特性

- 🔄 **自动监控**: 实时监控文件变更，自动触发提交
- ⏰ **定时提交**: 支持按时间定时自动提交
- 🧠 **智能消息**: 自动生成语义化的提交消息
- 🖥️ **图形界面**: 现代化的GUI界面，操作简单直观
- 🔒 **安全可靠**: 敏感信息加密存储，完整的操作日志
- 📦 **多仓库**: 同时管理多个Git仓库
- 🎨 **可定制**: 丰富的配置选项，满足不同需求

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化配置

```bash
python main.py init
```

### 3. 添加Git仓库

```bash
python main.py add-repo --name myproject --path /path/to/repo --url https://gitee.com/username/repo.git
```

### 4. 查看仓库状态

```bash
python main.py status
```

### 5. 启动图形界面

```bash
python main.py gui
```

## 📋 命令行使用

### 基本命令

```bash
# 初始化配置
python main.py init

# 添加仓库
python main.py add-repo --name PROJECT_NAME --path LOCAL_PATH --url REMOTE_URL

# 列出所有仓库
python main.py list-repos

# 查看仓库状态
python main.py status [--repo REPO_NAME]

# 手动提交
python main.py commit --repo REPO_NAME [--message "提交消息"]

# 移除仓库
python main.py remove-repo --repo REPO_NAME

# 启动图形界面
python main.py gui
```

### 高级选项

```bash
# 指定配置目录
python main.py --config-dir /custom/config/path COMMAND

# 查看版本信息
python main.py --version

# 查看帮助
python main.py --help
python main.py COMMAND --help
```

## 🖥️ 图形界面

启动GUI界面：

```bash
python main.py gui
```

### 主要功能

- **仓库管理**: 添加、编辑、删除Git仓库
- **实时监控**: 可视化显示文件变更状态
- **快速提交**: 一键提交和推送
- **日志查看**: 实时查看操作日志
- **设置配置**: 图形化配置管理

## ⚙️ 配置说明

配置文件位于 `config/settings.yaml`：

```yaml
# 全局设置
global:
  log_level: "INFO"
  max_log_files: 10
  auto_save: true

# 提交配置
commit:
  message_template: "{type}: {description}"
  auto_message: true
  max_files_per_commit: 50

# 调度配置
schedule:
  enabled: false
  mode: "daily"
  time: "18:00"

# 监控配置
monitoring:
  enabled: true
  debounce_seconds: 5
  ignore_patterns:
    - "*.log"
    - "node_modules/"
    - ".git/"
```

## 📁 项目结构

```
gitee-auto-commit/
├── src/                    # 源代码
│   ├── config/            # 配置管理
│   ├── git_ops/           # Git操作
│   ├── monitor/           # 文件监控
│   ├── scheduler/         # 任务调度
│   ├── gui/              # 图形界面
│   └── utils/            # 工具函数
├── config/               # 配置文件
├── logs/                # 日志文件
├── tests/               # 测试文件
├── requirements.txt     # 依赖包
├── main.py             # 命令行入口
└── README.md           # 项目说明
```

## 🔧 开发说明

### 环境要求

- Python 3.8+
- Git 2.0+
- PyQt5 (GUI界面)

### 开发安装

```bash
# 克隆项目
git clone https://gitee.com/username/gitee-auto-commit.git
cd gitee-auto-commit

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/

# 代码格式化
black src/
```

### 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📝 更新日志

### v1.0.0 (2024-01-01)

- ✨ 初始版本发布
- 🔄 基础的Git操作功能
- ⚙️ 配置管理系统
- 📝 命令行界面
- 🖥️ 图形用户界面

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🤝 支持

如果你觉得这个项目有用，请给它一个 ⭐️！

- 📧 邮箱: support@gitee-auto-commit.com
- 🐛 问题反馈: [Issues](https://gitee.com/username/gitee-auto-commit/issues)
- 💬 讨论: [Discussions](https://gitee.com/username/gitee-auto-commit/discussions)

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！
