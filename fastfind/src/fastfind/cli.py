# -*- coding: utf-8 -*-

import click
import os
from pathlib import Path
from typing import List


@click.group()
@click.version_option()
def cli():
    """fastfind - 现代化的文件查找工具"""
    pass


def simple_find(path: str, pattern: str = None) -> List[str]:
    """简单的文件查找函数"""
    results = []
    for root, dirs, files in os.walk(path):
        for file in files:
            filepath = os.path.join(root, file)
            if pattern:
                if pattern in file:
                    results.append(filepath)
            else:
                results.append(filepath)
    return results


@cli.command()
@click.argument("path", default=".")
@click.option("-n", "--name", help="文件名包含的字符串")
@click.option("-t", "--type", "file_type", help="文件扩展名，如 .py .txt")
def find(path, name, file_type) -> None:
    """查找文件"""
    click.echo(f"🔍 搜索路径: {path}")

    if not os.path.exists(path):
        click.echo(f"❌ 路径不存在: {path}", err=True)
        return

    results = []

    for root, dirs, files in os.walk(path):
        for file in files:
            filepath = os.path.join(root, file)

            # 过滤条件
            if name and name not in file:
                continue
            if file_type and not file.endswith(file_type):
                continue

            results.append(filepath)

    # 输出结果
    if results:
        click.echo(f"📁 找到 {len(results)} 个文件:")
        for result in results[:50]:  # 限制显示前50个
            click.echo(f"  {result}")
        if len(results) > 50:
            click.echo(f"  ... 还有 {len(results) - 50} 个文件未显示")
    else:
        click.echo("❌ 未找到匹配的文件")


@cli.command()
def stats():
    """显示项目统计信息"""
    import fastfind

    click.echo(f"📊 fastfind v{fastfind.__version__}")
    click.echo(f"📁 项目路径: {os.getcwd()}")

    # 统计代码行数
    python_files = []
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    click.echo(f"📝 Python文件数量: {len(python_files)}")


if __name__ == "__main__":
    cli()


@cli.command()
@click.argument("path")
@click.option("--detail", is_flag=True, help="显示详细信息")
@click.option("--human", is_flag=True, help="人性化显示文件大小")
def info(path, detail, human) -> None:
    """显示文件或目录信息"""
    from pathlib import Path
    import stat
    import time
    import math

    p = Path(path)
    if not p.exists():
        click.echo(f"❌ 路径不存在: {path}", err=True)
        return

    def format_size(size_bytes) -> None:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0B"
        if not human:
            return f"{size_bytes} B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    def format_time(timestamp) -> None:
        """格式化时间"""
        from datetime import datetime

        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    click.echo(f"📁 路径信息: {path}")
    click.echo(f"📊 类型: {'目录' if p.is_dir() else '文件'}")

    if p.is_file():
        click.echo(f"📏 大小: {format_size(p.stat().st_size)}")

    stat_info = p.stat()
    click.echo(f"📅 创建时间: {format_time(stat_info.st_ctime)}")
    click.echo(f"📅 修改时间: {format_time(stat_info.st_mtime)}")
    click.echo(f"📅 访问时间: {format_time(stat_info.st_atime)}")

    if detail:
        # 显示权限信息
        mode = stat_info.st_mode
        click.echo(f"🔒 权限: {oct(mode)[-3:]}")

        # 如果是目录，统计内容
        if p.is_dir():
            files = list(p.glob("*"))
            dirs = [f for f in files if f.is_dir()]
            files = [f for f in files if f.is_file()]
            click.echo(f"📂 包含: {len(dirs)} 个目录, {len(files)} 个文件")


@cli.command()
@click.argument("source")
@click.argument("dest")
@click.option("--move", is_flag=True, help="移动而不是复制")
@click.option("--dry-run", is_flag=True, help="模拟运行，不实际操作")
def batch(source, dest, move, dry_run) -> None:
    """批量处理查找到的文件"""
    import shutil
    from pathlib import Path

    dest_path = Path(dest)

    # 先查找文件
    click.echo(f"🔍 查找文件: {source}")
    from .scanner import scan_directory

    files = scan_directory(".", name_filter=source)

    if not files:
        click.echo("❌ 未找到匹配的文件")
        return

    click.echo(f"📁 找到 {len(files)} 个文件")

    if dry_run:
        click.echo("🧪 模拟运行（不会实际操作）:")

    success = 0
    failed = 0

    for file in files[:50]:  # 限制前50个文件
        src = Path(file)
        if dest_path.is_dir():
            dst = dest_path / src.name
        else:
            dst = dest_path

        try:
            if dry_run:
                action = "移动" if move else "复制"
                click.echo(f"  {action}: {src} -> {dst}")
            else:
                if move:
                    shutil.move(str(src), str(dst))
                else:
                    shutil.copy2(str(src), str(dst))
                success += 1
        except Exception as e:
            if not dry_run:
                click.echo(f"  ❌ 失败: {src} -> {dst} ({e})", err=True)
                failed += 1

    if not dry_run:
        click.echo(f"✅ 操作完成: 成功 {success}, 失败 {failed}")


@cli.command()
@click.argument("path", default=".")
@click.option("-n", "--name", help="文件名包含的字符串")
@click.option("-t", "--type", "file_type", help="文件扩展名")
@click.option(
    "--format",
    type=click.Choice(["json", "csv", "txt"]),
    default="txt",
    help="导出格式",
)
@click.option("--output", "-o", help="输出文件路径")
def export(path, name, file_type, format, output) -> None:
    """导出查找结果"""
    import json
    import csv
    from datetime import datetime
    from pathlib import Path

    # 查找文件
    from .scanner import scan_directory

    files = scan_directory(path, name, file_type)

    if not files:
        click.echo("❌ 未找到匹配的文件")
        return

    click.echo(f"📁 找到 {len(files)} 个文件，准备导出...")

    # 准备数据
    data = []
    for filepath in files:
        p = Path(filepath)
        try:
            stat = p.stat()
            data.append(
                {
                    "path": str(p),
                    "name": p.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "created": stat.st_ctime,
                    "is_dir": p.is_dir(),
                    "parent": str(p.parent),
                }
            )
        except:
            data.append(
                {
                    "path": str(p),
                    "name": p.name,
                    "size": 0,
                    "modified": 0,
                    "created": 0,
                    "is_dir": False,
                    "parent": str(p.parent),
                }
            )

    # 确定输出文件
    if output:
        output_path = Path(output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"fastfind_export_{timestamp}.{format}")

    # 导出
    if format == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        click.echo(f"✅ JSON已导出到: {output_path}")

    elif format == "csv":
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        click.echo(f"✅ CSV已导出到: {output_path}")

    elif format == "txt":
        with open(output_path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(f"{item['path']}\n")
        click.echo(f"✅ 文本列表已导出到: {output_path}")

    click.echo(f"📊 导出 {len(data)} 条记录")

