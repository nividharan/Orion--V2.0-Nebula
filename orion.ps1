param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$PythonScript = "c:\skill\desktop_controller.py"
$ApiBase = "http://127.0.0.1:8765"

$AutoGenScript = "c:\skill\orion_autogen.py"

if (-not $ArgsList -or $ArgsList.Count -eq 0) {
    & python $PythonScript --help
    return
}

$firstArg = $ArgsList[0].ToLower()

if ($firstArg -in @("team", "run", "workflow", "autogen")) {
    $teamPrompt = ($ArgsList[1..($ArgsList.Count - 1)] -join " ").Trim()
    & python $AutoGenScript $teamPrompt
    return
}

if ($firstArg -in @("console", "shell", "interactive", "terminal")) {
    & python $PythonScript console
    return
}

if ($firstArg -in @("help", "--help", "-h")) {
    & python $PythonScript --help
    return
}

# ==============================================================================
# ORION v2.0 NEBULA - IN-MEMORY FAST PATHS (<20ms)
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
        [PSCustomObject]@{ status = "ok"; saved_path = $savePath; method = "orion_in_memory" } | ConvertTo-Json
        return
    } catch {}
}

if ($firstArg -eq "focus" -and $ArgsList.Count -ge 2) {
    try {
        $title = ($ArgsList[1..($ArgsList.Count - 1)] -join " ").Replace("--title", "").Trim()
        $body = @{ action = "focus"; title = $title } | ConvertTo-Json
        $res = Invoke-RestMethod -Uri "$ApiBase/action" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 2 -ErrorAction Stop
        $res | ConvertTo-Json -Depth 5
        return
    } catch {}
}

if ($firstArg -eq "speak" -and $ArgsList.Count -ge 2) {
    try {
        $rawMsg = ($ArgsList[1..($ArgsList.Count - 1)] -join " ")
        $voiceChoice = "George"
        if ($rawMsg -match '(?:--voice|-v)\s+([a-zA-Z]+)') {
            $voiceChoice = $Matches[1]
            $rawMsg = $rawMsg -replace '(?:--voice|-v)\s+[a-zA-Z]+', ''
        }
        $msg = $rawMsg.Replace("--text", "").Trim()
        $body = @{ action = "speak"; text = $msg; voice = $voiceChoice } | ConvertTo-Json
        $res = Invoke-RestMethod -Uri "$ApiBase/action" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
        $res | ConvertTo-Json -Depth 5
        return
    } catch {}
}

if ($firstArg -in @("voices", "list_voices")) {
    try {
        $res = Invoke-RestMethod -Uri "$ApiBase/voices" -TimeoutSec 2 -ErrorAction Stop
        $res | ConvertTo-Json -Depth 5
        return
    } catch {}
}

if ($firstArg -in @("browse", "search", "web") -and $ArgsList.Count -ge 2) {
    try {
        $query = ($ArgsList[1..($ArgsList.Count - 1)] -join " ").Trim()
        $browserChoice = $null
        if ($query -match '^(?:--browser|-b)\s+(chrome|edge)\s+(.*)$') {
            $browserChoice = $Matches[1]
            $query = $Matches[2].Trim()
        }
        $body = @{ action = "browse"; query = $query; browser = $browserChoice } | ConvertTo-Json
        $res = Invoke-RestMethod -Uri "$ApiBase/action" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 2 -ErrorAction Stop
        $res | ConvertTo-Json -Depth 5
        return
    } catch {}
}

if ($firstArg -eq "task" -and $ArgsList.Count -ge 3 -and $ArgsList[1] -eq "--file") {
    try {
        $filePath = $ArgsList[2]
        if (Test-Path $filePath) {
            $jsonContent = Get-Content $filePath -Raw -Encoding UTF8
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
    "version", "--version", "-v",
    "preflight", "batch", "launch", "open", "port", "ports", "check_port", "apps",
    "browse", "search", "web",
    "shot", "screenshot", "click", "hover", 
    "double_click", "right_click", "move", "drag", "scroll", "pos", 
    "type", "paste", "press", "hotkey", "list_windows", "windows", 
    "active_window", "focus", "speak", "voices", "list_voices", "transcribe", "listen", "record",
    "status", "api", "monitor", "server", "task"
)

if ($firstArg -in $controllerCmds) {
    & python $PythonScript @ArgsList
    return
}

# ==============================================================================
# LOCAL INTENT ROUTER (REGEX FAST-PATHS BEFORE AI AGENT FALLBACK)
# ==============================================================================

$rawPrompt = ($ArgsList -join " ").Trim()

# Compound multi-step goal -> route to AutoGen Multi-Agent collaborative society!
if ($rawPrompt -match '\b(?:and|then)\b') {
    & python $AutoGenScript $rawPrompt
    return
}

# 1. Browser Commands: open/browse/search/goto (chrome|edge|browser)? <url or query>
if ($rawPrompt -match '^(?:open|browse|search|goto|go\s+to)\s+(?:in\s+)?(?:(chrome|edge|browser)\s+)?(?:for\s+)?(.+)$') {
    $matchedBrowser = if ($Matches[1] -and $Matches[1] -ne "browser") { $Matches[1] } else { $null }
    $matchedQuery = $Matches[2].Trim()

    $knownApps = @("notepad", "calc", "calculator", "blender", "paint", "cmd", "powershell", "code", "vscode", "explorer")
    if (-not $matchedBrowser -and ($matchedQuery.ToLower() -in $knownApps)) {
        try {
            $body = @{ action = "open"; app = $matchedQuery } | ConvertTo-Json
            $res = Invoke-RestMethod -Uri "$ApiBase/action" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 2 -ErrorAction Stop
            $res | ConvertTo-Json -Depth 5
            return
        } catch {
            & python $PythonScript launch $matchedQuery
            return
        }
    }

    try {
        $body = @{ action = "browse"; query = $matchedQuery; browser = $matchedBrowser } | ConvertTo-Json
        $res = Invoke-RestMethod -Uri "$ApiBase/action" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 2 -ErrorAction Stop
        $res | ConvertTo-Json -Depth 5
        return
    } catch {
        $bArgs = @("browse", $matchedQuery)
        if ($matchedBrowser) { $bArgs += @("--browser", $matchedBrowser) }
        & python $PythonScript @bArgs
        return
    }
}

# 2. App Launch: open/launch/start <app>
if ($rawPrompt -match '^(?:open|launch|start)\s+([a-zA-Z0-9_\-\.\s]+)$') {
    $appName = $Matches[1].Trim()
    try {
        $body = @{ action = "open"; app = $appName } | ConvertTo-Json
        $res = Invoke-RestMethod -Uri "$ApiBase/action" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 2 -ErrorAction Stop
        $res | ConvertTo-Json -Depth 5
        return
    } catch {
        & python $PythonScript launch $appName
        return
    }
}

# 3. Window Focus: focus/switch to/bring up <window_title>
if ($rawPrompt -match '^(?:focus|switch\s+to|bring\s+up)\s+(.+)$') {
    $targetTitle = $Matches[1].Trim()
    try {
        $body = @{ action = "focus"; title = $targetTitle } | ConvertTo-Json
        $res = Invoke-RestMethod -Uri "$ApiBase/action" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 2 -ErrorAction Stop
        $res | ConvertTo-Json -Depth 5
        return
    } catch {
        & python $PythonScript focus $targetTitle
        return
    }
}

# 4. Voice TTS: speak/say/tts <message>
if ($rawPrompt -match '^(?:speak|say|tts)\s+(.+)$') {
    $msg = $Matches[1].Trim()
    try {
        $body = @{ action = "speak"; text = $msg } | ConvertTo-Json
        $res = Invoke-RestMethod -Uri "$ApiBase/action" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 2 -ErrorAction Stop
        $res | ConvertTo-Json -Depth 5
        return
    } catch {
        & python $PythonScript speak $msg
        return
    }
}

# ==============================================================================
# NATURAL LANGUAGE MULTI-AGENT COLLABORATION (AUTOGEN TEAM)
# ==============================================================================

& python $AutoGenScript $rawPrompt
return
