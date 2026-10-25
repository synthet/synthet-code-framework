$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
uv sync --extra dev
& (Join-Path $Root '.venv\Scripts\python.exe') -m jev_engineering.install_config apply
Write-Output 'OK install'
