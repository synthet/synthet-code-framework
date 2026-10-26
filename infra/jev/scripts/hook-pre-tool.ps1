$ErrorActionPreference = 'Continue'
$root = 'D:\Projects\_agent-infra\jev'
$py = Join-Path $root '.venv\Scripts\python.exe'
$fallbackClaude = '{}'
$fallbackCursor = '{"permission":"ask","user_message":"jev-engineering unavailable","agent_message":"jev-engineering unavailable"}'
$raw = ''

function Get-HookFallback([string]$text) {
    if ($text -match '"conversation_id"|"generation_id"|"hook_event_name"\s*:\s*"(preToolUse|postToolUse|beforeShellExecution|beforeMCPExecution|beforeReadFile|afterFileEdit)"') {
        return $fallbackCursor
    }
    return $fallbackClaude
}

try {
    $raw = [Console]::In.ReadToEnd()
    if (-not (Test-Path -LiteralPath $py)) {
        Write-Output (Get-HookFallback $raw)
        exit 0
    }
    $env:JEV_ENGINEERING_ROOT = $root
    $output = $raw | & $py -m jev_engineering.hook pre-tool
    if ($output) { Write-Output $output } else { Write-Output (Get-HookFallback $raw) }
} catch {
    Write-Output (Get-HookFallback $raw)
}
exit 0
