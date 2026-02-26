@echo off
chcp 65001 >nul
cd /d "%~dp0\..\src"
echo Starting Meeting Management Server...
python -m uvicorn main:app --host 0.0.0.0 --port 8765
