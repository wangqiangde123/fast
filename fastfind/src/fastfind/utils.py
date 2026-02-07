# -*- coding: utf-8 -*-

"""
工具函数模块
提供各种实用函数
"""

import os
import sys
import hashlib
import time
import math
import json
import shutil
import tarfile
import zipfile
import gzip
import bz2
import lzma
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any, BinaryIO
from datetime import datetime, timedelta
import mimetypes
import chardet
import fnmatch
import csv
import pickle
import base64
import uuid
import inspect
import textwrap
import itertools
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
import queue

# ========== 文件操作工具 ==========


def get_file_hash(filepath: str, algorithm: str = "md5", chunk_size: int = 8192) -> str:
    """计算文件哈希值"""
    hash_func = getattr(hashlib, algorithm)()

    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception:
        return ""


def get_file_info(filepath: str) -> Dict[str, Any]:
    """获取文件的详细信息"""
    path = Path(filepath)

    try:
        stat_info = path.stat()

        # 检测文件编码
        encoding = "utf-8"
        try:
            with open(filepath, "rb") as f:
                raw_data = f.read(1024)
                result = chardet.detect(raw_data)
                if result["confidence"] > 0.7:
                    encoding = result["encoding"]
        except:
            pass

        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(filepath)

        info = {
            "path": str(path.absolute()),
            "name": path.name,
            "stem": path.stem,
            "suffix": path.suffix,
            "parent": str(path.parent),
            "size": stat_info.st_size,
            "size_human": human_readable_size(stat_info.st_size),
            "created": stat_info.st_ctime,
            "created_iso": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
            "modified": stat_info.st_mtime,
            "modified_iso": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            "accessed": stat_info.st_atime,
            "accessed_iso": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
            "is_dir": path.is_dir(),
            "is_file": path.is_file(),
            "is_symlink": path.is_symlink(),
            "exists": path.exists(),
            "permissions": oct(stat_info.st_mode)[-3:],
            "inode": stat_info.st_ino,
            "device": stat_info.st_dev,
            "encoding": encoding,
            "mime_type": mime_type or "application/octet-stream",
            "hash_md5": get_file_hash(filepath, "md5"),
            "hash_sha1": get_file_hash(filepath, "sha1"),
            "hash_sha256": get_file_hash(filepath, "sha256"),
        }

        # 如果是文本文件，尝试读取前几行
        if path.is_file() and stat_info.st_size > 0 and stat_info.st_size < 1024 * 1024:
            try:
                with open(filepath, "r", encoding=encoding, errors="ignore") as f:
                    preview = f.read(500)
                    info["preview"] = preview
                    info["line_count"] = len(preview.splitlines())
            except:
                info["preview"] = ""
                info["line_count"] = 0

        return info
    except Exception as e:
        return {"path": str(path), "name": path.name, "exists": False, "error": str(e)}


def compare_files(file1: str, file2: str) -> Dict[str, Any]:
    """比较两个文件"""
    info1 = get_file_info(file1)
    info2 = get_file_info(file2)

    comparison = {
        "file1": info1,
        "file2": info2,
        "size_equal": info1.get("size", 0) == info2.get("size", 0),
        "modified_equal": info1.get("modified", 0) == info2.get("modified", 0),
        "hash_equal": info1.get("hash_md5") == info2.get("hash_md5"),
        "identical": False,
    }

    if comparison["hash_equal"]:
        comparison["identical"] = True
    elif info1.get("size") == info2.get("size"):
        # 大小相同但哈希不同，可能是内容不同
        try:
            with open(file1, "rb") as f1, open(file2, "rb") as f2:
                chunk1 = f1.read(8192)
                chunk2 = f2.read(8192)
                comparison["first_chunk_equal"] = chunk1 == chunk2
        except:
            comparison["first_chunk_equal"] = False

    return comparison


def find_duplicate_files(directory: str, algorithm: str = "md5") -> List[List[str]]:
    """查找目录中的重复文件"""
    file_hashes = defaultdict(list)

    for root, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            file_hash = get_file_hash(filepath, algorithm)
            if file_hash:
                file_hashes[file_hash].append(filepath)

    # 返回有重复的文件组
    return [paths for paths in file_hashes.values() if len(paths) > 1]


# ========== 文本处理工具 ==========


def count_file_stats(filepath: str) -> Dict[str, int]:
    """统计文件的字数、行数等"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        lines = content.splitlines()
        words = content.split()

        return {
            "chars": len(content),
            "lines": len(lines),
            "words": len(words),
            "non_empty_lines": len([l for l in lines if l.strip()]),
            "bytes": os.path.getsize(filepath),
        }
    except Exception:
        return {"chars": 0, "lines": 0, "words": 0, "non_empty_lines": 0, "bytes": 0}


def detect_indentation(content: str) -> Dict[str, Any]:
    """检测代码的缩进风格"""
    lines = content.splitlines()

    # 统计缩进
    space_indents = 0
    tab_indents = 0
    mixed_indents = 0
    indent_sizes = []

    for line in lines:
        if line.startswith(" ") or line.startswith("\t"):
            leading = line[: len(line) - len(line.lstrip())]

            if " " in leading and "\t" in leading:
                mixed_indents += 1
            elif leading.startswith(" "):
                space_indents += 1
                # 计算空格数
                spaces = len(leading) - len(leading.replace(" ", ""))
                if spaces > 0:
                    indent_sizes.append(spaces)
            elif leading.startswith("\t"):
                tab_indents += 1

    # 分析缩进大小
    if indent_sizes:
        size_counter = Counter(indent_sizes)
        most_common_size, most_common_count = size_counter.most_common(1)[0]
    else:
        most_common_size = 4
        most_common_count = 0

    return {
        "total_lines": len(lines),
        "indented_lines": space_indents + tab_indents + mixed_indents,
        "space_indents": space_indents,
        "tab_indents": tab_indents,
        "mixed_indents": mixed_indents,
        "most_common_indent": most_common_size,
        "most_common_count": most_common_count,
        "likely_indent": (
            most_common_size if most_common_count > len(indent_sizes) * 0.5 else 4
        ),
        "has_mixed": mixed_indents > 0,
    }


def extract_imports(filepath: str) -> Dict[str, List[str]]:
    """提取Python文件的导入语句"""
    imports = {"import": [], "from_import": [], "try_import": []}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()

            # 简单匹配导入语句
            if line.startswith("import "):
                imports["import"].append(line[7:].strip())
            elif line.startswith("from "):
                imports["from_import"].append(line[5:].strip())
            elif "try:" in line.lower() and "import" in line:
                imports["try_import"].append(line.strip())

    except Exception:
        pass

    return imports


# ========== 压缩和归档工具 ==========


def compress_file(
    input_file: str, output_file: Optional[str] = None, method: str = "gzip"
) -> str:
    """压缩文件"""
    if output_file is None:
        if method == "gzip":
            output_file = input_file + ".gz"
        elif method == "bz2":
            output_file = input_file + ".bz2"
        elif method == "xz":
            output_file = input_file + ".xz"
        else:
            output_file = input_file + ".zip"

    input_path = Path(input_file)

    try:
        if method == "gzip":
            with open(input_file, "rb") as f_in:
                with gzip.open(output_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

        elif method == "bz2":
            with open(input_file, "rb") as f_in:
                with bz2.open(output_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

        elif method == "xz":
            with open(input_file, "rb") as f_in:
                with lzma.open(output_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

        elif method == "zip":
            with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(input_file, input_path.name)

        else:
            raise ValueError(f"不支持的压缩方法: {method}")

        # 计算压缩率
        original_size = input_path.stat().st_size
        compressed_size = Path(output_file).stat().st_size
        compression_ratio = compressed_size / original_size if original_size > 0 else 0

        return {
            "success": True,
            "output_file": output_file,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": compression_ratio,
            "saved_bytes": original_size - compressed_size,
        }

    except Exception as e:
        return {"success": False, "error": str(e), "output_file": output_file}


def create_archive(
    source_dir: str, output_file: str, format: str = "zip"
) -> Dict[str, Any]:
    """创建归档文件"""
    source_path = Path(source_dir)

    try:
        if format == "zip":
            with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in source_path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(source_path)
                        zipf.write(file_path, arcname)

        elif format == "tar":
            with tarfile.open(output_file, "w") as tarf:
                tarf.add(source_dir, arcname=source_path.name)

        elif format == "tar.gz":
            with tarfile.open(output_file, "w:gz") as tarf:
                tarf.add(source_dir, arcname=source_path.name)

        elif format == "tar.bz2":
            with tarfile.open(output_file, "w:bz2") as tarf:
                tarf.add(source_dir, arcname=source_path.name)

        else:
            raise ValueError(f"不支持的归档格式: {format}")

        # 统计信息
        file_count = sum(1 for _ in source_path.rglob("*") if _.is_file())
        archive_size = Path(output_file).stat().st_size

        return {
            "success": True,
            "output_file": output_file,
            "source_dir": source_dir,
            "file_count": file_count,
            "archive_size": archive_size,
            "format": format,
        }

    except Exception as e:
        return {"success": False, "error": str(e), "output_file": output_file}


# ========== 文件搜索工具 ==========


def search_in_files(
    directory: str,
    search_text: str,
    file_pattern: str = "*",
    case_sensitive: bool = False,
    max_size: int = 1024 * 1024,
) -> List[Dict[str, Any]]:
    """在文件中搜索文本"""
    results = []
    search_lower = search_text.lower() if not case_sensitive else search_text

    for root, dirs, files in os.walk(directory):
        for file in files:
            if not fnmatch.fnmatch(file, file_pattern):
                continue

            filepath = os.path.join(root, file)

            try:
                file_size = os.path.getsize(filepath)
                if file_size > max_size or file_size == 0:
                    continue

                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if not case_sensitive:
                    content_check = content.lower()
                else:
                    content_check = content

                if search_lower in content_check:
                    # 找到匹配，记录上下文
                    lines = content.splitlines()
                    matches = []

                    for i, line in enumerate(lines):
                        line_check = line.lower() if not case_sensitive else line
                        if search_lower in line_check:
                            # 高亮匹配部分
                            if case_sensitive:
                                highlighted = line.replace(
                                    search_text, f"**{search_text}**"
                                )
                            else:
                                # 不区分大小写的高亮
                                import re

                                pattern = re.compile(
                                    re.escape(search_text), re.IGNORECASE
                                )
                                highlighted = pattern.sub(
                                    lambda m: f"**{m.group()}**", line
                                )

                            matches.append(
                                {
                                    "line_number": i + 1,
                                    "line": line,
                                    "highlighted": highlighted,
                                    "context_before": lines[max(0, i - 2) : i],
                                    "context_after": lines[
                                        i + 1 : min(len(lines), i + 3)
                                    ],
                                }
                            )

                    results.append(
                        {
                            "file": filepath,
                            "matches": matches,
                            "match_count": len(matches),
                            "relative_path": os.path.relpath(filepath, directory),
                            "size": file_size,
                        }
                    )

            except Exception:
                continue

    # 按匹配数量排序
    results.sort(key=lambda x: x["match_count"], reverse=True)
    return results


# ========== 格式转换工具 ==========


def human_readable_size(size_bytes: int) -> str:
    """将字节数转换为易读的大小"""
    if size_bytes == 0:
        return "0B"

    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.2f} {units[i]}"


def format_duration(seconds: float) -> str:
    """格式化时间间隔"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f}µs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.2f}h"
    else:
        days = seconds / 86400
        return f"{days:.2f}d"


def format_timestamp(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间戳"""
    return datetime.fromtimestamp(timestamp).strftime(format_str)


def parse_human_size(size_str: str) -> int:
    """解析人类可读的大小字符串为字节数"""
    size_str = size_str.strip().upper()

    multipliers = {
        "B": 1,
        "K": 1024,
        "KB": 1024,
        "M": 1024**2,
        "MB": 1024**2,
        "G": 1024**3,
        "GB": 1024**3,
        "T": 1024**4,
        "TB": 1024**4,
        "P": 1024**5,
        "PB": 1024**5,
    }

    # 提取数字和单位
    import re

    match = re.match(r"([\d.]+)\s*([A-Z]*)", size_str)

    if match:
        number = float(match.group(1))
        unit = match.group(2)

        if unit in multipliers:
            return int(number * multipliers[unit])
        else:
            # 如果没有单位，假设是字节
            return int(number)

    raise ValueError(f"无法解析大小字符串: {size_str}")


# ========== 并发工具 ==========


class ParallelProcessor:
    """并行处理器"""

    def __init__(self, max_workers: int = None, use_threads: bool = True):
        self.max_workers = max_workers or os.cpu_count() or 4
        self.use_threads = use_threads

        if use_threads:
            self.executor_class = ThreadPoolExecutor
        else:
            self.executor_class = ProcessPoolExecutor

    def process_files(
        self, file_list: List[str], process_func: Callable, chunk_size: int = 10
    ) -> List[Any]:
        """并行处理文件列表"""
        results = []

        with self.executor_class(max_workers=self.max_workers) as executor:
            # 分块处理，避免内存问题
            chunks = [
                file_list[i : i + chunk_size]
                for i in range(0, len(file_list), chunk_size)
            ]

            futures = []
            for chunk in chunks:
                future = executor.submit(self._process_chunk, chunk, process_func)
                futures.append(future)

            for future in futures:
                try:
                    chunk_results = future.result(timeout=300)  # 5分钟超时
                    results.extend(chunk_results)
                except Exception as e:
                    print(f"处理块时出错: {e}")

        return results

    def _process_chunk(self, chunk: List[str], process_func: Callable) -> List[Any]:
        """处理一个文件块"""
        return [process_func(file) for file in chunk]


# ========== 其他工具函数 ==========


def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    import platform

    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "cpu_count": os.cpu_count(),
        "total_memory": None,  # 需要psutil
        "disk_usage": None,  # 需要psutil
        "current_user": os.getlogin() if hasattr(os, "getlogin") else "",
        "home_dir": str(Path.home()),
        "current_dir": os.getcwd(),
        "temp_dir": (
            os.path.join(os.path.sep, "tmp")
            if os.name == "posix"
            else os.getenv("TEMP", "")
        ),
        "path_sep": os.path.sep,
        "line_sep": os.linesep,
    }


def generate_file_tree(
    directory: str,
    max_depth: int = 3,
    include_files: bool = True,
    include_hidden: bool = False,
) -> Dict[str, Any]:
    """生成目录树结构"""
    root_path = Path(directory)

    def build_tree(path: Path, depth: int = 0) -> Dict:
        if depth > max_depth:
            return {"name": path.name, "type": "directory", "truncated": True}

        tree = {
            "name": path.name,
            "path": str(path),
            "type": "directory" if path.is_dir() else "file",
        }

        if path.is_dir():
            children = []
            try:
                for child in path.iterdir():
                    if not include_hidden and child.name.startswith("."):
                        continue

                    if child.is_dir():
                        children.append(build_tree(child, depth + 1))
                    elif include_files:
                        children.append(
                            {
                                "name": child.name,
                                "path": str(child),
                                "type": "file",
                                "size": child.stat().st_size if child.exists() else 0,
                            }
                        )

                tree["children"] = children
                tree["child_count"] = len(children)
            except PermissionError:
                tree["permission_error"] = True

        elif path.is_file():
            try:
                stat_info = path.stat()
                tree.update(
                    {
                        "size": stat_info.st_size,
                        "modified": stat_info.st_mtime,
                        "created": stat_info.st_ctime,
                    }
                )
            except:
                pass

        return tree

    return build_tree(root_path)


def validate_path(
    path: str,
    check_exists: bool = True,
    check_readable: bool = False,
    check_writable: bool = False,
) -> Dict[str, Any]:
    """验证路径的有效性"""
    path_obj = Path(path)

    result = {
        "path": str(path),
        "exists": path_obj.exists(),
        "is_file": path_obj.is_file() if path_obj.exists() else False,
        "is_dir": path_obj.is_dir() if path_obj.exists() else False,
        "is_symlink": path_obj.is_symlink() if path_obj.exists() else False,
        "is_absolute": path_obj.is_absolute(),
        "absolute_path": str(path_obj.absolute()) if path_obj.exists() else None,
    }

    if check_exists and not result["exists"]:
        result["error"] = "路径不存在"
        return result

    if check_readable and result["exists"]:
        result["readable"] = os.access(str(path_obj), os.R_OK)
        if not result["readable"]:
            result["error"] = "路径不可读"

    if check_writable and result["exists"]:
        result["writable"] = os.access(str(path_obj), os.W_OK)
        if not result["writable"]:
            result["error"] = "路径不可写"

    if result["exists"]:
        try:
            stat_info = path_obj.stat()
            result.update(
                {
                    "size": stat_info.st_size,
                    "modified": stat_info.st_mtime,
                    "created": stat_info.st_ctime,
                    "permissions": oct(stat_info.st_mode)[-3:],
                }
            )
        except Exception as e:
            result["stat_error"] = str(e)

    return result


# ========== 主函数测试 ==========

if __name__ == "__main__":
    # 测试各种工具函数
    print("测试工具函数模块...")

    # 测试文件信息获取
    test_file = __file__
    info = get_file_info(test_file)
    print(f"\n文件信息测试 ({test_file}):")
    print(f"  大小: {info['size_human']}")
    print(f"  修改时间: {info['modified_iso']}")
    print(f"  MD5哈希: {info['hash_md5'][:16]}...")

    # 测试大小格式化
    print("\n大小格式化测试:")
    test_sizes = [
        0,
        1023,
        1024,
        1024 * 1024,
        1024 * 1024 * 1024,
        1024 * 1024 * 1024 * 1024,
    ]
    for size in test_sizes:
        print(f"  {size} bytes = {human_readable_size(size)}")

    # 测试路径验证
    print("\n路径验证测试:")
    test_paths = [__file__, "/nonexistent/path", os.getcwd()]
    for path in test_paths:
        validation = validate_path(path, check_exists=False)
        print(f"  {path}:")
        print(f"    存在: {validation['exists']}")
        print(
            f"    类型: {'目录' if validation['is_dir'] else '文件' if validation['is_file'] else '未知'}"
        )

    print("\n工具函数测试完成!")

