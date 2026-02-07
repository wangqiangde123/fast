"""CLI集成测试 - 简化版本"""

import pytest
import tempfile
import os
from click.testing import CliRunner

from fastfind.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_dir():
    """创建临时测试目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建一些测试文件
        for i in range(5):
            txt_file = os.path.join(tmpdir, f"test_{i}.txt")
            with open(txt_file, "w") as f:
                f.write(f"content {i}")

            py_file = os.path.join(tmpdir, f"script_{i}.py")
            with open(py_file, "w") as f:
                f.write(f"print('hello {i}')")

        yield tmpdir


def test_find_command_basic(runner, temp_dir):
    """测试基本查找命令"""
    result = runner.invoke(cli, ["find", temp_dir])
    assert result.exit_code == 0
    assert "找到" in result.output or "搜索" in result.output


def test_find_with_name_filter(runner, temp_dir):
    """测试带名称过滤的查找"""
    result = runner.invoke(cli, ["find", temp_dir, "-n", "test"])
    assert result.exit_code == 0


def test_find_with_type_filter(runner, temp_dir):
    """测试带类型过滤的查找"""
    result = runner.invoke(cli, ["find", temp_dir, "-t", ".py"])
    assert result.exit_code == 0


def test_info_command(runner, temp_dir):
    """测试info命令"""
    # 测试目录信息
    result = runner.invoke(cli, ["info", temp_dir])
    assert result.exit_code == 0

    # 测试文件信息
    test_file = os.path.join(temp_dir, "test_0.txt")
    result = runner.invoke(cli, ["info", test_file])
    assert result.exit_code == 0


def test_stats_command(runner):
    """测试stats命令"""
    result = runner.invoke(cli, ["stats"])
    assert result.exit_code == 0
    assert "fastfind" in result.output


def test_version_command(runner):
    """测试版本命令"""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()


def test_help_command(runner):
    """测试帮助命令"""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
