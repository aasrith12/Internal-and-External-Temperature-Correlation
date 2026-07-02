@echo off
cd /d "%~dp0"
start "Temperature Dashboard Server" cmd /k python dashboard\server.py
timeout /t 2 >nul
start "" http://127.0.0.1:8765/dashboard/index.html
