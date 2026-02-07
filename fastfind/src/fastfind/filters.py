# -*- coding: utf-8 -*-

"""
文件过滤器模块
提供多种文件过滤条件
"""

import os
import re
import time
import fnmatch
import stat
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional, Union, Dict, Any


class FileFilter:
    """基础文件过滤器"""

    def __init__(self) -> None:
        self.conditions = []

    def add_condition(self, condition: Callable[[Path], bool]):
        """添加过滤条件"""
        self.conditions.append(condition)

    def match(self, filepath: Path) -> bool:
        """检查文件是否匹配所有条件"""
        if not self.conditions:
            return True

        for condition in self.conditions:
            if not condition(filepath):
                return False
        return True

    def filter_files(self, filepaths: List[Union[str, Path]]) -> List[str]:
        """过滤文件列表"""
        results = []
        for fp in filepaths:
            path = Path(fp) if isinstance(fp, str) else fp
            if self.match(path):
                results.append(str(path))
        return results


class NameFilter(FileFilter):
    """名称过滤器"""

    def __init__(
        self, pattern: str, use_regex: bool = False, case_sensitive: bool = False
    ):
        super().__init__()
        self.pattern = pattern
        self.use_regex = use_regex
        self.case_sensitive = case_sensitive

        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            self.regex = re.compile(pattern, flags)
            self.add_condition(self._match_regex)
        else:
            if not case_sensitive:
                pattern = pattern.lower()
            self.pattern = pattern
            self.add_condition(self._match_pattern)

    def _match_regex(self, filepath: Path) -> bool:
        """正则表达式匹配"""
        filename = filepath.name
        if not self.case_sensitive:
            filename = filename.lower()
        return bool(self.regex.search(filename))

    def _match_pattern(self, filepath: Path) -> bool:
        """模式匹配（支持通配符）"""
        filename = filepath.name
        if not self.case_sensitive:
            filename = filename.lower()
        return fnmatch.fnmatch(filename, self.pattern)


class ExtensionFilter(FileFilter):
    """扩展名过滤器"""

    def __init__(self, extensions: Union[str, List[str]], exclude: bool = False):
        super().__init__()
        if isinstance(extensions, str):
            extensions = [extensions]

        # 确保扩展名以点开头
        self.extensions = [
            ext if ext.startswith(".") else f".{ext}" for ext in extensions
        ]
        self.exclude = exclude

        self.add_condition(self._match_extension)

    def _match_extension(self, filepath: Path) -> bool:
        """匹配扩展名"""
        file_ext = filepath.suffix.lower()

        if self.exclude:
            return file_ext not in self.extensions
        else:
            return file_ext in self.extensions


class SizeFilter(FileFilter):
    """文件大小过滤器"""

    def __init__(self, min_size: Optional[int] = None, max_size: Optional[int] = None):
        super().__init__()
        self.min_size = min_size
        self.max_size = max_size

        self.add_condition(self._match_size)

    def _match_size(self, filepath: Path) -> bool:
        """匹配文件大小"""
        try:
            file_size = filepath.stat().st_size

            if self.min_size is not None and file_size < self.min_size:
                return False
            if self.max_size is not None and file_size > self.max_size:
                return False

            return True
        except (OSError, FileNotFoundError):
            return False


# 为了节省时间，先实现这些基本过滤器，测试通过后再添加更多

