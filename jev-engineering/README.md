# Jev engineering

Published snapshot of the local checkout at `D:\Projects\_agent-infra\jev`. The same tree is in `synthet/jev-mcp` under `engineering/`, which is the package home. Harness MCP entries still launch the local checkout.

Local typed decision layer for Claude Code, Codex, Cursor, and Antigravity.

Jev classifies, scores, and answers yes/no questions. The coding model still writes code. Deterministic policy still decides what may run. `jev_assess_risk` never returns allow.

```powershell
uv sync --extra dev
.\.venv\Scripts\python.exe -m pytest
.\scripts\install.ps1
.\scripts\verify.ps1
.\scripts\rollback.ps1
```

Credentials stay in `D:\Projects\jev-mcp\.env` and are referenced by `JEV_ENV_FILE`. Set `JEV_MOCK=1` to run without the network. Set `JEV_HOOK_LIVE=1` only if Claude's PreToolUse hook should call Jev after the local policy screen.

Backups under `backups\` can contain private harness configuration. Do not commit them.
