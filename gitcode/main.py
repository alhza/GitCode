#!/usr/bin/env python3
"""
Gitee自动提交工具 - 命令行入口

提供命令行界面来管理Git仓库的自动提交功能。
"""

import sys
import click
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.utils.logger import setup_logging, get_logger
    from src.config.config_manager import ConfigManager
    from src.git_ops.git_handler import GitHandler

    # 初始化日志系统
    setup_logging()
    logger = get_logger(__name__)
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保所有依赖已正确安装: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ 初始化失败: {e}")
    sys.exit(1)


@click.group()
@click.version_option(version="1.0.0", prog_name="Gitee Auto Commit")
@click.option('--config-dir', default='config', help='配置文件目录')
@click.pass_context
def cli(ctx, config_dir):
    """Gitee自动提交工具 - 提高开发效率的Git自动化工具"""
    ctx.ensure_object(dict)
    ctx.obj['config_dir'] = config_dir
    ctx.obj['config_manager'] = ConfigManager(config_dir)


@cli.command()
@click.pass_context
def init(ctx):
    """初始化配置文件"""
    try:
        config_manager = ctx.obj['config_manager']
        
        # 创建默认配置
        config = config_manager.load_config()
        
        click.echo("🎉 Gitee自动提交工具初始化成功！")
        click.echo(f"📁 配置目录: {config_manager.config_dir}")
        click.echo(f"📄 配置文件: {config_manager.settings_file}")
        
        # 显示下一步操作提示
        click.echo("\n📋 下一步操作:")
        click.echo("1. 使用 'python main.py add-repo' 添加Git仓库")
        click.echo("2. 使用 'python main.py monitor' 开始监控文件变更")
        click.echo("3. 使用 'python main.py gui' 启动图形界面")
        
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        click.echo(f"❌ 初始化失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--name', required=True, help='仓库名称')
@click.option('--path', required=True, help='本地路径')
@click.option('--url', required=True, help='远程仓库URL')
@click.option('--branch', default='main', help='分支名称')
@click.option('--enabled/--disabled', default=True, help='是否启用')
@click.pass_context
def add_repo(ctx, name, path, url, branch, enabled):
    """添加Git仓库"""
    try:
        config_manager = ctx.obj['config_manager']
        
        # 验证路径是否存在
        repo_path = Path(path)
        if not repo_path.exists():
            click.echo(f"❌ 路径不存在: {path}", err=True)
            return
        
        # 创建仓库配置
        repo_config = {
            "name": name,
            "local_path": str(repo_path.absolute()),
            "remote_url": url,
            "branch": branch,
            "enabled": enabled
        }
        
        # 添加仓库
        if config_manager.add_repository(repo_config):
            click.echo(f"✅ 仓库 '{name}' 添加成功！")
            
            # 验证Git仓库
            git_handler = GitHandler(path)
            if git_handler.is_valid_repo():
                status = git_handler.check_status()
                click.echo(f"📊 仓库状态: 分支 {status.get('branch', 'unknown')}")
            else:
                click.echo("⚠️  警告: 不是有效的Git仓库，请检查路径")
        else:
            click.echo(f"❌ 添加仓库失败", err=True)
            
    except Exception as e:
        logger.error(f"添加仓库失败: {e}")
        click.echo(f"❌ 添加仓库失败: {e}", err=True)


@cli.command()
@click.option('--repo', help='仓库名称，不指定则显示所有仓库')
@click.pass_context
def status(ctx, repo):
    """查看仓库状态"""
    try:
        config_manager = ctx.obj['config_manager']
        config = config_manager.load_config()
        repositories = config.get("repositories", [])
        
        if not repositories:
            click.echo("📭 没有配置的仓库")
            return
        
        # 过滤仓库
        if repo:
            repositories = [r for r in repositories if r.get("name") == repo]
            if not repositories:
                click.echo(f"❌ 仓库 '{repo}' 不存在", err=True)
                return
        
        # 显示仓库状态
        for repo_config in repositories:
            name = repo_config.get("name")
            path = repo_config.get("local_path")
            enabled = repo_config.get("enabled", True)
            
            click.echo(f"\n📁 仓库: {name}")
            click.echo(f"   路径: {path}")
            click.echo(f"   状态: {'启用' if enabled else '禁用'}")
            
            if enabled:
                git_handler = GitHandler(path)
                if git_handler.is_valid_repo():
                    status = git_handler.check_status()
                    
                    click.echo(f"   分支: {status.get('branch', 'unknown')}")
                    click.echo(f"   是否有变更: {'是' if status.get('is_dirty') else '否'}")
                    
                    if status.get('untracked_files'):
                        click.echo(f"   未跟踪文件: {len(status['untracked_files'])} 个")
                    
                    if status.get('modified_files'):
                        click.echo(f"   已修改文件: {len(status['modified_files'])} 个")
                    
                    if status.get('last_commit'):
                        last_commit = status['last_commit']
                        click.echo(f"   最后提交: {last_commit['hash']} - {last_commit['message'][:50]}...")
                else:
                    click.echo("   ❌ 无效的Git仓库")
            
    except Exception as e:
        logger.error(f"查看状态失败: {e}")
        click.echo(f"❌ 查看状态失败: {e}", err=True)


@cli.command()
@click.option('--repo', required=True, help='仓库名称')
@click.option('--message', help='提交消息')
@click.option('--auto-message/--no-auto-message', default=True, help='是否自动生成提交消息')
@click.pass_context
def commit(ctx, repo, message, auto_message):
    """手动提交指定仓库"""
    try:
        config_manager = ctx.obj['config_manager']
        repo_config = config_manager.get_repo_config(repo)
        
        if not repo_config:
            click.echo(f"❌ 仓库 '{repo}' 不存在", err=True)
            return
        
        if not repo_config.get("enabled", True):
            click.echo(f"❌ 仓库 '{repo}' 已禁用", err=True)
            return
        
        path = repo_config.get("local_path")
        git_handler = GitHandler(path)
        
        if not git_handler.is_valid_repo():
            click.echo(f"❌ 无效的Git仓库: {path}", err=True)
            return
        
        # 检查是否有变更
        status = git_handler.check_status()
        has_changes = (status.get('is_dirty') or
                      status.get('untracked_files') or
                      status.get('staged_files'))

        if not has_changes:
            click.echo("📭 没有需要提交的变更")
            return
        
        # 添加文件到暂存区
        click.echo("📝 添加文件到暂存区...")
        if not git_handler.add_files():
            click.echo("❌ 添加文件失败", err=True)
            return
        
        # 生成提交消息
        if not message:
            if auto_message:
                # TODO: 实现智能消息生成
                message = f"自动提交 - {len(status.get('modified_files', []) + status.get('untracked_files', []))} 个文件变更"
            else:
                message = click.prompt("请输入提交消息")
        
        # 获取认证信息
        auth_info = config_manager.get_auth_info(repo)
        author_name = auth_info.get("username") if auth_info else None
        author_email = auth_info.get("email") if auth_info else None
        
        # 创建提交
        click.echo("💾 创建提交...")
        if git_handler.create_commit(message, author_name, author_email):
            click.echo(f"✅ 提交成功: {message}")
            
            # 询问是否推送
            if click.confirm("是否推送到远程仓库?"):
                click.echo("🚀 推送到远程仓库...")
                if git_handler.push_changes():
                    click.echo("✅ 推送成功!")
                else:
                    click.echo("❌ 推送失败", err=True)
        else:
            click.echo("❌ 提交失败", err=True)
            
    except Exception as e:
        logger.error(f"提交失败: {e}")
        click.echo(f"❌ 提交失败: {e}", err=True)


@cli.command()
@click.pass_context
def list_repos(ctx):
    """列出所有配置的仓库"""
    try:
        config_manager = ctx.obj['config_manager']
        config = config_manager.load_config()
        repositories = config.get("repositories", [])
        
        if not repositories:
            click.echo("📭 没有配置的仓库")
            return
        
        click.echo("📋 配置的仓库列表:")
        for i, repo in enumerate(repositories, 1):
            name = repo.get("name")
            path = repo.get("local_path")
            enabled = repo.get("enabled", True)
            status_icon = "✅" if enabled else "⏸️"
            
            click.echo(f"{i}. {status_icon} {name}")
            click.echo(f"   路径: {path}")
            click.echo(f"   URL: {repo.get('remote_url')}")
            click.echo(f"   分支: {repo.get('branch')}")
            
    except Exception as e:
        logger.error(f"列出仓库失败: {e}")
        click.echo(f"❌ 列出仓库失败: {e}", err=True)


@cli.command()
@click.option('--repo', required=True, help='仓库名称')
@click.pass_context
def remove_repo(ctx, repo):
    """移除仓库配置"""
    try:
        config_manager = ctx.obj['config_manager']
        
        if not config_manager.get_repo_config(repo):
            click.echo(f"❌ 仓库 '{repo}' 不存在", err=True)
            return
        
        if click.confirm(f"确定要移除仓库 '{repo}' 吗?"):
            if config_manager.remove_repository(repo):
                click.echo(f"✅ 仓库 '{repo}' 已移除")
            else:
                click.echo(f"❌ 移除仓库失败", err=True)
        
    except Exception as e:
        logger.error(f"移除仓库失败: {e}")
        click.echo(f"❌ 移除仓库失败: {e}", err=True)


@cli.command()
@click.option('--repo', help='仓库名称，不指定则监控所有启用的仓库')
@click.option('--interval', default=5, help='检查间隔（秒）')
@click.pass_context
def monitor(ctx, repo, interval):
    """开始监控文件变更"""
    try:
        config_manager = ctx.obj['config_manager']
        config = config_manager.load_config()
        repositories = config.get("repositories", [])

        if not repositories:
            click.echo("📭 没有配置的仓库")
            return

        # 过滤仓库
        if repo:
            repositories = [r for r in repositories if r.get("name") == repo]
            if not repositories:
                click.echo(f"❌ 仓库 '{repo}' 不存在", err=True)
                return

        # 过滤启用的仓库
        enabled_repos = [r for r in repositories if r.get("enabled", True)]
        if not enabled_repos:
            click.echo("📭 没有启用的仓库")
            return

        click.echo(f"🔍 开始监控 {len(enabled_repos)} 个仓库...")

        # 简单的监控循环（暂时不使用watchdog）
        try:
            import time
            from src.git_ops.git_handler import GitHandler

            while True:
                for repo_config in enabled_repos:
                    repo_name = repo_config.get("name")
                    repo_path = repo_config.get("local_path")

                    git_handler = GitHandler(repo_path)
                    if git_handler.is_valid_repo():
                        status = git_handler.check_status()

                        has_changes = (status.get('is_dirty') or
                                     status.get('untracked_files') or
                                     status.get('staged_files'))

                        if has_changes:
                            click.echo(f"📝 检测到 {repo_name} 有变更")

                            # 询问是否自动提交
                            if click.confirm(f"是否自动提交 {repo_name}?"):
                                # 自动提交
                                if git_handler.add_files():
                                    message = f"自动提交 - {len(status.get('modified_files', []) + status.get('untracked_files', []))} 个文件变更"
                                    if git_handler.create_commit(message):
                                        click.echo(f"✅ {repo_name} 自动提交成功")
                                    else:
                                        click.echo(f"❌ {repo_name} 提交失败")

                time.sleep(interval)

        except KeyboardInterrupt:
            click.echo("\n👋 监控已停止")

    except Exception as e:
        logger.error(f"监控失败: {e}")
        click.echo(f"❌ 监控失败: {e}", err=True)


@cli.group()
@click.pass_context
def config(ctx):
    """配置管理命令"""
    pass


@config.command()
@click.option('--key', help='配置项键名')
@click.pass_context
def get(ctx, key):
    """获取配置项"""
    try:
        config_manager = ctx.parent.obj['config_manager']
        config = config_manager.load_config(force_reload=False)

        if key:
            # 获取指定配置项
            keys = key.split('.')
            value = config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    click.echo(f"❌ 配置项 '{key}' 不存在", err=True)
                    return

            click.echo(f"{key}: {value}")
        else:
            # 显示所有配置
            import yaml
            click.echo("📋 当前配置:")
            click.echo(yaml.dump(config, default_flow_style=False, allow_unicode=True))

    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        click.echo(f"❌ 获取配置失败: {e}", err=True)


@config.command()
@click.option('--key', required=True, help='配置项键名')
@click.option('--value', required=True, help='配置项值')
@click.pass_context
def set(ctx, key, value):
    """设置配置项"""
    try:
        config_manager = ctx.parent.obj['config_manager']
        config = config_manager.load_config(force_reload=True)

        # 解析键路径
        keys = key.split('.')
        target = config

        # 导航到目标位置
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        # 尝试转换值类型
        try:
            if value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif '.' in value and value.replace('.', '').isdigit():
                value = float(value)
        except:
            pass

        # 设置值
        target[keys[-1]] = value

        if config_manager.save_config(config):
            click.echo(f"✅ 配置项 '{key}' 已设置为: {value}")
        else:
            click.echo(f"❌ 保存配置失败", err=True)

    except Exception as e:
        logger.error(f"设置配置失败: {e}")
        click.echo(f"❌ 设置配置失败: {e}", err=True)


@config.command()
@click.pass_context
def reset(ctx):
    """重置为默认配置"""
    try:
        config_manager = ctx.parent.obj['config_manager']

        if click.confirm("确定要重置所有配置为默认值吗？"):
            if config_manager.reset_to_default():
                click.echo("✅ 配置已重置为默认值")
            else:
                click.echo("❌ 重置配置失败", err=True)

    except Exception as e:
        logger.error(f"重置配置失败: {e}")
        click.echo(f"❌ 重置配置失败: {e}", err=True)


@config.command()
@click.option('--file', required=True, help='导出文件路径')
@click.pass_context
def export(ctx, file):
    """导出配置到文件"""
    try:
        config_manager = ctx.parent.obj['config_manager']

        if config_manager.export_config(file):
            click.echo(f"✅ 配置已导出到: {file}")
        else:
            click.echo(f"❌ 导出配置失败", err=True)

    except Exception as e:
        logger.error(f"导出配置失败: {e}")
        click.echo(f"❌ 导出配置失败: {e}", err=True)


@config.command()
@click.option('--file', required=True, help='导入文件路径')
@click.pass_context
def import_config(ctx, file):
    """从文件导入配置"""
    try:
        config_manager = ctx.parent.obj['config_manager']

        if not Path(file).exists():
            click.echo(f"❌ 文件不存在: {file}", err=True)
            return

        if click.confirm(f"确定要从 {file} 导入配置吗？这将覆盖当前配置。"):
            if config_manager.import_config(file):
                click.echo(f"✅ 配置已从 {file} 导入")
            else:
                click.echo(f"❌ 导入配置失败", err=True)

    except Exception as e:
        logger.error(f"导入配置失败: {e}")
        click.echo(f"❌ 导入配置失败: {e}", err=True)


@cli.command()
def gui():
    """启动图形界面"""
    try:
        click.echo("🚀 启动图形界面...")

        # 导入GUI模块
        try:
            from src.gui.main_window import main as gui_main

            click.echo("✅ 图形界面已启动")
            sys.exit(gui_main())

        except ImportError as e:
            click.echo("❌ GUI依赖未安装，请运行: pip install PyQt5", err=True)
            click.echo("或者直接运行: python gui_main.py", err=True)
            click.echo("或使用命令行界面进行操作", err=True)

    except Exception as e:
        logger.error(f"启动GUI失败: {e}")
        click.echo(f"❌ 启动GUI失败: {e}", err=True)


if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n👋 程序已退出")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        click.echo(f"❌ 程序异常退出: {e}", err=True)
        sys.exit(1)
