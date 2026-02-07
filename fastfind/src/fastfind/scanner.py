# -*- coding: utf-8 -*-

"""
fastfind 异步文件扫描器
提供高性能的异步文件扫描功能
"""

import asyncio
import aiofiles
import aiofiles.os
from pathlib import Path
from typing import List, Optional, Callable, AsyncGenerator, Dict, Any
import time
import os
import sys


class AsyncScanner:
    """异步文件扫描器"""

    def __init__(self, max_concurrent: int = 100, follow_symlinks: bool = False):
        """
        初始化异步扫描器

        Args:
            max_concurrent: 最大并发数
            follow_symlinks: 是否跟踪符号链接
        """
        self.max_concurrent = max_concurrent
        self.follow_symlinks = follow_symlinks
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._ignore_patterns = []
        self.stats = {
            "files_found": 0,
            "dirs_scanned": 0,
            "files_skipped": 0,
            "permission_errors": 0,
            "start_time": 0,
            "end_time": 0,
            "total_bytes": 0,
        }
        self._cache = {}

    def add_ignore_pattern(self, pattern: str):
        """添加忽略模式（glob格式）"""
        from fnmatch import fnmatch

        self._ignore_patterns.append(pattern)

    def should_ignore(self, path: Path) -> bool:
        """检查路径是否应该被忽略"""
        for pattern in self._ignore_patterns:
            if fnmatch(str(path), pattern):
                return True
        return False

    async def scan(
        self,
        root_path: str,
        name_filter: Optional[str] = None,
        ext_filter: Optional[str] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        callback: Optional[Callable] = None,
    ) -> List[str]:
        """
        异步扫描目录

        Args:
            root_path: 根目录路径
            name_filter: 文件名包含的字符串
            ext_filter: 文件扩展名
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            callback: 找到文件时的回调函数

        Returns:
            找到的文件路径列表
        """
        self.stats["start_time"] = time.time()
        results = []
        root = Path(root_path).resolve()

        # 自动添加常见忽略模式
        if not self._ignore_patterns:
            self._ignore_patterns = [
                "**/.git/**",
                "**/.svn/**",
                "**/.hg/**",
                "**/__pycache__/**",
                "**/*.pyc",
                "**/*.pyo",
                "**/*.pyd",
                "**/.DS_Store",
            ]

        async for filepath in self._scan_generator(root):
            # 检查是否应该忽略
            if self.should_ignore(filepath):
                self.stats["files_skipped"] += 1
                continue

            # 获取文件信息用于过滤
            try:
                stat_info = await aiofiles.os.stat(str(filepath))
                file_size = stat_info.st_size

                # 应用过滤器
                if name_filter and name_filter not in filepath.name:
                    continue
                if ext_filter and not filepath.name.endswith(ext_filter):
                    continue
                if min_size is not None and file_size < min_size:
                    continue
                if max_size is not None and file_size > max_size:
                    continue

                self.stats["total_bytes"] += file_size

            except (OSError, PermissionError) as e:
                self.stats["permission_errors"] += 1
                continue

            filepath_str = str(filepath)
            results.append(filepath_str)

            if callback:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(filepath_str)
                    else:
                        callback(filepath_str)
                except Exception:
                    pass

        self.stats["end_time"] = time.time()
        self.stats["files_found"] = len(results)
        return results

    async def _scan_generator(
        self, path: Path, depth: int = 0, max_depth: int = 100
    ) -> AsyncGenerator[Path, None]:
        """异步生成器，递归扫描目录"""
        if depth > max_depth:
            return

        try:
            async for entry in self._listdir(path):
                if entry.is_dir():
                    self.stats["dirs_scanned"] += 1
                    async for sub_entry in self._scan_generator(
                        entry, depth + 1, max_depth
                    ):
                        yield sub_entry
                else:
                    yield entry
        except (PermissionError, OSError) as e:
            self.stats["permission_errors"] += 1
        except Exception as e:
            # 忽略其他异常，继续扫描
            pass

    async def _listdir(self, path: Path):
        """异步列出目录内容"""
        async with self.semaphore:
            try:
                items = await aiofiles.os.listdir(str(path))
                for item in items:
                    full_path = path / item

                    # 检查符号链接
                    if full_path.is_symlink():
                        if not self.follow_symlinks:
                            continue
                        try:
                            # 解析符号链接
                            target = full_path.resolve()
                            if target.is_dir():
                                self.stats["dirs_scanned"] += 1
                                async for sub_entry in self._scan_generator(target):
                                    yield sub_entry
                            else:
                                yield full_path
                        except Exception:
                            yield full_path
                    else:
                        yield full_path
            except Exception:
                return

    async def scan_with_metadata(
        self, root_path: str, **filters
    ) -> List[Dict[str, Any]]:
        """
        扫描目录并返回带元数据的文件信息

        Returns:
            包含文件信息的字典列表
        """
        files = await self.scan(root_path, **filters)
        results = []

        for filepath in files:
            try:
                stat_info = await aiofiles.os.stat(filepath)
                file_info = {
                    "path": filepath,
                    "name": Path(filepath).name,
                    "size": stat_info.st_size,
                    "modified": stat_info.st_mtime,
                    "created": stat_info.st_ctime,
                    "accessed": stat_info.st_atime,
                    "is_dir": False,
                    "is_file": True,
                    "permissions": stat_info.st_mode,
                    "inode": stat_info.st_ino,
                    "device": stat_info.st_dev,
                }
                results.append(file_info)
            except Exception:
                # 添加基本信息，即使无法获取完整元数据
                results.append(
                    {
                        "path": filepath,
                        "name": Path(filepath).name,
                        "size": 0,
                        "modified": 0,
                        "created": 0,
                        "accessed": 0,
                        "is_dir": False,
                        "is_file": True,
                        "permissions": 0,
                        "inode": 0,
                        "device": 0,
                    }
                )

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取扫描统计信息"""
        if self.stats["end_time"] > 0:
            elapsed = self.stats["end_time"] - self.stats["start_time"]
            self.stats["elapsed_time"] = elapsed
            if elapsed > 0:
                self.stats["files_per_second"] = self.stats["files_found"] / elapsed
                self.stats["bytes_per_second"] = self.stats["total_bytes"] / elapsed

        # 添加性能指标
        self.stats["avg_file_size"] = (
            self.stats["total_bytes"] / self.stats["files_found"]
            if self.stats["files_found"] > 0
            else 0
        )

        return self.stats.copy()


class FastScanner(AsyncScanner):
    """快速扫描器，针对常见场景优化"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._file_cache = {}
        self._cache_ttl = 300  # 5分钟缓存

    async def scan(self, *args, **kwargs) -> List[str]:
        """重写扫描方法，添加缓存支持"""
        root_path = args[0] if args else kwargs.get("root_path", ".")

        # 检查缓存
        cache_key = self._get_cache_key(root_path, kwargs)
        if cache_key in self._file_cache:
            cached_data = self._file_cache[cache_key]
            if time.time() - cached_data["timestamp"] < self._cache_ttl:
                self.stats["from_cache"] = True
                return cached_data["files"]

        # 执行扫描
        files = await super().scan(*args, **kwargs)

        # 更新缓存
        self._file_cache[cache_key] = {
            "files": files,
            "timestamp": time.time(),
            "count": len(files),
        }

        # 清理旧缓存
        self._clean_cache()

        return files

    def _get_cache_key(self, root_path: str, filters: dict) -> str:
        """生成缓存键"""
        import hashlib

        key_data = {
            "path": root_path,
            "filters": filters,
            "ignore_patterns": self._ignore_patterns,
        }
        import json

        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _clean_cache(self) -> None:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key
            for key, data in self._file_cache.items()
            if current_time - data["timestamp"] > self._cache_ttl
        ]
        for key in expired_keys:
            del self._file_cache[key]


# 同步包装器（兼容原有接口）
def scan_directory(
    root_path: str,
    name_filter: Optional[str] = None,
    ext_filter: Optional[str] = None,
    use_cache: bool = True,
) -> List[str]:
    """
    同步扫描目录（兼容接口）

    Args:
        root_path: 根目录路径
        name_filter: 文件名包含的字符串
        ext_filter: 文件扩展名
        use_cache: 是否使用缓存

    Returns:
        文件路径列表
    """
    if use_cache:
        scanner = FastScanner()
    else:
        scanner = AsyncScanner()

    return asyncio.run(
        scanner.scan(root_path, name_filter=name_filter, ext_filter=ext_filter)
    )


def scan_with_metadata_sync(root_path: str, **filters) -> List[Dict[str, Any]]:
    """同步扫描并返回元数据"""
    scanner = AsyncScanner()
    return asyncio.run(scanner.scan_with_metadata(root_path, **filters))


# 性能测试函数
async def benchmark_scan(
    path: str, iterations: int = 3, use_cache: bool = False
) -> Dict[str, Any]:
    """
    性能基准测试

    Args:
        path: 测试路径
        iterations: 迭代次数
        use_cache: 是否测试缓存效果

    Returns:
        性能测试结果
    """
    results = []

    for i in range(iterations):
        if use_cache and i > 0:
            scanner = FastScanner()
        else:
            scanner = AsyncScanner()

        start = time.time()
        files = await scanner.scan(path)
        end = time.time()

        results.append(
            {
                "iteration": i + 1,
                "files_found": len(files),
                "time_seconds": end - start,
                "files_per_second": (
                    len(files) / (end - start) if (end - start) > 0 else 0
                ),
                "scanner_stats": scanner.get_stats(),
                "from_cache": (
                    getattr(scanner, "from_cache", False) if use_cache else False
                ),
            }
        )

    # 计算统计信息
    avg_time = sum(r["time_seconds"] for r in results) / len(results)
    avg_speed = sum(r["files_per_second"] for r in results) / len(results)

    return {
        "path": path,
        "iterations": iterations,
        "use_cache": use_cache,
        "results": results,
        "summary": {
            "avg_time_seconds": avg_time,
            "avg_files_per_second": avg_speed,
            "total_files_found": results[0]["files_found"] if results else 0,
            "best_time": min(r["time_seconds"] for r in results),
            "worst_time": max(r["time_seconds"] for r in results),
        },
    }


# 高级扫描功能
class AdvancedScanner(FastScanner):
    """高级扫描器，支持更多功能"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._file_handlers = {}

    def register_file_handler(self, extension: str, handler: Callable):
        """注册文件处理器"""
        self._file_handlers[extension] = handler

    async def scan_with_content(
        self, root_path: str, **filters
    ) -> List[Dict[str, Any]]:
        """扫描文件并读取内容（有限制）"""
        files = await self.scan_with_metadata(root_path, **filters)

        for file_info in files:
            # 只读取小文件
            if file_info["size"] > 1024 * 1024:  # 1MB
                continue

            extension = Path(file_info["path"]).suffix.lower()
            if extension in self._file_handlers:
                try:
                    async with aiofiles.open(
                        file_info["path"], "r", encoding="utf-8"
                    ) as f:
                        content = await f.read(10240)  # 最多读取10KB
                        file_info["content_preview"] = (
                            content[:500] + "..." if len(content) > 500 else content
                        )
                        file_info["handler"] = self._file_handlers[extension].__name__
                except Exception:
                    file_info["content_preview"] = ""
            else:
                # 默认文本文件处理
                if extension in [".txt", ".py", ".js", ".html", ".css", ".json", ".md"]:
                    try:
                        async with aiofiles.open(
                            file_info["path"], "r", encoding="utf-8"
                        ) as f:
                            content = await f.read(10240)
                            file_info["content_preview"] = (
                                content[:500] + "..." if len(content) > 500 else content
                            )
                    except Exception:
                        file_info["content_preview"] = ""

        return files


# 工具函数
def human_readable_size(size_bytes: int) -> str:
    """将字节数转换为易读的大小"""
    if size_bytes == 0:
        return "0B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.2f} {units[i]}"


def format_duration(seconds: float) -> str:
    """格式化时间间隔"""
    if seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.2f}h"


# 命令行测试
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="测试异步扫描器")
    parser.add_argument("path", nargs="?", default=".", help="扫描路径")
    parser.add_argument("--name", help="文件名过滤")
    parser.add_argument("--ext", help="文件扩展名过滤")
    parser.add_argument("--benchmark", action="store_true", help="运行性能测试")
    parser.add_argument("--iterations", type=int, default=3, help="性能测试迭代次数")
    parser.add_argument("--cache", action="store_true", help="测试缓存效果")

    args = parser.parse_args()

    async def main():
        if args.benchmark:
            print(f"性能测试: {args.path}")
            print(f"迭代次数: {args.iterations}")
            print(f"使用缓存: {args.cache}")
            print("-" * 50)

            result = await benchmark_scan(args.path, args.iterations, args.cache)

            print(f"测试路径: {result['path']}")
            print(f"总文件数: {result['summary']['total_files_found']}")
            print(f"平均时间: {format_duration(result['summary']['avg_time_seconds'])}")
            print(f"平均速度: {result['summary']['avg_files_per_second']:.1f} 文件/秒")
            print(f"最快时间: {format_duration(result['summary']['best_time'])}")
            print(f"最慢时间: {format_duration(result['summary']['worst_time'])}")

            if args.cache:
                print("\n缓存效果:")
                for r in result["results"]:
                    cache_status = "缓存命中" if r.get("from_cache") else "首次扫描"
                    print(
                        f"  迭代 {r['iteration']}: {format_duration(r['time_seconds'])} ({cache_status})"
                    )
        else:
            print(f"扫描: {args.path}")
            scanner = FastScanner() if args.cache else AsyncScanner()

            start = time.time()
            files = await scanner.scan(
                args.path, name_filter=args.name, ext_filter=args.ext
            )
            end = time.time()

            stats = scanner.get_stats()

            print(f"找到 {len(files)} 个文件")
            print(f"耗时: {format_duration(end - start)}")
            print(f"速度: {stats.get('files_per_second', 0):.1f} 文件/秒")
            print(f"总大小: {human_readable_size(stats.get('total_bytes', 0))}")
            print(f"平均文件大小: {human_readable_size(stats.get('avg_file_size', 0))}")
            print(f"跳过文件: {stats.get('files_skipped', 0)}")
            print(f"权限错误: {stats.get('permission_errors', 0)}")

            if files:
                print(f"\n前10个文件:")
                for f in files[:10]:
                    print(f"  {f}")
                if len(files) > 10:
                    print(f"  ... 还有 {len(files) - 10} 个文件")

    asyncio.run(main())

