$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
& $Python -m jev_engineering.install_config rollback
exit $LASTEXITCODE
