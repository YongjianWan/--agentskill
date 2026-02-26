@echo off
curl -s http://localhost:8765/api/v1/health >nul
if %errorlevel% == 0 (
    echo [Running] Meeting server is running on port 8765
) else (
    echo [Stopped] Meeting server is not running
)
