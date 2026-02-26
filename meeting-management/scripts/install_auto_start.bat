@echo off
chcp 65001 >nul
title 安装会议管理系统自动启动任务

echo ================================================
echo   安装会议管理系统自动启动任务
echo ================================================
echo.

REM 设置项目路径
set "PROJECT_ROOT=c:\Users\sdses\Desktop\神思\ai孪生\agentp平台skill\meeting-management"
set "VBS_PATH=%PROJECT_ROOT%\scripts\start_server_silent.vbs"

REM 检查 VBS 文件是否存在
if not exist "%VBS_PATH%" (
    echo [错误] 找不到文件: %VBS_PATH%
    echo 请确保项目路径正确。
    pause
    exit /b 1
)

echo [信息] 项目路径: %PROJECT_ROOT%
echo [信息] 启动脚本: %VBS_PATH%
echo.

REM 删除已存在的任务（如果存在）
schtasks /Delete /TN "MeetingManagementServer" /F 2>nul

REM 创建新的定时任务
REM /TN: 任务名称
REM /TR: 要运行的程序
REM /SC: 触发器类型 (ONSTART = 系统启动时)
REM /DELAY: 延迟时间 0000:30 = 30秒
REM /RU: 运行用户 (%USERNAME% = 当前用户)
REM /RL: 运行级别 (HIGHEST = 最高权限)
REM /F: 强制覆盖
schtasks /Create ^
    /TN "MeetingManagementServer" ^
    /TR "\"%VBS_PATH%\"" ^
    /SC ONSTART ^
    /DELAY 0000:30 ^
    /RU %USERNAME% ^
    /RL HIGHEST ^
    /F

if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo   [成功] 自动启动任务安装完成！
    echo ================================================
    echo.
    echo 任务详情:
    echo   - 任务名称: MeetingManagementServer
    echo   - 触发器: 系统启动时
    echo   - 延迟: 30秒（等待网络就绪）
    echo   - 运行用户: %USERNAME%
    echo   - 运行脚本: %VBS_PATH%
    echo.
    echo 您可以使用以下命令管理任务:
    echo   - 查看任务: schtasks /Query /TN "MeetingManagementServer"
    echo   - 手动运行: schtasks /Run /TN "MeetingManagementServer"
    echo   - 删除任务: schtasks /Delete /TN "MeetingManagementServer" /F
    echo.
) else (
    echo.
    echo ================================================
    echo   [失败] 安装自动启动任务时出错！
    echo ================================================
    echo.
    echo 请以管理员身份运行此脚本。
    echo.
)

pause
