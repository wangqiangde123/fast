# -*- coding: utf-8 -*-


"""���ܲ��� - �򻯰汾"""
import pytest
import tempfile
import time
import os
from pathlib import Path

# �������ܲ��ԣ�������ȷҪ��
pytest.mark.skipif(
    not os.getenv('RUN_PERFORMANCE_TESTS'),
    reason="���ܲ�����Ҫ��ʽ����"
)

def test_scan_performance():
    """����ɨ������"""
    # ������������
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # ����100���ļ�
        for i in range(100):
            file_path = tmp_path / f"file_{i:03d}.txt"
            file_path.write_text(f"Content of file {i}")
        
        # ����ɨ����
        from fastfind.scanner import scan_directory
        
        # ��������
        start_time = time.time()
        results = scan_directory(tmpdir)
        end_time = time.time()
        
        duration = end_time - start_time
        files_per_second = len(results) / duration if duration > 0 else 0
        
        print(f"
���ܲ��Խ��:")
        print(f"  �ļ�����: {len(results)}")
        print(f"  ɨ��ʱ��: {duration:.3f}��")
        print(f"  �ٶ�: {files_per_second:.1f} �ļ�/��")
        
        # ������֤
        assert len(results) == 100
        assert duration < 5.0  # Ӧ������5�������

def test_async_scan_performance():
    """�����첽ɨ������"""
    pytest.importorskip("asyncio")
    
    # ������������
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # ����100���ļ�
        for i in range(100):
            file_path = tmp_path / f"file_{i:03d}.txt")
            file_path.write_text(f"Content of file {i}")
        
        # �����첽ɨ����
        from fastfind.scanner import AsyncScanner
        import asyncio
        
        async def run_test():
            scanner = AsyncScanner()
            start_time = time.time()
            results = await scanner.scan(tmpdir)
            end_time = time.time()
            return results, end_time - start_time
        
        results, duration = asyncio.run(run_test())
        files_per_second = len(results) / duration if duration > 0 else 0
        
        print(f"
�첽���ܲ��Խ��:")
        print(f"  �ļ�����: {len(results)}")
        print(f"  ɨ��ʱ��: {duration:.3f}��")
        print(f"  �ٶ�: {files_per_second:.1f} �ļ�/��")
        
        # ������֤
        assert len(results) == 100
        assert duration < 5.0

