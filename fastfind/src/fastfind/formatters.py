# -*- coding: utf-8 -*-

"""输出格式化模块"""

import json
import csv
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import textwrap
from enum import Enum


class OutputFormat(Enum):
    """输出格式枚举"""

    TEXT = "text"
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    HTML = "html"
    MARKDOWN = "markdown"


class BaseFormatter:
    """格式化器基类"""

    def __init__(
        self, show_header: bool = True, max_width: int = 80, color_output: bool = False
    ):
        self.show_header = show_header
        self.max_width = max_width
        self.color_output = color_output

    def format(self, data: List[Dict[str, Any]]) -> str:
        """格式化数据"""
        raise NotImplementedError

    def format_single(self, item: Dict[str, Any]) -> str:
        """格式化单个项目"""
        return self.format([item])


class TextFormatter(BaseFormatter):
    """文本格式化器"""

    def __init__(
        self,
        show_size: bool = True,
        show_time: bool = True,
        show_path: bool = True,
        truncate_path: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.show_size = show_size
        self.show_time = show_time
        self.show_path = show_path
        self.truncate_path = truncate_path

    def format(self, data: List[Dict[str, Any]]) -> str:
        """格式化为文本"""
        if not data:
            return "未找到文件"

        lines = []

        # 表头
        if self.show_header:
            header_parts = []
            if self.show_path:
                header_parts.append("路径")
            if self.show_size:
                header_parts.append("大小")
            if self.show_time:
                header_parts.append("修改时间")

            header = " | ".join(header_parts)
            lines.append(header)
            lines.append("-" * len(header))

        # 数据行
        for item in data:
            parts = []

            if self.show_path:
                path = item.get("path", "")
                if self.truncate_path and len(path) > 40:
                    path = "..." + path[-37:]
                parts.append(path)

            if self.show_size:
                size = item.get("size", 0)
                parts.append(self._format_size(size))

            if self.show_time:
                mtime = item.get("mtime", 0)
                parts.append(self._format_time(mtime))

            lines.append(" | ".join(parts))

        return "\n".join(lines)

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f}K"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.1f}M"
        else:
            return f"{size_bytes/(1024*1024*1024):.1f}G"

    def _format_time(self, timestamp: float) -> str:
        """格式化时间"""
        if timestamp <= 0:
            return "未知"

        dt = datetime.fromtimestamp(timestamp)
        now = datetime.now()

        delta = now - dt

        if delta.days == 0:
            if delta.seconds < 60:
                return "刚刚"
            elif delta.seconds < 3600:
                return f"{delta.seconds // 60}分钟前"
            else:
                return f"{delta.seconds // 3600}小时前"
        elif delta.days == 1:
            return "昨天"
        elif delta.days < 7:
            return f"{delta.days}天前"
        else:
            return dt.strftime("%Y-%m-%d")


class JSONFormatter(BaseFormatter):
    """JSON格式化器"""

    def __init__(self, indent: int = 2, sort_keys: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.indent = indent
        self.sort_keys = sort_keys

    def format(self, data: List[Dict[str, Any]]) -> str:
        """格式化为JSON"""
        return json.dumps(
            data,
            indent=self.indent,
            sort_keys=self.sort_keys,
            ensure_ascii=False,
            default=self._json_default,
        )

    def _json_default(self, obj):
        """JSON序列化默认处理器"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)


class CSVFormatter(BaseFormatter):
    """CSV格式化器"""

    def __init__(self, delimiter: str = ",", **kwargs):
        super().__init__(**kwargs)
        self.delimiter = delimiter

    def format(self, data: List[Dict[str, Any]]) -> str:
        """格式化为CSV"""
        if not data:
            return ""

        import io

        output = io.StringIO()

        # 获取所有字段
        fieldnames = set()
        for item in data:
            fieldnames.update(item.keys())
        fieldnames = sorted(fieldnames)

        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=self.delimiter)

        if self.show_header:
            writer.writeheader()

        for item in data:
            writer.writerow(item)

        return output.getvalue()


class HTMLFormatter(BaseFormatter):
    """HTML格式化器"""

    def format(self, data: List[Dict[str, Any]]) -> str:
        """格式化为HTML"""
        html = ["<!DOCTYPE html>", "<html>", "<head>"]
        html.append('<meta charset="UTF-8">')
        html.append("<title>fastfind 搜索结果</title>")
        html.append("<style>")
        html.append("""
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            .count { margin-bottom: 20px; color: #666; }
        """)
        html.append("</style>")
        html.append("</head>")
        html.append("<body>")

        html.append(f"<h1>fastfind 搜索结果</h1>")
        html.append(f'<div class="count">找到 {len(data)} 个文件</div>')

        if data:
            html.append("<table>")
            # 表头
            html.append("<tr>")
            for key in data[0].keys():
                html.append(f"<th>{key}</th>")
            html.append("</tr>")

            # 数据行
            for item in data:
                html.append("<tr>")
                for value in item.values():
                    html.append(f"<td>{value}</td>")
                html.append("</tr>")

            html.append("</table>")

        html.append("</body>")
        html.append("</html>")

        return "\n".join(html)


class XMLFormatter(BaseFormatter):
    """XML格式化器"""

    def format(self, data: List[Dict[str, Any]]) -> str:
        """格式化为XML"""
        xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml.append('<results count="{}">'.format(len(data)))

        for item in data:
            xml.append("  <item>")
            for key, value in item.items():
                if isinstance(value, (list, dict)):
                    value = str(value)
                xml.append("    <{}><![CDATA[{}]]></{}>".format(key, value, key))
            xml.append("  </item>")

        xml.append("</results>")
        return "\n".join(xml)


class MarkdownFormatter(BaseFormatter):
    """Markdown格式化器"""

    def format(self, data: List[Dict[str, Any]]) -> str:
        """格式化为Markdown"""
        if not data:
            return "未找到文件"

        md = [f"# fastfind 搜索结果\n", f"找到 **{len(data)}** 个文件\n"]

        if data:
            md.append("\n## 文件列表\n")

            # 表格头
            headers = list(data[0].keys())
            md.append("| " + " | ".join(headers) + " |")
            md.append("|" + "|".join(["---"] * len(headers)) + "|")

            # 表格数据
            for item in data:
                row = []
                for header in headers:
                    value = item.get(header, "")
                    if isinstance(value, (list, dict)):
                        value = str(value)
                    row.append(str(value))
                md.append("| " + " | ".join(row) + " |")

        return "\n".join(md)


class FormatterFactory:
    """格式化器工厂"""

    @staticmethod
    def create_formatter(format_type: str, **kwargs) -> BaseFormatter:
        """
        创建格式化器

        Args:
            format_type: 格式类型（text, json, csv, xml, html, markdown）
            **kwargs: 格式化器参数

        Returns:
            格式化器实例
        """
        format_type = format_type.lower()

        if format_type == OutputFormat.TEXT.value:
            return TextFormatter(**kwargs)
        elif format_type == OutputFormat.JSON.value:
            return JSONFormatter(**kwargs)
        elif format_type == OutputFormat.CSV.value:
            return CSVFormatter(**kwargs)
        elif format_type == OutputFormat.XML.value:
            return XMLFormatter(**kwargs)
        elif format_type == OutputFormat.HTML.value:
            return HTMLFormatter(**kwargs)
        elif format_type == OutputFormat.MARKDOWN.value:
            return MarkdownFormatter(**kwargs)
        else:
            raise ValueError(f"不支持的格式类型: {format_type}")

    @staticmethod
    def get_supported_formats() -> List[str]:
        """获取支持的格式列表"""
        return [fmt.value for fmt in OutputFormat]


# 便捷函数
def format_results(
    data: List[Dict[str, Any]], format_type: str = "text", **kwargs
) -> str:
    """
    格式化结果

    Args:
        data: 数据列表
        format_type: 格式类型
        **kwargs: 格式化器参数

    Returns:
        格式化后的字符串
    """
    formatter = FormatterFactory.create_formatter(format_type, **kwargs)
    return formatter.format(data)


def save_results(
    data: List[Dict[str, Any]], filepath: str, format_type: str = "text", **kwargs
):
    """
    保存结果到文件

    Args:
        data: 数据列表
        filepath: 文件路径
        format_type: 格式类型
        **kwargs: 格式化器参数
    """
    formatted = format_results(data, format_type, **kwargs)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(formatted)


# 测试函数
def test_formatters():
    """测试格式化器"""
    test_data = [
        {
            "path": "/home/user/test.txt",
            "size": 1024,
            "mtime": 1672531200,
            "is_dir": False,
        },
        {"path": "/home/user/docs", "size": 2048, "mtime": 1672617600, "is_dir": True},
    ]

    # 测试文本格式
    text_formatter = TextFormatter()
    text_output = text_formatter.format(test_data)
    assert "test.txt" in text_output
    print("✅ 文本格式化器测试通过")

    # 测试JSON格式
    json_formatter = JSONFormatter()
    json_output = json_formatter.format(test_data)
    assert '"path"' in json_output
    print("✅ JSON格式化器测试通过")

    # 测试CSV格式
    csv_formatter = CSVFormatter()
    csv_output = csv_formatter.format(test_data)
    assert "," in csv_output
    print("✅ CSV格式化器测试通过")

    # 测试工厂
    formatter = FormatterFactory.create_formatter("text")
    assert isinstance(formatter, TextFormatter)
    print("✅ 格式化器工厂测试通过")


if __name__ == "__main__":
    test_formatters()

