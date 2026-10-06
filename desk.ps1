param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$PythonScript = "c:\skill\desktop_controller.py"

if (-not $ArgsList -or $ArgsList.Count -eq 0) {
    & cmd /c "$PSScriptRoot\desk.cmd help"
    return
}

$firstArg = $ArgsList[0].ToLower()
$controllerCmds = @(
    "preflight", "batch", "launch", "open", "port", "ports", "check_port", "apps",
    "shot", "screenshot", "click", "hover", 
    "double_click", "right_click", "move", "drag", "scroll", "pos", 
    "type", "paste", "press", "hotkey", "list_windows", "windows", 
    "active_window", "focus", "speak", "transcribe", "listen"
)

if ($firstArg -in @("help", "--help", "-h")) {
    & cmd /c "$PSScriptRoot\desk.cmd help"
    return
}

if ($firstArg -in $controllerCmds) {
    & python $PythonScript @ArgsList
    return
}

# Otherwise delegate to agy CLI with natural language prompt
$fullPrompt = $ArgsList -join " "
Write-Host "[desk] Delegating natural language command to agy AI agent: $fullPrompt" -ForegroundColor Green
& agy -p $fullPrompt --dangerously-skip-permissions
