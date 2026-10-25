# Jev Engineering (`_agent-infra/jev`)

Local typed decision layer and centralized permission auto-approval gate for Claude Code, Codex, Cursor, Antigravity, and Grok.

Jev classifies, scores, and evaluates semantic choices. The coding model writes code. Deterministic policy strictly governs execution (`T0` deny, `T1` human ask, `T2` safe allow, `T3` Jev eligible, `T4` unclassified).

---

## 1. Architecture & Location Rationale

`D:\Projects\_agent-infra\jev` is placed outside both [`jev-mcp`](../jev-mcp) and [`synthet-code-framework`](../synthet-code-framework):

- **Role Boundaries:**
  - `synthet-code-framework`: Reusable agent specification, prompt templates, rules, and workflow playbooks.
  - `jev-mcp`: MCP tool server exposing raw TypeSafe Jev System One primitives (`jev_choice`, `jev_score`, etc.).
  - `_agent-infra/jev`: Machine-wide control plane enforcing deterministic policy screens, auditing tool calls, and bridging harness lifecycle hooks.
- **State & Backup Isolation:**
  - Audit database (`data/state.db`) records real-time tool commands, outcomes, and session IDs across all repositories.
  - Backups (`backups/<timestamp>/`) hold snapshots of personal harness configs (`~/.claude/settings.json`, `~/.codex/config.toml`, Cursor `state.vscdb`). Keeping this out of shared framework git repos prevents accidental leak of host history or private settings.
- **Authority & Anti-Tampering:**
  - The gate monitors activities occurring *within* `synthet-code-framework` and `jev-mcp`. Placing the gate in an external infrastructure directory ensures an agent cannot bypass or mutate its own guardrail during project work.
- **Underscore Prefix (`_`):**
  - Excludes the directory from project multi-repo scans, worktree tools, and backlog claim automation.

---

## 2. Directory Layout

```
D:\Projects\_agent-infra\jev\
├── config\
│   └── permission-policy.json  # Single source of truth for command classification tiers
├── data\
│   └── state.db                # SQLite WAL audit log for permission decisions
├── backups\                    # Byte-for-byte config backups generated before apply
├── scripts\
│   ├── hook-prompt.ps1         # UserPromptSubmit hook entrypoint
│   ├── hook-pre-tool.ps1       # PreToolUse advisory risk hook entrypoint
│   ├── run_mcp.py              # jev-engineering MCP server launcher
│   └── install.ps1             # Local setup installer
└── src\jev_engineering\
    ├── permission\             # Gate, grammar, classifier, and harness adapters
    ├── install_config.py       # Global config merger and permissions orchestrator
    └── hook.py                 # Hook payload handler (prompt & pre-tool)
```

---

## 3. Windows Hook Execution & Timeouts

- **Process Startup Latency:** On Windows, launching `pwsh -NoProfile` takes 1.5–2.5s; starting Python adds 0.5–1.0s. Under CPU/disk load, cold starts reach 2.5–3.5s.
- **Hook Timeouts:** Harness hook timeouts must be configured to at least **12–15s** (e.g. `timeout: 15` in `~/.claude/settings.json`). Hardcoded 3s or 5s timeouts will intermittently trigger failures during background compilations or test runs.
- **GUI Environment Execution:** Desktop GUI applications (Antigravity, Cursor) do not inherit shell profile PATHs where `uv` or WinGet binaries live. GUI hook entries must execute the virtual environment Python directly:
  `D:\Projects\_agent-infra\jev\.venv\Scripts\python.exe -m jev_engineering.permission hook --harness <harness>`

---

## 4. Development & Verification

```powershell
uv sync --extra dev
.\.venv\Scripts\python.exe -m pytest
```

Credentials reside in `D:\Projects\jev-mcp\.env` referenced by `JEV_ENV_FILE`. Set `JEV_MOCK=1` to run tests without network dependencies.

To manage permissions across all harnesses on the workstation:
```powershell
python -m jev_engineering.install_config permissions plan
python -m jev_engineering.install_config permissions apply
python -m jev_engineering.install_config permissions rollback [receipt]
```
