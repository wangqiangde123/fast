# -*- coding: utf-8 -*-

"""
缓存模块
提供文件扫描结果的缓存功能
"""

import json
import pickle
import hashlib
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set
import os
import atexit
from datetime import datetime, timedelta


class CacheBase:
    """缓存基类"""

    def __init__(self, ttl: int = 300):
        self.ttl = ttl  # 生存时间（秒）
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        raise NotImplementedError

    def set(self, key: str, value: Any):
        """设置缓存值"""
        raise NotImplementedError

    def delete(self, key: str):
        """删除缓存值"""
        raise NotImplementedError

    def clear(self):
        """清空缓存"""
        raise NotImplementedError

    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": (
                self.hits / (self.hits + self.misses)
                if (self.hits + self.misses) > 0
                else 0
            ),
            "ttl": self.ttl,
        }


class MemoryCache(CacheBase):
    """内存缓存"""

    def __init__(self, ttl: int = 300, max_size: int = 1000):
        super().__init__(ttl)
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_order: List[str] = []

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            entry = self._cache[key]

            # 检查是否过期
            if time.time() - entry["timestamp"] > self.ttl:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self.misses += 1
                return None

            # 更新访问顺序
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            self.hits += 1
            return entry["value"]

        self.misses += 1
        return None

    def set(self, key: str, value: Any):
        """设置缓存值"""
        # 如果达到最大大小，移除最旧的条目
        if len(self._cache) >= self.max_size and self._access_order:
            oldest_key = self._access_order.pop(0)
            if oldest_key in self._cache:
                del self._cache[oldest_key]

        self._cache[key] = {"value": value, "timestamp": time.time()}

        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def delete(self, key: str):
        """删除缓存值"""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._access_order.clear()
        self.hits = 0
        self.misses = 0

    def cleanup_expired(self):
        """清理过期条目"""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if current_time - entry["timestamp"] > self.ttl
        ]

        for key in expired_keys:
            self.delete(key)

        return len(expired_keys)


class DiskCache(CacheBase):
    """磁盘缓存（使用SQLite）"""

    def __init__(self, cache_dir: Optional[str] = None, ttl: int = 3600):
        super().__init__(ttl)

        if cache_dir is None:
            cache_dir = os.path.join(str(Path.home()), ".cache", "fastfind")

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / "cache.db"
        self._init_database()

        atexit.register(self.close)

    def _init_database(self):
        """初始化数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        # 创建缓存表
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_cache (
            key TEXT PRIMARY KEY,
            value BLOB,
            timestamp REAL,
            path TEXT,
            file_count INTEGER,
            total_size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 创建索引
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON file_cache(timestamp)"
        )
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_path ON file_cache(path)")

        self.conn.commit()

    def _make_key(self, path: str, filters: Dict[str, Any]) -> str:
        """生成缓存键"""
        import json

        key_data = {"path": os.path.abspath(path), "filters": filters, "version": "1.0"}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            self.cursor.execute(
                "SELECT value, timestamp FROM file_cache WHERE key = ?", (key,)
            )
            result = self.cursor.fetchone()

            if result:
                value_blob, timestamp = result

                # 检查是否过期
                if time.time() - timestamp > self.ttl:
                    self.delete(key)
                    self.misses += 1
                    return None

                # 反序列化
                try:
                    value = pickle.loads(value_blob)
                    self.hits += 1
                    return value
                except Exception:
                    self.delete(key)
                    self.misses += 1
                    return None
            else:
                self.misses += 1
                return None
        except Exception:
            self.misses += 1
            return None

    def set(
        self, key: str, value: Any, path: str = "", metadata: Optional[Dict] = None
    ):
        """设置缓存值"""
        try:
            # 序列化值
            value_blob = pickle.dumps(value)
            timestamp = time.time()

            # 提取元数据
            file_count = len(value) if isinstance(value, list) else 0
            total_size = metadata.get("total_size", 0) if metadata else 0

            self.cursor.execute(
                """
            INSERT OR REPLACE INTO file_cache 
            (key, value, timestamp, path, file_count, total_size)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
                (key, value_blob, timestamp, path, file_count, total_size),
            )

            self.conn.commit()
        except Exception as e:
            print(f"缓存设置失败: {e}")

    def delete(self, key: str):
        """删除缓存值"""
        try:
            self.cursor.execute("DELETE FROM file_cache WHERE key = ?", (key,))
            self.conn.commit()
        except Exception:
            pass

    def clear(self):
        """清空缓存"""
        try:
            self.cursor.execute("DELETE FROM file_cache")
            self.conn.commit()
            self.hits = 0
            self.misses = 0
        except Exception:
            pass

    def cleanup_expired(self) -> int:
        """清理过期条目"""
        try:
            expire_time = time.time() - self.ttl
            self.cursor.execute(
                "DELETE FROM file_cache WHERE timestamp < ?", (expire_time,)
            )
            deleted_count = self.cursor.rowcount
            self.conn.commit()
            return deleted_count
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM file_cache")
            total_entries = self.cursor.fetchone()[0]

            self.cursor.execute("SELECT SUM(file_count) FROM file_cache")
            total_files = self.cursor.fetchone()[0] or 0

            self.cursor.execute("SELECT SUM(total_size) FROM file_cache")
            total_size = self.cursor.fetchone()[0] or 0

            self.cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM file_cache")
            min_ts, max_ts = self.cursor.fetchone()

            oldest = datetime.fromtimestamp(min_ts).isoformat() if min_ts else None
            newest = datetime.fromtimestamp(max_ts).isoformat() if max_ts else None

            base_stats = self.stats()
            base_stats.update(
                {
                    "total_entries": total_entries,
                    "total_files_cached": total_files,
                    "total_size_cached": total_size,
                    "oldest_entry": oldest,
                    "newest_entry": newest,
                    "cache_file_size": (
                        self.db_path.stat().st_size if self.db_path.exists() else 0
                    ),
                }
            )

            return base_stats
        except Exception:
            return self.stats()

    def close(self):
        """关闭数据库连接"""
        try:
            self.cleanup_expired()
            self.conn.close()
        except Exception:
            pass


class HierarchicalCache:
    """分层缓存（内存 + 磁盘）"""

    def __init__(self, memory_ttl: int = 300, disk_ttl: int = 3600):
        self.memory_cache = MemoryCache(ttl=memory_ttl)
        self.disk_cache = DiskCache(ttl=disk_ttl)

    def get(
        self, key: str, path: str = "", filters: Optional[Dict] = None
    ) -> Optional[Any]:
        """获取缓存值（先内存后磁盘）"""
        # 首先尝试内存缓存
        value = self.memory_cache.get(key)
        if value is not None:
            return value

        # 然后尝试磁盘缓存
        value = self.disk_cache.get(key)
        if value is not None:
            # 存入内存缓存
            self.memory_cache.set(key, value)
            return value

        return None

    def set(
        self, key: str, value: Any, path: str = "", metadata: Optional[Dict] = None
    ):
        """设置缓存值（同时存入内存和磁盘）"""
        self.memory_cache.set(key, value)
        self.disk_cache.set(key, value, path, metadata)

    def delete(self, key: str):
        """删除缓存值"""
        self.memory_cache.delete(key)
        self.disk_cache.delete(key)

    def clear(self):
        """清空所有缓存"""
        self.memory_cache.clear()
        self.disk_cache.clear()

    def cleanup(self) -> Dict[str, int]:
        """清理所有过期条目"""
        memory_cleaned = self.memory_cache.cleanup_expired()
        disk_cleaned = self.disk_cache.cleanup_expired()

        return {
            "memory_cleaned": memory_cleaned,
            "disk_cleaned": disk_cleaned,
            "total_cleaned": memory_cleaned + disk_cleaned,
        }

    def stats(self) -> Dict[str, Any]:
        """获取所有缓存统计信息"""
        memory_stats = self.memory_cache.stats()
        disk_stats = self.disk_cache.get_stats()

        return {
            "memory": memory_stats,
            "disk": disk_stats,
            "combined_hit_rate": (
                (memory_stats["hits"] + disk_stats["hits"])
                / (
                    memory_stats["hits"]
                    + memory_stats["misses"]
                    + disk_stats["hits"]
                    + disk_stats["misses"]
                )
                if (
                    memory_stats["hits"]
                    + memory_stats["misses"]
                    + disk_stats["hits"]
                    + disk_stats["misses"]
                )
                > 0
                else 0
            ),
        }


class FileSystemCache:
    """文件系统缓存（基于文件修改时间）"""

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            cache_dir = os.path.join(str(Path.home()), ".cache", "fastfind", "fscache")

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_directory_state(self, path: str) -> Optional[Dict[str, Any]]:
        """获取目录状态信息"""
        dir_path = Path(path)
        if not dir_path.exists() or not dir_path.is_dir():
            return None

        cache_file = self._get_cache_file(path)
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_state = json.load(f)

                # 检查目录是否已修改
                dir_mtime = dir_path.stat().st_mtime
                if dir_mtime <= cached_state.get("mtime", 0):
                    return cached_state
            except Exception:
                pass

        return None

    def set_directory_state(self, path: str, state: Dict[str, Any]):
        """设置目录状态信息"""
        dir_path = Path(path)
        if not dir_path.exists() or not dir_path.is_dir():
            return

        state["mtime"] = dir_path.stat().st_mtime
        state["cached_at"] = time.time()
        state["path"] = str(dir_path.absolute())

        cache_file = self._get_cache_file(path)
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def _get_cache_file(self, path: str) -> Path:
        """获取缓存文件路径"""
        # 使用路径的哈希值作为文件名
        path_hash = hashlib.md5(str(Path(path).absolute()).encode()).hexdigest()
        return self.cache_dir / f"{path_hash}.json"

    def cleanup_old_cache(self, max_age_days: int = 7):
        """清理旧的缓存文件"""
        cutoff_time = time.time() - (max_age_days * 24 * 3600)

        deleted = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                if cache_file.stat().st_mtime < cutoff_time:
                    cache_file.unlink()
                    deleted += 1
            except Exception:
                pass

        return deleted


# 缓存管理器
class CacheManager:
    """缓存管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.hierarchical_cache = HierarchicalCache()
        self.fs_cache = FileSystemCache()
        self.enabled = True

    def enable(self):
        """启用缓存"""
        self.enabled = True

    def disable(self):
        """禁用缓存"""
        self.enabled = False

    def get_file_list(self, path: str, filters: Dict[str, Any]) -> Optional[List[str]]:
        """获取缓存的文件列表"""
        if not self.enabled:
            return None

        cache_key = self._make_cache_key(path, filters)
        return self.hierarchical_cache.get(cache_key, path, filters)

    def set_file_list(
        self,
        path: str,
        filters: Dict[str, Any],
        file_list: List[str],
        metadata: Optional[Dict] = None,
    ):
        """缓存文件列表"""
        if not self.enabled:
            return

        cache_key = self._make_cache_key(path, filters)

        if metadata is None:
            # 计算总大小
            total_size = 0
            for filepath in file_list:
                try:
                    total_size += Path(filepath).stat().st_size
                except Exception:
                    pass

            metadata = {"total_size": total_size, "file_count": len(file_list)}

        self.hierarchical_cache.set(cache_key, file_list, path, metadata)

    def get_directory_stats(self, path: str) -> Optional[Dict[str, Any]]:
        """获取缓存的目录统计信息"""
        if not self.enabled:
            return None
        return self.fs_cache.get_directory_state(path)

    def set_directory_stats(self, path: str, stats: Dict[str, Any]):
        """缓存目录统计信息"""
        if not self.enabled:
            return
        self.fs_cache.set_directory_state(path, stats)

    def _make_cache_key(self, path: str, filters: Dict[str, Any]) -> str:
        """生成缓存键"""
        import json

        key_data = {
            "path": os.path.abspath(path),
            "filters": {k: v for k, v in filters.items() if v is not None},
            "cache_version": "2.0",
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def clear_all(self):
        """清空所有缓存"""
        self.hierarchical_cache.clear()
        # 文件系统缓存需要手动清理文件

    def cleanup(self) -> Dict[str, int]:
        """清理所有过期缓存"""
        hierarchical_cleanup = self.hierarchical_cache.cleanup()
        fs_cleanup = self.fs_cache.cleanup_old_cache()

        hierarchical_cleanup["fs_cleaned"] = fs_cleanup
        hierarchical_cleanup["total_cleaned"] = (
            hierarchical_cleanup["total_cleaned"] + fs_cleanup
        )

        return hierarchical_cleanup

    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "enabled": self.enabled,
            "hierarchical": self.hierarchical_cache.stats(),
            "filesystem": {
                "cache_dir": str(self.fs_cache.cache_dir),
                "cache_files": len(list(self.fs_cache.cache_dir.glob("*.json"))),
            },
        }


# 全局缓存实例
cache_manager = CacheManager()


if __name__ == "__main__":
    # 测试缓存功能
    import tempfile

    print("测试缓存系统...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        test_files = []
        for i in range(10):
            test_file = Path(tmpdir) / f"test_{i}.txt"
            test_file.write_text(f"content {i}")
            test_files.append(str(test_file))

        # 测试缓存
        filters = {"ext": ".txt"}

        # 第一次获取（应该缓存未命中）
        print("第一次获取（应该缓存未命中）:")
        cached = cache_manager.get_file_list(tmpdir, filters)
        print(f"  结果: {'命中' if cached else '未命中'}")

        # 设置缓存
        print("设置缓存...")
        cache_manager.set_file_list(tmpdir, filters, test_files)

        # 第二次获取（应该缓存命中）
        print("第二次获取（应该缓存命中）:")
        cached = cache_manager.get_file_list(tmpdir, filters)
        print(f"  结果: {'命中' if cached else '未命中'}")

        if cached:
            print(f"  缓存文件数: {len(cached)}")

        # 测试统计信息
        print("\n缓存统计:")
        stats = cache_manager.stats()
        print(f"  启用状态: {stats['enabled']}")
        print(f"  内存命中率: {stats['hierarchical']['memory']['hit_rate']:.2%}")
        print(f"  磁盘命中率: {stats['hierarchical']['disk']['hit_rate']:.2%}")

        # 清理
        print("\n清理缓存...")
        cleanup_stats = cache_manager.cleanup()
        print(f"  清理条目: {cleanup_stats['total_cleaned']}")

        # 清空缓存
        print("清空所有缓存...")
        cache_manager.clear_all()
        print("完成!")

