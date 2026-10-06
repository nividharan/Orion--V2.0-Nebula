@echo off
title Orion v2.0 Nebula Terminal Console
echo ===================================================
echo   Starting Orion v2.0 "Nebula" in Terminal...
echo ===================================================
cd /d "%~dp0"
python "%~dp0desktop_controller.py" console
pause
