@echo off
title Orion v2.0 Nebula Launcher
echo ===================================================
echo   Starting Orion v2.0 "Nebula" Dashboard...
echo ===================================================

:: Check if API server on port 8765 is already responding
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8765/quick_state' -TimeoutSec 1 -UseBasicParsing; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% NEQ 0 (
    echo Starting Orion background daemon on port 8765...
    start /b pythonw c:\skill\desktop_controller.py api --port 8765
    timeout /t 2 /nobreak >nul
)

echo Opening Orion Web Dashboard in your browser...
start http://localhost:8765/
exit
