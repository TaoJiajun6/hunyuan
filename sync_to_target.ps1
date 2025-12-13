# 将本地 hunyuan 目录内容同步到目标仓库的 hunyuan 文件夹
# 使用方法: .\sync_to_target.ps1 -TargetRepoUrl "<目标仓库地址>"

param(
    [Parameter(Mandatory=$true)]
    [string]$TargetRepoUrl,
    
    [string]$TargetBranch = "master",
    [string]$CommitMessage = "更新：覆盖 hunyuan 文件夹内容"
)

Write-Host "=== 开始同步本地代码到目标仓库 ===" -ForegroundColor Green

# 1. 确保当前目录是 hunyuan 项目根目录
$CurrentDir = Get-Location
Write-Host "当前目录: $CurrentDir" -ForegroundColor Yellow

# 2. 先提交本地更改
Write-Host "`n[1/6] 检查并提交本地更改..." -ForegroundColor Yellow
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "发现未提交的更改，正在提交..." -ForegroundColor Yellow
    git add .
    git commit -m "准备同步: $CommitMessage"
} else {
    Write-Host "没有未提交的更改，跳过" -ForegroundColor Green
}

# 3. 创建临时目录并克隆目标仓库
Write-Host "`n[2/6] 克隆目标仓库到临时目录..." -ForegroundColor Yellow
$TempDir = Join-Path $env:TEMP "sync-target-repo-$(Get-Date -Format 'yyyyMMddHHmmss')"
if (Test-Path $TempDir) {
    Remove-Item -Recurse -Force $TempDir
}
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

try {
    git clone $TargetRepoUrl $TempDir
    if ($LASTEXITCODE -ne 0) {
        throw "克隆目标仓库失败"
    }
    Write-Host "✅ 克隆成功" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: $_" -ForegroundColor Red
    exit 1
}

# 4. 切换到目标仓库的指定分支
Write-Host "`n[3/6] 切换到目标分支 $TargetBranch..." -ForegroundColor Yellow
Push-Location $TempDir
try {
    git checkout $TargetBranch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "分支 $TargetBranch 不存在，尝试创建..." -ForegroundColor Yellow
        git checkout -b $TargetBranch
    }
    Write-Host "✅ 切换到 $TargetBranch 分支" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: $_" -ForegroundColor Red
    Pop-Location
    Remove-Item -Recurse -Force $TempDir
    exit 1
}

# 5. 删除目标仓库中的旧 hunyuan 文件夹
Write-Host "`n[4/6] 删除目标仓库中的旧 hunyuan 文件夹..." -ForegroundColor Yellow
if (Test-Path "hunyuan") {
    git rm -r hunyuan
    Write-Host "✅ 已删除旧的 hunyuan 文件夹" -ForegroundColor Green
} else {
    Write-Host "目标仓库中没有 hunyuan 文件夹，跳过删除" -ForegroundColor Yellow
}

# 6. 复制本地 hunyuan 目录内容到目标仓库
Write-Host "`n[5/6] 复制本地代码到目标仓库..." -ForegroundColor Yellow
try {
    # 使用 robocopy 复制，排除 .git 等目录
    $SourcePath = $CurrentDir
    $DestPath = Join-Path $TempDir "hunyuan"
    
    # 创建目标目录
    New-Item -ItemType Directory -Path $DestPath -Force | Out-Null
    
    # 使用 robocopy 复制文件（排除 .git, __pycache__, .cursor 等）
    $RobocopyArgs = @(
        $SourcePath,
        $DestPath,
        "/E",           # 复制所有子目录
        "/XD",          # 排除目录
        ".git",
        "__pycache__",
        ".cursor",
        ".idea",
        "node_modules",
        ".pytest_cache",
        "*.egg-info",
        "dist",
        "build"
    )
    
    $RobocopyResult = & robocopy @RobocopyArgs /NJH /NJS /NP /NDL /NC /NS
    $ExitCode = $LASTEXITCODE
    
    # robocopy 的退出代码：0-7 都表示成功
    if ($ExitCode -le 7) {
        Write-Host "✅ 文件复制成功" -ForegroundColor Green
    } else {
        Write-Host "⚠️ 复制过程中有警告，退出代码: $ExitCode" -ForegroundColor Yellow
    }
    
    # 添加 .gitignore 确保不包含不必要的文件
    $GitIgnoreContent = @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# IDE
.idea/
.vscode/
.cursor/

# Environment
.env
.venv
venv/
ENV/

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Model files (too large)
SoulX-Podcast/pretrained_models/
*.bin
*.safetensors
*.model
*.ckpt
"@
    
    $GitIgnorePath = Join-Path $DestPath ".gitignore"
    if (-not (Test-Path $GitIgnorePath)) {
        Set-Content -Path $GitIgnorePath -Value $GitIgnoreContent -Encoding UTF8
    }
    
} catch {
    Write-Host "❌ 复制文件失败: $_" -ForegroundColor Red
    Pop-Location
    Remove-Item -Recurse -Force $TempDir
    exit 1
}

# 7. 提交并推送到目标仓库
Write-Host "`n[6/6] 提交并推送到目标仓库..." -ForegroundColor Yellow
try {
    git add .
    git commit -m $CommitMessage
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️ 没有更改需要提交（可能内容相同）" -ForegroundColor Yellow
    } else {
        Write-Host "✅ 提交成功" -ForegroundColor Green
    }
    
    git push origin $TargetBranch
    if ($LASTEXITCODE -ne 0) {
        throw "推送到目标仓库失败，请检查权限"
    }
    Write-Host "✅ 推送成功！" -ForegroundColor Green
    
} catch {
    Write-Host "❌ 错误: $_" -ForegroundColor Red
    Write-Host "提示：您可以手动进入临时目录完成提交和推送" -ForegroundColor Yellow
    Write-Host "临时目录: $TempDir" -ForegroundColor Yellow
    Pop-Location
    exit 1
}

Pop-Location

# 8. 清理临时目录（可选）
Write-Host "`n清理临时目录..." -ForegroundColor Yellow
$Cleanup = Read-Host "是否删除临时目录? (Y/N)"
if ($Cleanup -eq "Y" -or $Cleanup -eq "y") {
    Remove-Item -Recurse -Force $TempDir
    Write-Host "✅ 临时目录已清理" -ForegroundColor Green
} else {
    Write-Host "临时目录保留在: $TempDir" -ForegroundColor Yellow
}

Write-Host "`n=== 同步完成 ===" -ForegroundColor Green

