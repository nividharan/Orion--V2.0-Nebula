@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM Orion v2.0 "Nebula" - Universal Autonomous Desktop & Perception Engine
REM ==============================================================================

set PYTHON_SCRIPT=c:\skill\desktop_controller.py

if "%~1"=="" goto show_help

set CMD=%~1

REM In-Memory Fast Paths via Port 8765
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
        echo {"status": "ok", "saved_path": "c:\\skill\\.cache\\screen_live.png", "method": "orion_in_memory"}
        goto end
    )
    goto run_shot
)

REM Standard Controller Subcommands
if /i "%CMD%"=="version" goto run_python
if /i "%CMD%"=="--version" goto run_python
if /i "%CMD%"=="-v" goto run_python
if /i "%CMD%"=="preflight" goto run_python
if /i "%CMD%"=="batch" goto run_python
if /i "%CMD%"=="launch" goto run_python
if /i "%CMD%"=="open" goto run_python
if /i "%CMD%"=="port" goto run_python
if /i "%CMD%"=="ports" goto run_python
if /i "%CMD%"=="check_port" goto run_python
if /i "%CMD%"=="apps" goto run_python
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
if /i "%CMD%"=="transcribe" goto run_python
if /i "%CMD%"=="api" goto run_python
if /i "%CMD%"=="monitor" goto run_python
if /i "%CMD%"=="server" goto run_python
if /i "%CMD%"=="task" goto run_python
if /i "%CMD%"=="help" goto show_help
if /i "%CMD%"=="--help" goto show_help
if /i "%CMD%"=="-h" goto show_help

REM Natural language AI delegation to agy CLI
echo [Orion v2.0 Nebula] Delegating command to Antigravity AI Agent...
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

:show_help
echo ==============================================================================
echo           ORION v2.0 "Nebula" - Universal Autonomous Desktop Engine
echo ==============================================================================
echo Usage:
echo   orion "<natural language prompt>"    Execute autonomous task via Antigravity CLI
echo   orion quick                          Instant 6ms workstation telemetry
echo   orion status                         Full real-time system status and motion delta
echo   orion shot                           Ultra-fast in-memory screen capture
echo   orion focus ^<title^>                  Restore and bring application window to front
echo   orion task --file ^<task.json^>        Execute closed-loop 5-stage task runner
echo   orion preflight [apps...]            Validate software, ports and environment
echo   orion apps [filter]                  Discover all 209 installed Windows applications
echo   orion ports                          Scan listening TCP ports in 0.05s
echo   orion open ^<app^>                     Launch application with visible window guard
echo   orion api [--port 8765]              Start continuous Perception API server
echo ==============================================================================
goto end

:end
