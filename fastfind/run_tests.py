#!/usr/bin/env python3
"""
fastfind 测试执行脚本
执行完整的测试套件
"""
import os
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
import platform

class TestRunner:
    """测试运行器"""
    
    def __init__(self, project_root="."):
        self.project_root = Path(project_root).absolute()
        self.test_results = []
        self.start_time = datetime.now()
        self.report = {
            "project": "fastfind",
            "test_start": self.start_time.isoformat(),
            "environment": self._get_environment_info(),
            "results": {},
            "summary": {}
        }
    
    def _get_environment_info(self):
        """获取环境信息"""
        try:
            import fastfind
            version = fastfind.__version__
        except:
            version = "未知"
        
        return {
            "system": platform.system(),
            "release": platform.release(),
            "python_version": platform.python_version(),
            "fastfind_version": version,
            "working_directory": str(self.project_root),
            "cpu_count": os.cpu_count(),
            "python_executable": sys.executable
        }
    
    def check_test_files(self):
        """检查测试文件是否存在"""
        print("🔍 检查测试文件...")
        
        required_files = [
            "tests/unit/test_imports.py",
            "tests/integration/test_cli_basic.py",
            "tests/integration/test_performance_basic.py",
            "tests/conftest.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"⚠️  缺少测试文件: {missing_files}")
            return False
        else:
            print("✅ 测试文件检查通过")
            return True
    
    def run_unit_tests(self):
        """运行单元测试"""
        print("🔬 运行单元测试...")
        
        # 检查单元测试目录
        unit_test_dir = self.project_root / "tests" / "unit"
        if not unit_test_dir.exists():
            print("⚠️  单元测试目录不存在，创建基础测试...")
            unit_test_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建基础单元测试
            basic_test = unit_test_dir / "test_basic.py"
            if not basic_test.exists():
                basic_test.write_text('''
"""基础单元测试"""
import pytest

def test_import_fastfind():
    """测试导入fastfind包"""
    import fastfind
    assert hasattr(fastfind, '__version__')

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
''')
        
        tests = [
            ("测试基本导入", "pytest tests/unit/test_basic.py -v"),
        ]
        
        results = {}
        for name, cmd in tests:
            print(f"\n📝 {name}")
            print(f"   命令: {cmd}")
            
            try:
                start = time.time()
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    cwd=self.project_root
                )
                duration = time.time() - start
                
                if result.returncode == 0:
                    # 解析测试结果
                    lines = result.stdout.split('\n')
                    passed = 0
                    failed = 0
                    for line in lines:
                        if 'passed' in line and 'failed' in line:
                            parts = line.split()
                            for part in parts:
                                if part.isdigit():
                                    if passed == 0:
                                        passed = int(part)
                                    else:
                                        failed = int(part)
                            break
                    
                    results[name] = {
                        "status": "PASSED",
                        "passed": passed,
                        "failed": failed,
                        "duration": f"{duration:.2f}s",
                        "output": result.stdout[-500:]  # 最后500字符
                    }
                    print(f"   ✅ 通过: {passed} 通过, {failed} 失败, 耗时: {duration:.2f}s")
                else:
                    results[name] = {
                        "status": "FAILED",
                        "returncode": result.returncode,
                        "duration": f"{duration:.2f}s",
                        "error": result.stderr[:500] if result.stderr else "无错误输出"
                    }
                    print(f"   ❌ 失败: {result.returncode}, 耗时: {duration:.2f}s")
                    
            except Exception as e:
                results[name] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                print(f"   ⚠️  错误: {e}")
        
        self.report["results"]["unit_tests"] = results
        return results
    
    def run_integration_tests(self):
        """运行集成测试"""
        print("\n🔗 运行集成测试...")
        
        # 检查集成测试目录
        integration_test_dir = self.project_root / "tests" / "integration"
        if not integration_test_dir.exists():
            print("⚠️  集成测试目录不存在，创建基础测试...")
            integration_test_dir.mkdir(parents=True, exist_ok=True)
        
        tests = []
        
        # 检查CLI测试文件
        cli_test = integration_test_dir / "test_cli_basic.py"
        if not cli_test.exists():
            print("创建CLI基础测试文件...")
            cli_test.write_text('''
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
            with open(txt_file, 'w') as f:
                f.write(f"content {i}")
            
            py_file = os.path.join(tmpdir, f"script_{i}.py")
            with open(py_file, 'w') as f:
                f.write(f"print('hello {i}')")
        
        yield tmpdir

def test_find_command_basic(runner, temp_dir):
    """测试基本查找命令"""
    result = runner.invoke(cli, ['find', temp_dir])
    assert result.exit_code == 0
    assert "找到" in result.output or "搜索" in result.output

def test_find_with_name_filter(runner, temp_dir):
    """测试带名称过滤的查找"""
    result = runner.invoke(cli, ['find', temp_dir, '-n', 'test'])
    assert result.exit_code == 0

def test_find_with_type_filter(runner, temp_dir):
    """测试带类型过滤的查找"""
    result = runner.invoke(cli, ['find', temp_dir, '-t', '.py'])
    assert result.exit_code == 0

def test_info_command(runner, temp_dir):
    """测试info命令"""
    # 测试目录信息
    result = runner.invoke(cli, ['info', temp_dir])
    assert result.exit_code == 0
    
    # 测试文件信息
    test_file = os.path.join(temp_dir, "test_0.txt")
    result = runner.invoke(cli, ['info', test_file])
    assert result.exit_code == 0

def test_stats_command(runner):
    """测试stats命令"""
    result = runner.invoke(cli, ['stats'])
    assert result.exit_code == 0
    assert "fastfind" in result.output

def test_version_command(runner):
    """测试版本命令"""
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert "version" in result.output.lower()

def test_help_command(runner):
    """测试帮助命令"""
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert "Usage" in result.output
''')
        
        if cli_test.exists():
            tests.append(("测试CLI命令", "pytest tests/integration/test_cli_basic.py -v"))
        
        # 检查性能测试文件
        perf_test = integration_test_dir / "test_performance_basic.py"
        if not perf_test.exists():
            print("创建性能基础测试文件...")
            perf_test.write_text('''
"""性能测试 - 简化版本"""
import pytest
import tempfile
import time
import os
from pathlib import Path

# 跳过性能测试（除非明确要求）
pytest.mark.skipif(
    not os.getenv('RUN_PERFORMANCE_TESTS'),
    reason="性能测试需要显式启用"
)

def test_scan_performance():
    """测试扫描性能"""
    # 创建测试数据
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # 创建100个文件
        for i in range(100):
            file_path = tmp_path / f"file_{i:03d}.txt"
            file_path.write_text(f"Content of file {i}")
        
        # 导入扫描器
        from fastfind.scanner import scan_directory
        
        # 测量性能
        start_time = time.time()
        results = scan_directory(tmpdir)
        end_time = time.time()
        
        duration = end_time - start_time
        files_per_second = len(results) / duration if duration > 0 else 0
        
        print(f"\n性能测试结果:")
        print(f"  文件数量: {len(results)}")
        print(f"  扫描时间: {duration:.3f}秒")
        print(f"  速度: {files_per_second:.1f} 文件/秒")
        
        # 基本验证
        assert len(results) == 100
        assert duration < 5.0  # 应该能在5秒内完成

def test_async_scan_performance():
    """测试异步扫描性能"""
    pytest.importorskip("asyncio")
    
    # 创建测试数据
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # 创建100个文件
        for i in range(100):
            file_path = tmp_path / f"file_{i:03d}.txt")
            file_path.write_text(f"Content of file {i}")
        
        # 导入异步扫描器
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
        
        print(f"\n异步性能测试结果:")
        print(f"  文件数量: {len(results)}")
        print(f"  扫描时间: {duration:.3f}秒")
        print(f"  速度: {files_per_second:.1f} 文件/秒")
        
        # 基本验证
        assert len(results) == 100
        assert duration < 5.0
''')
        
        if perf_test.exists():
            tests.append(("测试性能", "pytest tests/integration/test_performance_basic.py -v --tb=short"))
        
        if not tests:
            print("⚠️  没有找到集成测试")
            return {}
        
        results = {}
        for name, cmd in tests:
            print(f"\n📝 {name}")
            print(f"   命令: {cmd}")
            
            try:
                start = time.time()
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    cwd=self.project_root,
                    timeout=300  # 5分钟超时
                )
                duration = time.time() - start
                
                if result.returncode == 0:
                    results[name] = {
                        "status": "PASSED",
                        "duration": f"{duration:.2f}s",
                        "output": result.stdout[-300:]
                    }
                    print(f"   ✅ 通过, 耗时: {duration:.2f}s")
                else:
                    results[name] = {
                        "status": "FAILED",
                        "returncode": result.returncode,
                        "duration": f"{duration:.2f}s",
                        "error": result.stderr[:300] if result.stderr else result.stdout[-300:]
                    }
                    print(f"   ❌ 失败: {result.returncode}, 耗时: {duration:.2f}s")
                    
            except subprocess.TimeoutExpired:
                results[name] = {
                    "status": "TIMEOUT",
                    "duration": ">300s"
                }
                print(f"   ⏰ 超时: >300s")
            except Exception as e:
                results[name] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                print(f"   ⚠️  错误: {e}")
        
        self.report["results"]["integration_tests"] = results
        return results
    
    def run_code_quality_checks(self):
        """运行代码质量检查"""
        print("\n📊 运行代码质量检查...")
        
        checks = [
            ("代码格式化检查 (black)", "black --check src/fastfind tests 2>&1"),
            ("代码风格检查 (flake8)", "flake8 src/fastfind tests --max-line-length=88 2>&1"),
        ]
        
        # 检查mypy是否可用
        try:
            subprocess.run("mypy --version", shell=True, capture_output=True)
            checks.append(("类型检查 (mypy)", "mypy src/fastfind --ignore-missing-imports 2>&1"))
        except:
            print("⚠️  mypy未安装，跳过类型检查")
        
        # 检查bandit是否可用
        try:
            subprocess.run("bandit --version", shell=True, capture_output=True)
            checks.append(("安全检查 (bandit)", "bandit -r src/fastfind -ll 2>&1"))
        except:
            print("⚠️  bandit未安装，跳过安全检查")
        
        results = {}
        for name, cmd in checks:
            print(f"\n📝 {name}")
            print(f"   命令: {cmd.split()[0]}...")
            
            try:
                start = time.time()
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    cwd=self.project_root,
                    timeout=120  # 2分钟超时
                )
                duration = time.time() - start
                
                if result.returncode == 0:
                    results[name] = {
                        "status": "PASSED",
                        "duration": f"{duration:.2f}s",
                        "output": result.stdout[:200] if result.stdout else "无输出"
                    }
                    print(f"   ✅ 通过, 耗时: {duration:.2f}s")
                else:
                    results[name] = {
                        "status": "FAILED",
                        "returncode": result.returncode,
                        "duration": f"{duration:.2f}s",
                        "error": result.stderr[:200] if result.stderr else result.stdout[:200]
                    }
                    print(f"   ❌ 失败: {result.returncode}, 耗时: {duration:.2f}s")
                    
            except subprocess.TimeoutExpired:
                results[name] = {
                    "status": "TIMEOUT",
                    "duration": ">120s"
                }
                print(f"   ⏰ 超时: >120s")
            except Exception as e:
                results[name] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                print(f"   ⚠️  错误: {e}")
        
        self.report["results"]["code_quality"] = results
        return results
    
    def run_coverage_check(self):
        """运行代码覆盖率检查"""
        print("\n📈 运行代码覆盖率检查...")
        
        cmd = "pytest --cov=src.fastfind --cov-report=term-missing"
        
        print(f"命令: {cmd}")
        
        try:
            start = time.time()
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                cwd=self.project_root,
                timeout=600  # 10分钟超时
            )
            duration = time.time() - start
            
            # 解析覆盖率结果
            coverage = 0.0
            if result.returncode == 0:
                # 从输出中提取覆盖率
                for line in result.stdout.split('\n'):
                    if 'TOTAL' in line:
                        parts = line.split()
                        for part in parts:
                            if part.endswith('%'):
                                coverage = float(part[:-1])
                                break
            
            results = {
                "status": "PASSED" if result.returncode == 0 else "FAILED",
                "coverage_percentage": coverage,
                "duration": f"{duration:.2f}s",
                "returncode": result.returncode,
                "output": result.stdout[-500:]
            }
            
            if result.returncode == 0:
                print(f"   ✅ 覆盖率: {coverage}%, 耗时: {duration:.2f}s")
            else:
                print(f"   ❌ 失败: {result.returncode}, 耗时: {duration:.2f}s")
                
        except subprocess.TimeoutExpired:
            results = {
                "status": "TIMEOUT",
                "duration": ">600s"
            }
            print(f"   ⏰ 超时: >600s")
        except Exception as e:
            results = {
                "status": "ERROR",
                "error": str(e)
            }
            print(f"   ⚠️  错误: {e}")
        
        self.report["results"]["coverage"] = results
        return results
    
    def run_cli_functional_test(self):
        """运行CLI功能测试"""
        print("\n🔧 运行CLI功能测试...")
        
        import tempfile
        from click.testing import CliRunner
        from fastfind.cli import cli
        
        runner = CliRunner()
        results = {}
        
        # 测试1: 基本find命令
        print("测试基本find命令...")
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            # 创建测试文件
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test content")
            
            result = runner.invoke(cli, ['find', tmpdir])
            if result.exit_code == 0 and ("找到" in result.output or "test.txt" in result.output):
                results["find_basic"] = {"status": "PASSED"}
                print("   ✅ find命令通过")
            else:
                results["find_basic"] = {"status": "FAILED", "error": result.output[:100]}
                print(f"   ❌ find命令失败: {result.exit_code}")
        
        # 测试2: info命令
        print("测试info命令...")
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test content")
            
            result = runner.invoke(cli, ['info', test_file])
            if result.exit_code == 0 and ("文件" in result.output or "路径" in result.output):
                results["info_file"] = {"status": "PASSED"}
                print("   ✅ info命令通过")
            else:
                results["info_file"] = {"status": "FAILED", "error": result.output[:100]}
                print(f"   ❌ info命令失败: {result.exit_code}")
        
        # 测试3: stats命令
        print("测试stats命令...")
        result = runner.invoke(cli, ['stats'])
        if result.exit_code == 0 and ("fastfind" in result.output or "版本" in result.output):
            results["stats"] = {"status": "PASSED"}
            print("   ✅ stats命令通过")
        else:
            results["stats"] = {"status": "FAILED", "error": result.output[:100]}
            print(f"   ❌ stats命令失败: {result.exit_code}")
        
        # 测试4: version命令
        print("测试version命令...")
        result = runner.invoke(cli, ['--version'])
        if result.exit_code == 0 and "version" in result.output.lower():
            results["version"] = {"status": "PASSED"}
            print("   ✅ version命令通过")
        else:
            results["version"] = {"status": "FAILED", "error": result.output[:100]}
            print(f"   ❌ version命令失败: {result.exit_code}")
        
        self.report["results"]["cli_functional"] = results
        return results
    
    def generate_summary(self):
        """生成测试摘要"""
        print("\n" + "="*60)
        print("测试执行摘要")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        # 统计单元测试
        if "unit_tests" in self.report["results"]:
            for test_name, result in self.report["results"]["unit_tests"].items():
                if result["status"] == "PASSED":
                    total_tests += result.get("passed", 0) + result.get("failed", 0)
                    passed_tests += result.get("passed", 0)
                    failed_tests += result.get("failed", 0)
        
        # 统计集成测试
        if "integration_tests" in self.report["results"]:
            for test_name, result in self.report["results"]["integration_tests"].items():
                total_tests += 1
                if result["status"] == "PASSED":
                    passed_tests += 1
                else:
                    failed_tests += 1
        
        # 统计CLI功能测试
        if "cli_functional" in self.report["results"]:
            for test_name, result in self.report["results"]["cli_functional"].items():
                total_tests += 1
                if result["status"] == "PASSED":
                    passed_tests += 1
                else:
                    failed_tests += 1
        
        # 统计质量检查
        quality_passed = 0
        quality_failed = 0
        if "code_quality" in self.report["results"]:
            for check_name, result in self.report["results"]["code_quality"].items():
                total_tests += 1
                if result["status"] == "PASSED":
                    quality_passed += 1
                    passed_tests += 1
                else:
                    quality_failed += 1
                    failed_tests += 1
        
        # 覆盖率
        coverage = 0.0
        if "coverage" in self.report["results"]:
            coverage = self.report["results"]["coverage"].get("coverage_percentage", 0)
        
        # 计算通过率
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        self.report["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": f"{pass_rate:.1f}%",
            "code_coverage": f"{coverage:.1f}%",
            "quality_checks_passed": quality_passed,
            "quality_checks_failed": quality_failed,
            "test_duration": f"{(datetime.now() - self.start_time).total_seconds():.1f}s"
        }
        
        # 显示摘要
        print(f"\n📊 测试统计:")
        print(f"  总测试数: {total_tests}")
        print(f"  通过: {passed_tests}")
        print(f"  失败: {failed_tests}")
        print(f"  通过率: {pass_rate:.1f}%")
        print(f"  代码覆盖率: {coverage:.1f}%")
        
        print(f"\n🔧 质量检查:")
        print(f"  通过: {quality_passed}")
        print(f"  失败: {quality_failed}")
        
        print(f"\n⏱️  总耗时: {(datetime.now() - self.start_time).total_seconds():.1f}秒")
        
        # 评估结果
        if pass_rate >= 90 and coverage >= 70 and quality_failed == 0:
            print("\n🎉 测试结果: ✅ 优秀 - 所有指标达标!")
        elif pass_rate >= 80 and coverage >= 60:
            print("\n👍 测试结果: ⚠️  良好 - 主要指标达标")
        else:
            print("\n⚠️  测试结果: ❌ 需要改进 - 部分指标未达标")
    
    def save_report(self, filename="test_report.json"):
        """保存测试报告"""
        self.report["test_end"] = datetime.now().isoformat()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细测试报告已保存到: {filename}")
        return filename
    
    def run_all_tests(self):
        """运行所有测试"""
        print("="*60)
        print("fastfind 项目 - 完整测试套件")
        print("="*60)
        
        try:
            # 0. 检查测试文件
            if not self.check_test_files():
                print("⚠️  测试文件不完整，将继续创建基础测试")
            
            # 1. 单元测试
            self.run_unit_tests()
            
            # 2. 集成测试
            self.run_integration_tests()
            
            # 3. CLI功能测试
            self.run_cli_functional_test()
            
            # 4. 代码质量检查
            self.run_code_quality_checks()
            
            # 5. 覆盖率检查
            self.run_coverage_check()
            
            # 6. 生成摘要
            self.generate_summary()
            
            # 7. 保存报告
            report_file = self.save_report()
            
            print(f"\n✅ 测试执行完成!")
            print(f"📁 报告文件: {report_file}")
            
            return True
            
        except KeyboardInterrupt:
            print("\n⏹️  测试被用户中断")
            return False
        except Exception as e:
            print(f"\n❌ 测试执行出错: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """主函数"""
    runner = TestRunner()
    success = runner.run_all_tests()
    
    if success:
        print("\n🎯 下一步建议:")
        print("  1. 查看测试报告: test_report.json")
        print("  2. 修复失败的测试")
        print("  3. 提高代码覆盖率")
        print("  4. 优化性能")
        print("  5. 准备提交华为比赛")
    else:
        print("\n⚠️  测试执行失败，请检查问题")

if __name__ == "__main__":
    main()
