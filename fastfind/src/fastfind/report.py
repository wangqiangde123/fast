# -*- coding: utf-8 -*-

"""
报表生成模块
生成各种统计报表
"""

import json
import csv
import yaml
import toml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import os
import textwrap
from dataclasses import dataclass, asdict
from enum import Enum
import statistics


class ReportFormat(Enum):
    """报表格式"""

    TEXT = "text"
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    MARKDOWN = "markdown"
    YAML = "yaml"
    TOML = "toml"


@dataclass
class FileStat:
    """文件统计信息"""

    path: str
    name: str
    size: int
    modified: float
    created: float
    accessed: float
    is_dir: bool
    is_file: bool

    @property
    def size_human(self) -> str:
        """人类可读的大小"""
        return self._human_readable_size(self.size)

    @property
    def modified_str(self) -> str:
        """格式化修改时间"""
        return datetime.fromtimestamp(self.modified).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _human_readable_size(size_bytes: int) -> str:
        """将字节数转换为易读的大小"""
        if size_bytes == 0:
            return "0B"

        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        i = 0
        size = float(size_bytes)

        while size >= 1024 and i < len(units) - 1:
            size /= 1024.0
            i += 1

        return f"{size:.2f} {units[i]}"


@dataclass
class DirectoryReport:
    """目录报告"""

    path: str
    scan_time: float
    total_files: int
    total_dirs: int
    total_size: int
    file_stats: List[FileStat]

    @property
    def total_size_human(self) -> str:
        """人类可读的总大小"""
        return FileStat._human_readable_size(self.total_size)

    @property
    def avg_file_size(self) -> float:
        """平均文件大小"""
        if self.total_files == 0:
            return 0
        return self.total_size / self.total_files

    @property
    def file_extensions(self) -> Dict[str, int]:
        """文件扩展名统计"""
        extensions = {}
        for stat in self.file_stats:
            if stat.is_file:
                ext = Path(stat.path).suffix.lower()
                if ext:
                    extensions[ext] = extensions.get(ext, 0) + 1
        return extensions

    @property
    def size_distribution(self) -> Dict[str, int]:
        """文件大小分布"""
        distribution = {
            "tiny": 0,  # < 1KB
            "small": 0,  # 1KB - 1MB
            "medium": 0,  # 1MB - 10MB
            "large": 0,  # 10MB - 100MB
            "huge": 0,  # > 100MB
        }

        for stat in self.file_stats:
            if stat.is_file:
                size_mb = stat.size / (1024 * 1024)
                if stat.size < 1024:
                    distribution["tiny"] += 1
                elif size_mb < 1:
                    distribution["small"] += 1
                elif size_mb < 10:
                    distribution["medium"] += 1
                elif size_mb < 100:
                    distribution["large"] += 1
                else:
                    distribution["huge"] += 1

        return distribution


class ReportGenerator:
    """报表生成器"""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.getcwd()
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def generate_text_report(
        self, report: DirectoryReport, detailed: bool = False
    ) -> str:
        """生成文本报表"""
        lines = []

        # 标题
        lines.append("=" * 60)
        lines.append(f"目录扫描报告: {report.path}")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")

        # 摘要
        lines.append("摘要:")
        lines.append(f"  扫描时间: {report.scan_time:.2f} 秒")
        lines.append(f"  文件总数: {report.total_files}")
        lines.append(f"  目录总数: {report.total_dirs}")
        lines.append(f"  总大小: {report.total_size_human}")
        lines.append(
            f"  平均文件大小: {FileStat._human_readable_size(report.avg_file_size)}"
        )
        lines.append("")

        # 扩展名统计
        lines.append("文件扩展名统计:")
        extensions = report.file_extensions
        if extensions:
            for ext, count in sorted(
                extensions.items(), key=lambda x: x[1], reverse=True
            )[:10]:
                percentage = (
                    (count / report.total_files * 100) if report.total_files > 0 else 0
                )
                lines.append(f"  {ext or '无扩展名'}: {count} 个 ({percentage:.1f}%)")
        else:
            lines.append("  无文件")
        lines.append("")

        # 大小分布
        lines.append("文件大小分布:")
        distribution = report.size_distribution
        for category, count in distribution.items():
            if count > 0:
                percentage = (
                    (count / report.total_files * 100) if report.total_files > 0 else 0
                )
                lines.append(f"  {category}: {count} 个 ({percentage:.1f}%)")
        lines.append("")

        # 详细文件列表（如果启用）
        if detailed and report.file_stats:
            lines.append("文件列表（前20个）:")
            lines.append("-" * 80)
            lines.append(f"{'文件名':<30} {'大小':>12} {'修改时间':>20}")
            lines.append("-" * 80)

            for stat in report.file_stats[:20]:
                if stat.is_file:
                    name = Path(stat.path).name
                    if len(name) > 28:
                        name = name[:25] + "..."
                    lines.append(
                        f"{name:<30} {stat.size_human:>12} {stat.modified_str:>20}"
                    )

        return "\n".join(lines)

    def generate_json_report(self, report: DirectoryReport) -> str:
        """生成JSON报表"""
        report_dict = {
            "metadata": {
                "path": report.path,
                "scan_time": report.scan_time,
                "generated_at": datetime.now().isoformat(),
                "report_version": "1.0",
            },
            "summary": {
                "total_files": report.total_files,
                "total_dirs": report.total_dirs,
                "total_size": report.total_size,
                "total_size_human": report.total_size_human,
                "avg_file_size": report.avg_file_size,
                "avg_file_size_human": FileStat._human_readable_size(
                    report.avg_file_size
                ),
            },
            "extensions": report.file_extensions,
            "size_distribution": report.size_distribution,
            "files": [asdict(stat) for stat in report.file_stats[:100]],  # 限制数量
        }

        return json.dumps(report_dict, indent=2, ensure_ascii=False, default=str)

    def generate_csv_report(self, report: DirectoryReport) -> str:
        """生成CSV报表"""
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入摘要
        writer.writerow(["项目", "值"])
        writer.writerow(["路径", report.path])
        writer.writerow(["扫描时间(秒)", f"{report.scan_time:.2f}"])
        writer.writerow(["文件总数", report.total_files])
        writer.writerow(["目录总数", report.total_dirs])
        writer.writerow(["总大小(字节)", report.total_size])
        writer.writerow(["总大小(可读)", report.total_size_human])
        writer.writerow([])

        # 写入扩展名统计
        writer.writerow(["文件扩展名统计"])
        writer.writerow(["扩展名", "数量", "百分比"])
        extensions = report.file_extensions
        for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
            percentage = (
                (count / report.total_files * 100) if report.total_files > 0 else 0
            )
            writer.writerow([ext or "无扩展名", count, f"{percentage:.1f}%"])
        writer.writerow([])

        # 写入文件列表
        writer.writerow(["文件列表"])
        writer.writerow(["路径", "名称", "大小(字节)", "大小(可读)", "修改时间"])
        for stat in report.file_stats[:50]:  # 限制数量
            if stat.is_file:
                writer.writerow(
                    [
                        stat.path,
                        stat.name,
                        stat.size,
                        stat.size_human,
                        stat.modified_str,
                    ]
                )

        return output.getvalue()

    def generate_html_report(self, report: DirectoryReport) -> str:
        """生成HTML报表"""
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>目录扫描报告 - {report.path}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .section {{ margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .stat-item {{ background: #f9f9f9; padding: 10px; border-radius: 3px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .chart {{ display: flex; height: 20px; margin: 10px 0; }}
        .chart-item {{ display: flex; align-items: center; justify-content: center; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📁 目录扫描报告</h1>
        <p><strong>路径:</strong> {report.path}</p>
        <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="section">
        <h2>📊 摘要</h2>
        <div class="stats">
            <div class="stat-item">
                <strong>文件总数:</strong><br>
                <span style="font-size: 24px;">{report.total_files}</span>
            </div>
            <div class="stat-item">
                <strong>目录总数:</strong><br>
                <span style="font-size: 24px;">{report.total_dirs}</span>
            </div>
            <div class="stat-item">
                <strong>总大小:</strong><br>
                <span style="font-size: 24px;">{report.total_size_human}</span>
            </div>
            <div class="stat-item">
                <strong>扫描时间:</strong><br>
                <span style="font-size: 24px;">{report.scan_time:.2f} 秒</span>
            </div>
        </div>
    </div>
"""

        # 添加扩展名统计
        extensions = report.file_extensions
        if extensions:
            html += """
    <div class="section">
        <h2>📄 文件扩展名统计</h2>
        <table>
            <tr>
                <th>扩展名</th>
                <th>数量</th>
                <th>百分比</th>
            </tr>
"""

            for ext, count in sorted(
                extensions.items(), key=lambda x: x[1], reverse=True
            )[:15]:
                percentage = (
                    (count / report.total_files * 100) if report.total_files > 0 else 0
                )
                html += f"""
            <tr>
                <td>{ext or '无扩展名'}</td>
                <td>{count}</td>
                <td>{percentage:.1f}%</td>
            </tr>
"""

            html += """
        </table>
    </div>
"""

        html += """
</body>
</html>
"""

        return html

    def generate_markdown_report(self, report: DirectoryReport) -> str:
        """生成Markdown报表"""
        lines = []

        lines.append(f"# 目录扫描报告: {report.path}")
        lines.append(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        lines.append("## 摘要")
        lines.append("")
        lines.append(f"- **扫描时间:** {report.scan_time:.2f} 秒")
        lines.append(f"- **文件总数:** {report.total_files}")
        lines.append(f"- **目录总数:** {report.total_dirs}")
        lines.append(f"- **总大小:** {report.total_size_human}")
        lines.append(
            f"- **平均文件大小:** {FileStat._human_readable_size(report.avg_file_size)}"
        )
        lines.append("")

        # 扩展名统计
        lines.append("## 文件扩展名统计")
        lines.append("")
        lines.append("| 扩展名 | 数量 | 百分比 |")
        lines.append("|--------|------|--------|")

        extensions = report.file_extensions
        for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]:
            percentage = (
                (count / report.total_files * 100) if report.total_files > 0 else 0
            )
            lines.append(f"| {ext or '无扩展名'} | {count} | {percentage:.1f}% |")

        lines.append("")

        return "\n".join(lines)

    def save_report(
        self,
        report: DirectoryReport,
        format: ReportFormat,
        filename: Optional[str] = None,
    ) -> str:
        """保存报表到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fastfind_report_{timestamp}.{format.value}"

        output_path = Path(self.output_dir) / filename

        # 生成报表内容
        if format == ReportFormat.TEXT:
            content = self.generate_text_report(report, detailed=True)
            output_path.write_text(content, encoding="utf-8")

        elif format == ReportFormat.JSON:
            content = self.generate_json_report(report)
            output_path.write_text(content, encoding="utf-8")

        elif format == ReportFormat.CSV:
            content = self.generate_csv_report(report)
            output_path.write_text(content, encoding="utf-8")

        elif format == ReportFormat.HTML:
            content = self.generate_html_report(report)
            output_path.write_text(content, encoding="utf-8")

        elif format == ReportFormat.MARKDOWN:
            content = self.generate_markdown_report(report)
            output_path.write_text(content, encoding="utf-8")

        elif format == ReportFormat.YAML:
            import yaml

            report_dict = {
                "path": report.path,
                "scan_time": report.scan_time,
                "total_files": report.total_files,
                "total_dirs": report.total_dirs,
                "total_size": report.total_size,
                "extensions": report.file_extensions,
            }
            content = yaml.dump(
                report_dict, allow_unicode=True, default_flow_style=False
            )
            output_path.write_text(content, encoding="utf-8")

        elif format == ReportFormat.TOML:
            import toml

            report_dict = {
                "path": report.path,
                "scan_time": report.scan_time,
                "total_files": report.total_files,
                "total_dirs": report.total_dirs,
                "total_size": report.total_size,
                "extensions": report.file_extensions,
            }
            content = toml.dumps(report_dict)
            output_path.write_text(content, encoding="utf-8")

        return str(output_path)


def create_sample_report() -> DirectoryReport:
    """创建示例报表（用于测试）"""
    import time

    # 创建一些示例数据
    file_stats = []
    for i in range(10):
        file_stats.append(
            FileStat(
                path=f"/path/to/file_{i}.txt",
                name=f"file_{i}.txt",
                size=1024 * (i + 1),
                modified=time.time() - i * 3600,
                created=time.time() - i * 3600 * 24,
                accessed=time.time() - i * 3600 * 7,
                is_dir=False,
                is_file=True,
            )
        )

    return DirectoryReport(
        path="/path/to/directory",
        scan_time=1.23,
        total_files=10,
        total_dirs=3,
        total_size=sum(stat.size for stat in file_stats),
        file_stats=file_stats,
    )


if __name__ == "__main__":
    print("测试报表生成模块...")

    # 创建示例报表
    report = create_sample_report()
    generator = ReportGenerator()

    # 测试各种格式
    print("\n1. 文本报表:")
    print(generator.generate_text_report(report))

    print("\n2. JSON报表（前200字符）:")
    json_report = generator.generate_json_report(report)
    print(json_report[:200] + "...")

    print("\n3. CSV报表（前200字符）:")
    csv_report = generator.generate_csv_report(report)
    print(csv_report[:200] + "...")

    print("\n4. 保存测试报表...")
    saved_path = generator.save_report(report, ReportFormat.TEXT, "test_report.txt")
    print(f"已保存到: {saved_path}")

    print("\n✅ 报表生成模块测试完成!")

