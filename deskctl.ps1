param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$PythonScript = "c:\skill\desktop_controller.py"
$ApiBase = "http://127.0.0.1:8765"

if (-not $ArgsList -or $ArgsList.Count -eq 0) {
    & cmd /c "$PSScriptRoot\desk.cmd help"
    return
}

$firstArg = $ArgsList[0].ToLower()

if ($firstArg -in @("help", "--help", "-h")) {
    & cmd /c "$PSScriptRoot\desk.cmd help"
    return
}

# ==============================================================================
# ULTRA-LOW-LATENCY FAST PATH VIA RUNNING API SERVER (<50ms)
# ==============================================================================

if ($firstArg -eq "status") {
    try {
        $res = Invoke-RestMethod -Uri "$ApiBase/status" -TimeoutSec 1 -ErrorAction Stop
        $res | ConvertTo-Json -Depth 5
        return
    } catch {}
}

if ($firstArg -in @("quick", "telemetry")) {
    try {
        $res = Invoke-RestMethod -Uri "$ApiBase/quick_state" -TimeoutSec 1 -ErrorAction Stop
        $res | ConvertTo-Json -Depth 5
        return
    } catch {}
}

if ($firstArg -in @("shot", "screenshot")) {
    try {
        $savePath = if ($ArgsList.Count -ge 2) { $ArgsList[1] } else { "c:\skill\.cache\screen_live.png" }
        Invoke-WebRequest -Uri "$ApiBase/screen.jpg" -OutFile $savePath -TimeoutSec 2 -ErrorAction Stop
        [PSCustomObject]@{ status = "ok"; saved_path = $savePath; method = "api_in_memory" } | ConvertTo-Json
        return
    } catch {}
}

if ($firstArg -eq "focus" -and $ArgsList.Count -ge 2) {
    try {
        $title = $ArgsList[1]
        if ($title -eq "--title" -and $ArgsList.Count -ge 3) { $title = $ArgsList[2] }
        $body = @{ action = "focus"; title = $title } | ConvertTo-Json
        $res = Invoke-RestMethod -Uri "$ApiBase/action" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 2 -ErrorAction Stop
        $res | ConvertTo-Json -Depth 5
        return
    } catch {}
}

if ($firstArg -eq "task" -and $ArgsList.Count -ge 3 -and $ArgsList[1] -eq "--file") {
    try {
        $filePath = $ArgsList[2]
        if (Test-Path $filePath) {
            $jsonContent = Get-Content $filePath -Raw
            $res = Invoke-RestMethod -Uri "$ApiBase/task" -Method POST -Body $jsonContent -ContentType "application/json" -TimeoutSec 30 -ErrorAction Stop
            $res | ConvertTo-Json -Depth 5
            return
        }
    } catch {}
}

# ==============================================================================
# STANDARD CONTROLLER COMMANDS
# ==============================================================================

$controllerCmds = @(
    "preflight", "batch", "launch", "open", "port", "ports", "check_port", "apps",
    "shot", "screenshot", "click", "hover", 
    "double_click", "right_click", "move", "drag", "scroll", "pos", 
    "type", "paste", "press", "hotkey", "list_windows", "windows", 
    "active_window", "focus", "speak", "transcribe", "listen",
    "status", "api", "monitor", "server", "task"
)

if ($firstArg -in $controllerCmds) {
    & python $PythonScript @ArgsList
    return
}

# ==============================================================================
# NATURAL LANGUAGE AGENT DELEGATION (AGY CLI)
# ==============================================================================

$fullPrompt = $ArgsList -join " "
Write-Host "[desk] Delegating command to Antigravity AI Agent: $fullPrompt" -ForegroundColor Green
& agy -p $fullPrompt --dangerously-skip-permissions
