$ErrorActionPreference = 'Continue'
$root = 'D:\Projects\_agent-infra\jev'
$py = Join-Path $root '.venv\Scripts\python.exe'
$fallback = '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Jev engineering hook unavailable. Continue with local files and existing permission rules."}}'
try {
    $raw = [Console]::In.ReadToEnd()
    if (-not (Test-Path -LiteralPath $py)) {
        Write-Output $fallback
        exit 0
    }
    $env:JEV_ENGINEERING_ROOT = $root
    $output = $raw | & $py -m jev_engineering.hook prompt
    if ($output) { Write-Output $output } else { Write-Output $fallback }
} catch {
    Write-Output $fallback
}
exit 0
