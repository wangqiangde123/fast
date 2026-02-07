# setup_tests.ps1 - 一键设置测试环境
Write-Host "设置fastfind测试环境..." -ForegroundColor Green
Write-Host "="*60 -ForegroundColor Cyan

# 检查当前目录
$currentDir = Get-Location
Write-Host "当前目录: $currentDir" -ForegroundColor Yellow

# 1. 检查Python环境
Write-Host "`n1. 检查Python环境..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 未找到Python，请先安装Python 3.8+" -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ Python版本: $pythonVersion" -ForegroundColor Green

# 2. 创建虚拟环境（如果不存在）
Write-Host "`n2. 设置虚拟环境..." -ForegroundColor Yellow
if (Test-Path ".venv_test") {
    Write-Host "   虚拟环境已存在，跳过创建" -ForegroundColor Gray
} else {
    Write-Host "   创建虚拟环境..." -ForegroundColor Gray
    python -m venv .venv_test
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ 虚拟环境创建成功" -ForegroundColor Green
    } else {
        Write-Host "   ❌ 虚拟环境创建失败" -ForegroundColor Red
        Write-Host "   尝试使用: python3 -m venv .venv_test" -ForegroundColor Yellow
        exit 1
    }
}

# 3. 激活虚拟环境
Write-Host "`n3. 激活虚拟环境..." -ForegroundColor Yellow
try {
    .\.venv_test\Scripts\Activate.ps1
    Write-Host "   ✅ 虚拟环境激活成功" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  激活失败，尝试手动激活" -ForegroundColor Yellow
    Write-Host "      .\.venv_test\Scripts\Activate.ps1" -ForegroundColor White
}

# 4. 安装项目
Write-Host "`n4. 安装fastfind项目..." -ForegroundColor Yellow
pip install -e .
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ 项目安装成功" -ForegroundColor Green
} else {
    Write-Host "   ❌ 项目安装失败" -ForegroundColor Red
    exit 1
}

# 5. 安装测试依赖
Write-Host "`n5. 安装测试依赖..." -ForegroundColor Yellow
$testDeps = @(
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0",
    "flake8>=6.0",
    "mypy>=1.0",
    "bandit>=1.7.0"
)

foreach ($dep in $testDeps) {
    Write-Host "   安装 $dep..." -ForegroundColor Gray -NoNewline
    pip install $dep 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅" -ForegroundColor Green
    } else {
        Write-Host " ❌" -ForegroundColor Red
        Write-Host "   警告: $dep 安装失败，可能影响部分测试" -ForegroundColor Yellow
    }
}

# 6. 检查测试文件
Write-Host "`n6. 检查测试文件..." -ForegroundColor Yellow
$requiredFiles = @(
    "test_plan.py",
    "run_tests.py",
    "tests/conftest.py",
    "tests/unit/test_basic.py",
    "tests/integration/test_cli_basic.py"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (!(Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "   ⚠️  缺少文件: $missingFiles" -ForegroundColor Yellow
    Write-Host "   将创建缺少的测试文件..." -ForegroundColor Gray
} else {
    Write-Host "   ✅ 所有测试文件就绪" -ForegroundColor Green
}

Write-Host "`n" + "="*60 -ForegroundColor Cyan
Write-Host "✅ 测试环境设置完成!" -ForegroundColor Green
Write-Host "`n下一步操作:" -ForegroundColor Cyan
Write-Host "1. 确保虚拟环境已激活: .\.venv_test\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "2. 生成测试方案: python test_plan.py" -ForegroundColor White
Write-Host "3. 运行完整测试: python run_tests.py" -ForegroundColor White
Write-Host "4. 运行单元测试: pytest tests/unit/ -v" -ForegroundColor White
Write-Host "5. 查看测试方案: test_plan.json" -ForegroundColor White
Write-Host "`n提示: 如果虚拟环境未激活，请先运行第一步!" -ForegroundColor Yellow
