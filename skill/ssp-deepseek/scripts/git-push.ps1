# Git 提交推送脚本
# 
# 使用方法:
#   powershell -ExecutionPolicy Bypass -File git-push.ps1
#   或右键 -> 使用 PowerShell 运行

param(
    [string]$Message = "Update SSP DeepSeek config"
)

$REPO_PATH = "$env:USERPROFILE\openclaw-workspace"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git 提交推送工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查仓库
if (-not (Test-Path "$REPO_PATH\.git")) {
    Write-Host "✗ 错误: 未找到 Git 仓库: $REPO_PATH" -ForegroundColor Red
    exit 1
}

Set-Location $REPO_PATH

# 检查状态
Write-Host "检查 Git 状态..." -ForegroundColor Yellow
$status = git status --short

if (-not $status) {
    Write-Host "! 没有需要提交的更改" -ForegroundColor Yellow
    exit 0
}

Write-Host "待提交文件:" -ForegroundColor Gray
Write-Host $status -ForegroundColor Gray
Write-Host ""

# 确认
$response = Read-Host "确认提交? (y/n)"
if ($response -ne 'y' -and $response -ne 'Y') {
    Write-Host "已取消" -ForegroundColor Yellow
    exit 0
}

# 提交
Write-Host "正在提交..." -ForegroundColor Yellow
git add -A
git commit -m "$Message"

# 推送
Write-Host "正在推送到远程..." -ForegroundColor Yellow
git push

Write-Host ""
Write-Host "✓ 推送完成！" -ForegroundColor Green
Write-Host ""

# 显示日志
Write-Host "最近提交:" -ForegroundColor Gray
git log --oneline -3

Write-Host ""
Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
