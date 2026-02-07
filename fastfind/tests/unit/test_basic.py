"""基础单元测试"""

import pytest


def test_import_fastfind():
    """测试导入fastfind包"""
    import fastfind

    assert hasattr(fastfind, "__version__")


def test_import_scanner():
    """测试导入scanner模块"""
    from fastfind import scanner

    assert scanner is not None


def test_import_filters():
    """测试导入filters模块"""
    try:
        from fastfind import filters

        assert filters is not None
    except ImportError:
        pytest.skip("filters模块未找到")


def test_import_cache():
    """测试导入cache模块"""
    try:
        from fastfind import cache

        assert cache is not None
    except ImportError:
        pytest.skip("cache模块未找到")


def test_import_utils():
    """测试导入utils模块"""
    try:
        from fastfind import utils

        assert utils is not None
    except ImportError:
        pytest.skip("utils模块未找到")


def test_import_cli():
    """测试导入cli模块"""
    from fastfind import cli

    assert cli is not None
