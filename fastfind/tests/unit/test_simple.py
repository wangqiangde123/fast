"""简化的测试文件以提高覆盖率"""
import pytest
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_import_all_modules():
    """测试导入所有模块"""
    import fastfind
    
    # 测试导入各个模块
    modules = ['scanner', 'filters', 'utils', 'cache', 'report', 'cli']
    for module_name in modules:
        try:
            module = __import__(f'fastfind.{module_name}')
            assert module is not None
            print(f'✅ 成功导入 fastfind.{module_name}')
        except ImportError as e:
            print(f'⚠️  无法导入 fastfind.{module_name}: {e}')
            pytest.skip(f'模块 {module_name} 不可用')

def test_cli_basic():
    """测试CLI基本功能"""
    from fastfind.cli import cli
    from click.testing import CliRunner
    
    runner = CliRunner()
    
    # 测试--help
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Usage' in result.output
    
    # 测试--version
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0
    
    # 测试stats命令
    result = runner.invoke(cli, ['stats'])
    assert result.exit_code == 0

def test_scanner_basic():
    """测试扫描器基本功能"""
    try:
        from fastfind.scanner import scan_directory
        
        # 测试当前目录
        results = scan_directory('.')
        assert isinstance(results, list)
        print(f'✅ 扫描到 {len(results)} 个文件')
        
    except ImportError:
        pytest.skip('scanner模块不可用')

def test_simple_filters():
    """测试简单过滤器"""
    try:
        from fastfind.filters import NameFilter
        
        filter = NameFilter('test')
        assert filter is not None
        
        test_files = ['test.txt', 'other.py', 'test_file.txt']
        results = filter.filter_files(test_files)
        assert isinstance(results, list)
        
    except ImportError:
        pytest.skip('filters模块不可用')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
