# VLLM 手动安装脚本 (Windows PowerShell)
# 用于安装 SoulX-Podcast 修改版的 VLLM 0.10.1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VLLM 手动安装脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "[1/5] 检查 Python 环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python 已安装: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 未找到 Python，请先安装 Python 3.11" -ForegroundColor Red
    exit 1
}

# 检查 CUDA
Write-Host "[2/5] 检查 CUDA 支持..." -ForegroundColor Yellow
try {
    $cudaCheck = python -c "import torch; print('CUDA available:', torch.cuda.is_available())" 2>&1
    Write-Host "✅ $cudaCheck" -ForegroundColor Green
    if ($cudaCheck -notmatch "True") {
        Write-Host "⚠️  警告: CUDA 不可用，VLLM 需要 GPU 支持" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  警告: 无法检查 CUDA，请确保已安装 PyTorch" -ForegroundColor Yellow
}

# 安装基础 VLLM
Write-Host "[3/5] 安装基础 VLLM 0.10.1..." -ForegroundColor Yellow
Write-Host "这可能需要几分钟时间..." -ForegroundColor Gray
try {
    pip install vllm==0.10.1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ VLLM 0.10.1 安装成功" -ForegroundColor Green
    } else {
        Write-Host "❌ VLLM 安装失败，尝试从源码安装..." -ForegroundColor Red
        Write-Host "请手动执行: pip install git+https://github.com/vllm-project/vllm.git@v0.10.1" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ 安装失败: $_" -ForegroundColor Red
    exit 1
}

# 获取 VLLM 安装路径
Write-Host "[4/5] 获取 VLLM 安装路径..." -ForegroundColor Yellow
try {
    $vllmPath = python -c "import vllm; import os; print(os.path.dirname(vllm.__file__))"
    Write-Host "✅ VLLM 路径: $vllmPath" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 无法获取 VLLM 路径，请检查安装" -ForegroundColor Red
    exit 1
}

# 克隆修改版 VLLM
Write-Host "[5/5] 下载修改版 VLLM 文件..." -ForegroundColor Yellow
$tempDir = $env:TEMP
$vllmRepoPath = Join-Path $tempDir "vllm"

if (Test-Path $vllmRepoPath) {
    Write-Host "清理旧的仓库..." -ForegroundColor Gray
    Remove-Item -Recurse -Force $vllmRepoPath
}

try {
    Write-Host "克隆 Soul-AILab/vllm 仓库..." -ForegroundColor Gray
    git clone https://github.com/Soul-AILab/vllm.git $vllmRepoPath
    if ($LASTEXITCODE -ne 0) {
        throw "Git clone 失败"
    }
    
    Push-Location $vllmRepoPath
    git checkout v0.10.1.1-soulxpodcast
    if ($LASTEXITCODE -ne 0) {
        throw "Git checkout 失败"
    }
    Pop-Location
    
    Write-Host "✅ 修改版 VLLM 下载成功" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 下载修改版 VLLM 失败: $_" -ForegroundColor Red
    Write-Host "请手动执行:" -ForegroundColor Yellow
    Write-Host "  cd $tempDir" -ForegroundColor Yellow
    Write-Host "  git clone https://github.com/Soul-AILab/vllm.git" -ForegroundColor Yellow
    Write-Host "  cd vllm" -ForegroundColor Yellow
    Write-Host "  git checkout v0.10.1.1-soulxpodcast" -ForegroundColor Yellow
    exit 1
}

# 复制修改版文件
Write-Host "[6/6] 应用修改版文件..." -ForegroundColor Yellow
try {
    $modifiedFiles = @(
        @{Source = "vllm\model_executor\layers\sampler.py"; Dest = "model_executor\layers\sampler.py"},
        @{Source = "vllm\model_executor\layers\utils.py"; Dest = "model_executor\layers\utils.py"},
        @{Source = "vllm\model_executor\sampling_metadata.py"; Dest = "model_executor\sampling_metadata.py"},
        @{Source = "vllm\sampling_params.py"; Dest = "sampling_params.py"}
    )
    
    foreach ($file in $modifiedFiles) {
        $sourcePath = Join-Path $vllmRepoPath $file.Source
        $destPath = Join-Path $vllmPath $file.Dest
        
        if (-not (Test-Path $sourcePath)) {
            Write-Host "⚠️  警告: 源文件不存在: $($file.Source)" -ForegroundColor Yellow
            continue
        }
        
        $destDir = Split-Path $destPath -Parent
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        
        Copy-Item $sourcePath $destPath -Force
        Write-Host "  ✅ 已复制: $($file.Dest)" -ForegroundColor Gray
    }
    
    Write-Host "✅ 修改版文件应用成功" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 复制文件失败: $_" -ForegroundColor Red
    Write-Host "请手动复制文件从 $vllmRepoPath 到 $vllmPath" -ForegroundColor Yellow
    exit 1
}

# 验证安装
Write-Host ""
Write-Host "验证安装..." -ForegroundColor Yellow
try {
    python -c "from vllm import LLM; print('✅ VLLM 安装成功，可以正常导入')"
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "✅ VLLM 安装完成！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "下一步：" -ForegroundColor Yellow
    Write-Host "1. 设置环境变量: `$env:SOULX_PODCAST_LLM_ENGINE = 'vllm'" -ForegroundColor White
    Write-Host "2. 或在 config.py 中设置: SOULX_PODCAST_LLM_ENGINE = 'vllm'" -ForegroundColor White
    Write-Host ""
} catch {
    Write-Host "❌ 验证失败: $_" -ForegroundColor Red
    Write-Host "请检查安装过程" -ForegroundColor Yellow
    exit 1
}

