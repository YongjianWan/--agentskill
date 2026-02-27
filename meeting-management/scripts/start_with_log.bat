@echo off
chcp 65001 >nul
cd /d "%~dp0\..\src"

:: 方式1: 直接输出到控制台（推荐，实时看到日志）
python -m uvicorn main:app --host 0.0.0.0 --port 8765

:: 方式2: 如果想同时保存到文件（无缓冲）
:: python -m uvicorn main:app --host 0.0.0.0 --port 8765 2>&1 | python -c "import sys; [print(line, end='') or open('../backend_realtime.log','a',encoding='utf-8').write(line) for line in sys.stdin]"
