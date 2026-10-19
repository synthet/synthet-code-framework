---
type: Guide
title: Windows Agent CLI Recipes
description: Recipes for the Windows agent command names, so agent launches Cursor and grok
  launches Grok.
resource: guides/windows-agent-cli-recipes-2026-10-18.md
tags:
- docs
- agent-tooling
- cursor
- grok
- windows
timestamp: 2026-10-18 00:00:00+00:00
okf_version: 0.1
---

# Windows agent CLI recipes

One Windows PC has both the Grok CLI and the Cursor agent CLI. Both install a command named
`agent`. These recipes make `agent` launch Cursor and leave `grok` as the Grok command. Paths use
`~` for the user profile.

## What each name is

| Command | Winner when PATH is correct | File |
|---|---|---|
| `agent` | Cursor agent CLI | `%LOCALAPPDATA%\cursor-agent\agent.ps1` (PowerShell) and `agent.cmd` (Command Prompt) |
| `cursor-agent` | Cursor agent CLI, no name clash | `%LOCALAPPDATA%\cursor-agent\cursor-agent.ps1` |
| `grok` | Grok CLI | `~/.grok/bin/grok.exe` |

`~/.grok/bin/agent.exe` is the same binary as `grok.exe`. Grok installs it under both names. Cursor
does not ship an `agent.exe`.

## Recipe 1 — `agent` launches Cursor, `grok` stays Grok

Symptom: `agent` opens Grok. `Get-Command agent` and `where.exe agent` both list
`~/.grok/bin/agent.exe` first. Cursor's folder is also on the user PATH, later:

```text
~\.grok\bin\agent.exe
%LOCALAPPDATA%\cursor-agent\agent.cmd
```

Windows searches PATH in order. `PATHEXT` tries `.EXE` before `.CMD`. Whichever directory comes
first supplies `agent`.

Fix: in the **user** PATH, put `%LOCALAPPDATA%\cursor-agent` immediately ahead of `~\.grok\bin`.
Do not rename or delete `grok.exe`. Leave `agent.exe` in place; it stays available by full path
and loses the bare name only because its directory is no longer first.

```powershell
$cursor = Join-Path $env:LOCALAPPDATA 'cursor-agent'
$grok = Join-Path $env:USERPROFILE '.grok\bin'
$parts = @([Environment]::GetEnvironmentVariable('Path', 'User') -split ';' | Where-Object { $_ -ne '' })
$beforeCount = $parts.Count
$filtered = @($parts | Where-Object { $_.TrimEnd('\') -ine $cursor })
$list = New-Object System.Collections.Generic.List[string]
$inserted = $false
foreach ($p in $filtered) {
    if (-not $inserted -and ($p.TrimEnd('\') -ieq $grok)) {
        $list.Add($cursor)
        $inserted = $true
    }
    $list.Add($p)
}
if (-not $inserted) { $list.Insert(0, $cursor) }
if ($list.Count -ne $beforeCount) { throw "PATH entry count changed: $beforeCount -> $($list.Count)" }
[Environment]::SetEnvironmentVariable('Path', ($list -join ';'), 'User')
```

The script removes any earlier copy of the Cursor folder, then inserts one copy directly before
`~\.grok\bin`. Entry count must stay the same. If `~\.grok\bin` is missing, the Cursor folder goes
first.

Check, using a path built from the registry (an already-open terminal still has the old PATH):

```powershell
$fresh = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
pwsh -NoProfile -Command "`$env:PATH = @'`n$fresh`n'@; Write-Host (Get-Command agent).Source; Write-Host (Get-Command grok).Source"
```

Expected:

- `agent` → `%LOCALAPPDATA%\cursor-agent\agent.ps1`
- `grok` → `~\.grok\bin\grok.exe`

Command Prompt runs `%LOCALAPPDATA%\cursor-agent\agent.cmd`. `where agent` may still list
`~\.grok\bin\agent.exe` on a later line. The first line is the one that runs.

Open a new terminal before trying `agent`. A later Grok update can put `~\.grok\bin` first again.
If `agent` starts opening Grok after an update, run this recipe again.
