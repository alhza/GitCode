#!/usr/bin/env python3
"""
Gitee自动提交工具 - 启动脚本

提供多种启动方式的统一入口。
"""

import sys
import os
import subprocess
from pathlib import Path

def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    Gitee自动提交工具 v1.0                    ║
║                                                              ║
║  🔄 自动监控文件变更    💾 智能提交消息生成                   ║
║  📊 实时仓库状态显示    ⚙️ 灵活的配置管理                    ║
║  🔒 安全的认证信息存储  🖥️ 现代化图形界面                    ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    return True

def check_dependencies():
    """检查基础依赖"""
    required_packages = {
        'git': 'GitPython',
        'yaml': 'PyYAML', 
        'cryptography': 'cryptography',
        'click': 'click',
        'rich': 'rich'
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("❌ 缺少以下基础依赖包:")
        for pkg in missing:
            print(f"   - {pkg}")
        print(f"\n请运行: pip install {' '.join(missing)}")
        return False
    
    return True

def check_gui_dependencies():
    """检查GUI依赖"""
    try:
        import PyQt5
        return True
    except ImportError:
        return False

def show_menu():
    """显示启动菜单"""
    print("\n📋 请选择启动方式:")
    print("1. 🖥️  启动图形界面 (推荐)")
    print("2. 💻 启动命令行界面")
    print("3. ⚙️  初始化配置")
    print("4. 📖 查看帮助")
    print("5. 🚪 退出")
    
    while True:
        try:
            choice = input("\n请输入选择 (1-5): ").strip()
            if choice in ['1', '2', '3', '4', '5']:
                return int(choice)
            else:
                print("❌ 请输入有效的选择 (1-5)")
        except KeyboardInterrupt:
            print("\n👋 再见!")
            return 5
        except Exception:
            print("❌ 输入错误，请重试")

def start_gui():
    """启动GUI界面"""
    if not check_gui_dependencies():
        print("❌ GUI依赖未安装")
        print("请运行: pip install PyQt5")
        
        choice = input("\n是否要安装GUI依赖? (y/N): ").strip().lower()
        if choice == 'y':
            try:
                print("📦 正在安装PyQt5...")
                subprocess.run([sys.executable, "-m", "pip", "install", "PyQt5"], check=True)
                print("✅ PyQt5安装成功")
            except subprocess.CalledProcessError:
                print("❌ PyQt5安装失败")
                return False
        else:
            return False
    
    try:
        print("🚀 启动图形界面...")
        subprocess.run([sys.executable, "gui_main.py"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动GUI失败: {e}")
        return False
    except FileNotFoundError:
        print("❌ 找不到gui_main.py文件")
        return False

def start_cli():
    """启动命令行界面"""
    try:
        print("💻 启动命令行界面...")
        print("使用 'python main.py --help' 查看所有可用命令")
        subprocess.run([sys.executable, "main.py", "--help"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动CLI失败: {e}")
        return False
    except FileNotFoundError:
        print("❌ 找不到main.py文件")
        return False

def init_config():
    """初始化配置"""
    try:
        print("⚙️ 初始化配置...")
        subprocess.run([sys.executable, "main.py", "init"], check=True)
        
        print("\n✅ 配置初始化完成!")
        print("📋 下一步操作:")
        print("1. 使用 'python main.py add-repo' 添加Git仓库")
        print("2. 使用 'python main.py gui' 启动图形界面")
        print("3. 使用 'python main.py monitor' 开始监控")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 初始化失败: {e}")
        return False

def show_help():
    """显示帮助信息"""
    help_text = """
🔧 Gitee自动提交工具使用指南

📁 项目文件说明:
  • main.py        - 命令行界面入口
  • gui_main.py    - 图形界面入口  
  • start.py       - 统一启动脚本 (本文件)
  • src/           - 源代码目录
  • config/        - 配置文件目录
  • logs/          - 日志文件目录

💻 命令行使用:
  python main.py init                    # 初始化配置
  python main.py add-repo               # 添加仓库
  python main.py status                 # 查看状态
  python main.py commit --repo NAME     # 手动提交
  python main.py monitor               # 开始监控
  python main.py gui                   # 启动GUI

🖥️ 图形界面使用:
  python gui_main.py                   # 直接启动GUI
  python start.py                     # 使用启动脚本

📖 更多帮助:
  • README.md - 详细使用说明
  • working.md - 技术设计文档
  • PROJECT_SUMMARY.md - 项目总结

🌐 在线资源:
  • Gitee: https://gitee.com
  • Python: https://python.org
  • PyQt5: https://pypi.org/project/PyQt5/
"""
    print(help_text)

def main():
    """主函数"""
    print_banner()
    
    # 检查Python版本
    if not check_python_version():
        return 1
    
    # 检查基础依赖
    if not check_dependencies():
        choice = input("\n是否要安装缺少的依赖? (y/N): ").strip().lower()
        if choice == 'y':
            try:
                print("📦 正在安装依赖...")
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
                print("✅ 依赖安装成功")
            except subprocess.CalledProcessError:
                print("❌ 依赖安装失败")
                return 1
        else:
            return 1
    
    # 显示菜单并处理选择
    while True:
        choice = show_menu()
        
        if choice == 1:  # GUI
            if start_gui():
                break
        elif choice == 2:  # CLI
            if start_cli():
                break
        elif choice == 3:  # 初始化
            init_config()
        elif choice == 4:  # 帮助
            show_help()
        elif choice == 5:  # 退出
            print("👋 再见!")
            break
        
        input("\n按回车键继续...")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n👋 程序已中断")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        sys.exit(1)
