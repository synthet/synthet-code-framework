$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    uv sync --extra dev
}
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'docs') | Out-Null
$Help = Join-Path $Root 'docs\harness-help.txt'
Remove-Item -LiteralPath $Help -ErrorAction SilentlyContinue
function Add-Help([string]$Title, [scriptblock]$Block) {
    Add-Content -LiteralPath $Help -Value ("## " + $Title)
    try {
        $text = & $Block | Out-String
    } catch {
        $text = $_.Exception.Message
    }
    Add-Content -LiteralPath $Help -Value $text
}
Add-Help 'claude' { & "$env:USERPROFILE\.local\bin\claude.exe" --version }
$Codex = 'C:\Users\dmnsy\AppData\Local\OpenAI\Codex\bin\896a0166b774037a\codex.exe'
Add-Help 'codex' { & $Codex --version }
Add-Help 'codex-help' { & $Codex --help }
Add-Help 'cursor' { cursor --version }
Add-Help 'agent' { agent --help }
Add-Help 'agy' { agy --help }
Add-Help 'gemini' { gemini --version }
Write-Output '--- pytest ---'
& $Python -m pytest
$Pytest = $LASTEXITCODE
Write-Output '--- mcp ---'
& $Python (Join-Path $Root 'scripts\mcp_handshake.py')
$Mcp = $LASTEXITCODE
Write-Output '--- live ---'
& $Python (Join-Path $Root 'scripts\live_smoke.py')
Write-Output '--- route ---'
& (Join-Path $Root 'scripts\route.ps1') -Task 'add a docstring to the parser'
if ($Pytest -ne 0 -or $Mcp -ne 0) { exit 1 }
Write-Output 'OK verify'
exit 0
