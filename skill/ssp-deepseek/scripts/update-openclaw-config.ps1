# SSP DeepSeek OpenClaw 配置自动更新脚本 (Windows PowerShell)
# 
# 使用方法:
#   1. 修改下面的 ACCESS_KEY 和 SECRET_KEY
#   2. 右键 -> 使用 PowerShell 运行
#   3. 或命令行: powershell -ExecutionPolicy Bypass -File update-openclaw-config.ps1

# ==================== 配置区域 ====================
$ACCESS_KEY = "08edc581c6"
$SECRET_KEY = "b059cf9148"

# OpenClaw 配置文件路径 (根据你的实际路径修改)
$OPENCLAW_CONFIG_PATH = "$env:USERPROFILE\.openclaw\openclaw.json"
# 或者如果你用的是自定义路径:
# $OPENCLAW_CONFIG_PATH = "C:\Users\你的用户名\.openclaw\openclaw.json"

# Git 仓库路径 (如果需要在更新后自动提交)
$GIT_REPO_PATH = "$env:USERPROFILE\openclaw-workspace"
# =================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SSP DeepSeek 配置自动更新工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python 版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ 错误: 未找到 Python，请先安装 Python" -ForegroundColor Red
    exit 1
}

# 检查依赖
try {
    python -c "import gmssl, requests" 2>$null
    Write-Host "✓ 依赖检查通过 (gmssl, requests)" -ForegroundColor Green
} catch {
    Write-Host "! 正在安装依赖..." -ForegroundColor Yellow
    pip install gmssl requests
}

Write-Host ""
Write-Host "正在获取长期 Token..." -ForegroundColor Yellow

# 创建临时 Python 脚本获取 Token
# 使用字符串拼接来正确展开 PowerShell 变量
$tempScript = @"
import sys
sys.path.insert(0, '$($PSScriptRoot)\..')
from src.auth import SSPAuth

try:
    auth = SSPAuth('$ACCESS_KEY', '$SECRET_KEY')
    token = auth.get_token()
    print(token)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
"@

$tempFile = [System.IO.Path]::GetTempFileName()
$tempScriptPath = [System.IO.Path]::ChangeExtension($tempFile, ".py")
Remove-Item $tempFile -ErrorAction SilentlyContinue
[System.IO.File]::WriteAllText($tempScriptPath, $tempScript, [System.Text.Encoding]::UTF8)

try {
    $TOKEN = python $tempScriptPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "获取 Token 失败: $TOKEN"
    }
    if ($TOKEN -and $TOKEN.Length -gt 0) {
        $displayToken = if ($TOKEN.Length -gt 20) { $TOKEN.Substring(0, 20) } else { $TOKEN }
        Write-Host "✓ 获取 Token 成功: $displayToken..." -ForegroundColor Green
    } else {
        throw "获取的 Token 为空"
    }
} finally {
    Remove-Item $tempScriptPath -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "正在更新 OpenClaw 配置..." -ForegroundColor Yellow
Write-Host "配置文件路径: $OPENCLAW_CONFIG_PATH" -ForegroundColor Gray

# 检查配置文件是否存在
if (-not (Test-Path $OPENCLAW_CONFIG_PATH)) {
    Write-Host "✗ 错误: 找不到配置文件 $OPENCLAW_CONFIG_PATH" -ForegroundColor Red
    Write-Host "  请确认路径是否正确，或手动创建配置文件" -ForegroundColor Yellow
    exit 1
}

# 读取配置文件
$configContent = Get-Content $OPENCLAW_CONFIG_PATH -Raw -Encoding UTF8

# 检查是否已有 ssp-deepseek 配置
$sspPattern = '"ssp-deepseek"\s*:\s*\{'
$hasSspConfig = $configContent -match $sspPattern

if ($hasSspConfig) {
    # 更新现有配置中的 apiKey
    # 匹配 ssp-deepseek 区块内的 apiKey
    $pattern = '("ssp-deepseek"[\s\S]*?"apiKey"\s*:\s*")([^"]*)(")'
    $replacement = "`${1}$TOKEN`${3}"
    $newContent = $configContent -replace $pattern, $replacement
    
    if ($newContent -eq $configContent) {
        Write-Host "! 未找到需要更新的 apiKey，尝试添加新配置..." -ForegroundColor Yellow
        $hasSspConfig = $false
    } else {
        Write-Host "✓ 已更新现有配置的 apiKey" -ForegroundColor Green
    }
}

if (-not $hasSspConfig) {
    # 添加新的 ssp-deepseek 配置
    $newConfig = @"
    "ssp-deepseek": {
      "baseUrl": "https://www.ssfssp.com:8888/ssp/openApi/GkfFhhUy/kvshB4Rh/LNslKxsF",
      "apiKey": "$TOKEN",
      "api": "openai-completions",
      "models": [
        {
          "id": "DeepSeek-V3",
          "name": "SSP DeepSeek V3",
          "contextWindow": 64000,
          "maxTokens": 8192
        }
      ]
    }
"@
    
    # 在 models.providers 中添加
    if ($configContent -match '"providers"\s*:\s*\{') {
        # 在 providers 的 { 后面插入
        $pattern = '("providers"\s*:\s*\{)'
        $replacement = "`${1}`n$newConfig,"
        $newContent = $configContent -replace $pattern, $replacement
    } else {
        # 如果没有 providers，在 models 后面添加
        $newConfig = @"
  "models": {
    "providers": {
$newConfig
    }
  }
"@
        $pattern = '("models"\s*:\s*\{[^}]*\})'
        $replacement = $newConfig
        $newContent = $configContent -replace $pattern, $replacement
    }
    
    Write-Host "✓ 已添加新的 ssp-deepseek 配置" -ForegroundColor Green
}

# 备份原配置
$backupPath = "$OPENCLAW_CONFIG_PATH.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $OPENCLAW_CONFIG_PATH $backupPath
Write-Host "✓ 原配置已备份到: $backupPath" -ForegroundColor Green

# 写入新配置
[System.IO.File]::WriteAllText($OPENCLAW_CONFIG_PATH, $newContent, [System.Text.Encoding]::UTF8)
Write-Host "✓ 配置已更新" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "配置更新完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
if ($TOKEN -and $TOKEN.Length -gt 0) {
    $displayToken = if ($TOKEN.Length -gt 30) { $TOKEN.Substring(0, 30) } else { $TOKEN }
    Write-Host "Token: $displayToken..." -ForegroundColor Gray
}
Write-Host ""

# Git 提交（可选）
if (Test-Path "$GIT_REPO_PATH\.git") {
    $response = Read-Host "是否提交到 Git? (y/n)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host "正在提交到 Git..." -ForegroundColor Yellow
        
        Set-Location $GIT_REPO_PATH
        
        # 检查是否有更改
        $gitStatus = git status --porcelain 2>$null
        if ($gitStatus) {
            git add -A
            git commit -m "Update SSP DeepSeek config with new token"
            git push
            Write-Host "✓ 已推送到 Git" -ForegroundColor Green
        } else {
            Write-Host "! 没有需要提交的更改" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "! 未找到 Git 仓库，跳过提交" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
