@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM Orion System × Nebula Model (v2.0) - Cognitive Model CLI (Chrome Operations)
REM ==============================================================================

if "%~1"=="" (
    python "%~dp0orion_autogen.py" help
    exit /b 0
)

python "%~dp0orion_autogen.py" %*
