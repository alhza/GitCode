#!/usr/bin/env python3
"""
Gitee自动提交工具 - GUI程序入口

启动图形用户界面版本的Gitee自动提交工具。
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_dependencies():
    """检查依赖包"""
    missing_deps = []
    
    try:
        import PyQt5
    except ImportError:
        missing_deps.append("PyQt5")
    
    try:
        import git
    except ImportError:
        missing_deps.append("GitPython")
    
    try:
        import yaml
    except ImportError:
        missing_deps.append("PyYAML")
    
    try:
        import cryptography
    except ImportError:
        missing_deps.append("cryptography")
    
    if missing_deps:
        print("❌ 缺少以下依赖包:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n请运行以下命令安装:")
        print(f"pip install {' '.join(missing_deps)}")
        return False
    
    return True

def main():
    """主函数"""
    print("🚀 启动Gitee自动提交工具 GUI版本...")
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    try:
        # 导入GUI模块
        from src.gui.main_window import main as gui_main
        
        # 启动GUI
        return gui_main()
        
    except ImportError as e:
        print(f"❌ 导入GUI模块失败: {e}")
        print("请确保所有依赖包已正确安装")
        return 1
    
    except Exception as e:
        print(f"❌ 启动GUI失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
