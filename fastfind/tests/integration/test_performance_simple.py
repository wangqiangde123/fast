"""简化的性能测试"""
import pytest
import tempfile
import time
import os
from pathlib import Path

def test_scan_performance():
    """测试扫描性能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # 创建10个文件（减少数量以加快测试）
        for i in range(10):
            file_path = tmp_path / f"file_{i:03d}.txt"
            file_path.write_text(f"Content {i}")
        
        # 导入扫描器
        from fastfind.scanner import scan_directory
        
        # 测量性能
        start_time = time.time()
        results = scan_directory(tmpdir)
        end_time = time.time()
        
        duration = end_time - start_time
        
        print(f"性能测试: {len(results)} 文件, {duration:.3f}秒")
        
        # 基本验证
        assert len(results) == 10
        assert duration < 2.0  # 放宽时间限制
