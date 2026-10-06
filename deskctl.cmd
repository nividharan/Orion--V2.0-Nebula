@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM Orion v2.0 "Nebula" - Universal Autonomous Desktop & Perception Engine
REM ==============================================================================

if "%~1"=="" (
    python c:\skill\desktop_controller.py --help
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0orion.ps1" %*
