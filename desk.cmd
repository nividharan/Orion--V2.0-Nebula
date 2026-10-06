@echo off
setlocal enabledelayedexpansion

REM Desk Automation & AGY CLI Unified Gateway
REM Location: c:\skill\desktop_controller.py

set PYTHON_SCRIPT=c:\skill\desktop_controller.py

if "%~1"=="" goto show_help

REM Check for built-in controller subcommands
set CMD=%~1
if /i "%CMD%"=="preflight" goto run_python
if /i "%CMD%"=="batch" goto run_python
if /i "%CMD%"=="launch" goto run_python
if /i "%CMD%"=="open" goto run_python
if /i "%CMD%"=="port" goto run_python
if /i "%CMD%"=="ports" goto run_python
if /i "%CMD%"=="check_port" goto run_python
if /i "%CMD%"=="apps" goto run_python
if /i "%CMD%"=="shot" goto run_shot
if /i "%CMD%"=="screenshot" goto run_python
if /i "%CMD%"=="click" goto run_python
if /i "%CMD%"=="hover" goto run_python
if /i "%CMD%"=="double_click" goto run_python
if /i "%CMD%"=="right_click" goto run_python
if /i "%CMD%"=="move" goto run_python
if /i "%CMD%"=="drag" goto run_python
if /i "%CMD%"=="scroll" goto run_python
if /i "%CMD%"=="pos" goto run_python
if /i "%CMD%"=="type" goto run_python
if /i "%CMD%"=="paste" goto run_python
if /i "%CMD%"=="press" goto run_python
if /i "%CMD%"=="hotkey" goto run_python
if /i "%CMD%"=="list_windows" goto run_python
if /i "%CMD%"=="windows" goto run_windows
if /i "%CMD%"=="active_window" goto run_python
if /i "%CMD%"=="focus" goto run_python
if /i "%CMD%"=="speak" goto run_python
if /i "%CMD%"=="status" (
    curl -s http://127.0.0.1:8765/status 2>nul
    if not errorlevel 1 goto end
    goto run_python
)
if /i "%CMD%"=="quick" (
    curl -s http://127.0.0.1:8765/quick_state 2>nul
    if not errorlevel 1 goto end
    goto run_python
)
if /i "%CMD%"=="shot" (
    curl -s http://127.0.0.1:8765/screen.jpg --output c:\skill\.cache\screen_live.png 2>nul
    if not errorlevel 1 (
        echo {"status": "ok", "saved_path": "c:\\skill\\.cache\\screen_live.png", "method": "api_in_memory"}
        goto end
    )
    goto run_shot
)
if /i "%CMD%"=="api" goto run_python
if /i "%CMD%"=="monitor" goto run_python
if /i "%CMD%"=="server" goto run_python
if /i "%CMD%"=="task" goto run_python
if /i "%CMD%"=="help" goto show_help
if /i "%CMD%"=="--help" goto show_help
if /i "%CMD%"=="-h" goto show_help

REM If not a direct controller subcommand, treat as natural language prompt to agy CLI
echo [desk] Delegating natural language command to agy AI agent...
agy -p "%*" --dangerously-skip-permissions
goto end

:run_shot
python "%PYTHON_SCRIPT%" screenshot %2 %3 %4 %5 %6
goto end

:run_windows
python "%PYTHON_SCRIPT%" list_windows
goto end

:run_python
python "%PYTHON_SCRIPT%" %*
goto end

:run_listen
echo [desk] Listening for voice command... (speak into microphone)
python -c "from desktop_controller import listen_and_transcribe; import os; res = os.system('python c:\\skill\\desktop_controller.py listen');"
goto end

:show_help
echo ==============================================================================
echo                DESK - Unified Autonomous Desktop & AGY CLI
echo ==============================================================================
echo Usage:
echo   desk "<natural language prompt>"     Run AI instruction via agy CLI
echo   desk preflight [apps...]             Validate software and environment
echo   desk batch --file steps.json         Execute continuous machine-speed pipeline
echo   desk focus ^<title^>                   Bring application window to front
echo   desk shot                            Capture live screen buffer (.cache/screen_live.png)
echo   desk click --x ^<x^> --y ^<y^>           Pixel-accurate verified click
echo   desk paste ^<text^>                    Fast clipboard-based Unicode paste
echo   desk speak ^<text^>                    Windows SAPI spoken voice response
echo   desk windows                         List active application windows
echo   desk pos                             Show current mouse coordinates
echo ==============================================================================
goto end

:end
