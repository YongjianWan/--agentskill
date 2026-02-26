@echo off
chcp 65001 >nul
title 卸载会议管理系统自动启动任务

echo ================================================
echo   卸载会议管理系统自动启动任务
echo ================================================
echo.

REM 删除定时任务
schtasks /Delete /TN "MeetingManagementServer" /F 2>nul

if %errorlevel% equ 0 (
    echo [成功] 自动启动任务已删除。
) else (
    echo [信息] 任务不存在或已被删除。
)

echo.
echo ================================================
echo   卸载完成
echo ================================================
echo.
pause
