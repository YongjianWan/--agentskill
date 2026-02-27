# Nginx 统一入口检查脚本 (Windows版)
# 在 192.168.106.66 服务器上执行

Write-Host "========== 1. 检查 Nginx 进程 ==========" -ForegroundColor Green
Get-Process nginx -ErrorAction SilentlyContinue | Select-Object ProcessName, Id, CPU

Write-Host ""
Write-Host "========== 2. 检查端口监听 ==========" -ForegroundColor Green
netstat -ano | findstr :80

Write-Host ""
Write-Host "========== 3. 检查会议后端连通性 (172.20.3.70:8765) ==========" -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://172.20.3.70:8765/api/v1/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "状态码: $($response.StatusCode) ✅" -ForegroundColor Green
    Write-Host "响应内容: $($response.Content)"
} catch {
    Write-Host "连接失败 ❌: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========== 4. 检查 Django 连通性 (127.0.0.1:8000) ==========" -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "状态码: $($response.StatusCode) ✅" -ForegroundColor Green
} catch {
    Write-Host "连接失败 ❌: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========== 5. 测试统一入口 - 会议API ==========" -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://192.168.106.66/api/meetings/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "状态码: $($response.StatusCode) ✅" -ForegroundColor Green
    Write-Host "后端Header: $($response.Headers['X-Debug-Backend'])"
} catch {
    Write-Host "请求失败 ❌: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========== 6. Nginx 配置文件检查 ==========" -ForegroundColor Green
$nginxConfPaths = @(
    "C:\nginx\conf\nginx.conf",
    "C:\Program Files\nginx\conf\nginx.conf",
    "D:\nginx\conf\nginx.conf"
)

foreach ($path in $nginxConfPaths) {
    if (Test-Path $path) {
        Write-Host "找到配置: $path" -ForegroundColor Green
        Write-Host "--- 会议管理location配置 ---"
        Get-Content $path | Select-String -Pattern "location /api/meetings" -Context 0,5
        break
    }
}

Write-Host ""
Write-Host "========== 检查完成 ==========" -ForegroundColor Cyan
