import os
import sys
import tempfile
import pytest

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_version():
    """测试版本号"""
    from fastfind import __version__

    assert __version__ == "0.1.0"


def test_import():
    """测试导入"""
    import fastfind

    assert fastfind is not None


def test_cli_import():
    """测试CLI模块导入"""
    from fastfind import cli

    assert cli is not None


def test_simple_find():
    """测试简单查找功能"""
    from fastfind.cli import simple_find

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")

        # 测试查找
        results = simple_find(tmpdir)
        assert len(results) >= 1
        assert any("test.txt" in r for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
