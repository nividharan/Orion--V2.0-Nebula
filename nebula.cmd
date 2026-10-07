@echo off
if "%~1"=="" (
    python "%~dp0orion_autogen.py" help
    exit /b 0
)
python "%~dp0orion_autogen.py" %*
