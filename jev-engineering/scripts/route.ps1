param(
    [Parameter(Mandatory = $true)][string]$Task,
    [string]$CurrentModel = 'opus',
    [int]$ContextTokens = 0,
    [int]$OutputTokens = 0,
    [int]$ReadTokens = 0,
    [switch]$Live
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not $Live) { $env:JEV_MOCK = '1' }
& $Python -m jev_engineering.cli route --task $Task --current-model $CurrentModel --context-tokens $ContextTokens --output-tokens $OutputTokens --read-tokens $ReadTokens
exit $LASTEXITCODE
