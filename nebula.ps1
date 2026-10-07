param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

# ==============================================================================
# Orion System × Nebula Model (v2.0) - Cognitive Model CLI (Chrome Operations)
# ==============================================================================

$AutoGenScript = "c:\skill\orion_autogen.py"

if (-not $ArgsList -or $ArgsList.Count -eq 0) {
    & python $AutoGenScript help
    return
}

$firstArg = $ArgsList[0].ToLower()
if ($firstArg -in @("help", "--help", "-h")) {
    & python $AutoGenScript help
    return
}

$prompt = ($ArgsList -join " ").Trim()
& python $AutoGenScript $prompt
