---
type: Reference
title: "Full Cross-Harness Permission Inventory, Live Telemetry Analysis & Governance Architecture"
description: "Permission settings across harnesses and projects, with telemetry analysis and governance architecture."
resource: permissions-full-inventory.md
tags: [permissions, inventory, governance]
timestamp: 2026-10-25T00:00:00Z
okf_version: 0.1
---
# Cross-Harness Permission Inventory (summary)

> **Scope:** Claude Code, OpenAI Codex, Cursor (IDE & CLI), Google Antigravity (IDE & CLI) and xAI Grok CLI.
> **Companion specification:** [`docs/centralized-permissions.md`](centralized-permissions.md)

Each harness has its own permission model: TOML prefix rules, SQLite state blobs, JSON glob lists and
lifecycle hooks. Left unmanaged, interactive "Always Allow" approvals accumulate into hundreds of
one-off rules per harness, including raw shells and home-root workspace trust. The centralized
permission gate gives every harness a deterministic native floor (block T0 catastrophic commands,
prompt on T1 high-risk mutations, auto-allow T2 read-only inspection) and routes borderline T3
commands through lifecycle hooks to a semantic reviewer.

## Cross-harness comparison matrix

| Dimension | Anthropic Claude Code | OpenAI Codex | Cursor (CLI & IDE) | Google Antigravity (CLI & IDE) | xAI Grok CLI |
|---|---|---|---|---|---|
| **Global Config Path** | `~/.claude/settings.json` | `~/.codex/config.toml`<br>`~/.codex/rules/default.rules` | `~/.cursor/cli-config.json`<br>`~/.cursor/permissions.json`<br>`%APPDATA%\Cursor\...\state.vscdb` | `~/.gemini/antigravity-cli/settings.json`<br>`~/.gemini/config/config.json`<br>`~/.gemini/trustedFolders.json` | `~/.grok/config.toml`<br>`~/.grok/trusted_folders.toml` |
| **Global Hook Path** | `~/.claude/settings.json` (`hooks` key) | `~/.codex/hooks.json` | `~/.cursor/hooks.json` | `~/.gemini/config/hooks.json` | *(Configured via plugin/hook specs)* |
| **Project Config Path** | `<repo>/.claude/settings.json`<br>`<repo>/.claude/settings.local.json` | `<repo>/.codex/config.toml` | `<repo>/.cursor/rules/*.mdc`<br>`<repo>/.cursor/mcp.json` | `<repo>/.agents/rules/*.md`<br>`<repo>/.agents/mcp_config.json` | `<repo>/.grok/` *(optional)* |
| **Default Approval Mode** | `"defaultMode": "auto"` | `approval_policy = "on-request"`<br>`approvals_reviewer = "auto_review"` | `"approvalMode": "auto-review"` | `"agentMode": "auto"` | `permission_mode = "auto"`<br>`yolo = false` |
| **Sandbox Mechanism** | Native OS / WSL boundary | `sandbox_mode = "workspace-write"` | Optional CLI sandbox (disabled on Win) | `enableTerminalSandbox: true`<br>`allowNonWorkspaceAccess: false` | None (host execution) |
| **Rule Syntax** | `Bash(git diff:*)`<br>`PowerShell(rg:*)`<br>`Read(**/.env)` | `prefix_rule(pattern=["git", "push"], decision="prompt")` | CLI: `Shell(git status)`<br>IDE: prefix tokens in `yoloCommandAllowlist` | `command(git status:*)`<br>`read_file(C:\path)`<br>`mcp(server/tool)` | `Bash(git status *)`<br>`Read(~/.ssh/**)` |
| **Hook Intercept Event** | `PermissionRequest` (`Bash\|PowerShell`)<br>`PreToolUse` (advisory) | `PermissionRequest` | `beforeShellExecution`<br>`beforeMCPExecution` | `PreToolUse` (`run_command\|ask_permission`) | `PreToolUse` |
| **Can Hook Auto-Approve?** | **Yes** (`decision.behavior = "allow"`) | **Yes** (`decision.behavior = "allow"`) | **Yes** (`permission = "allow"`) *(CLI only)* | **Yes** (`decision = "allow"`) | **No** (Wire only supports `deny`/`ask`/`defer`) |
| **Fail-Closed Fallback** | `{}` (Native auto/dialog prompt) | `{}` (Native reviewer/dialog prompt) | `{"permission": "ask"}` (`failClosed: true`) | `{"decision": "ask"}` / `"force_ask"` | `{"decision": "ask"}` |

---

## Per-machine inventory

The full forensic inventory (annotated global configs, rule counts and telemetry from a specific
workstation) is machine-specific and is kept in the maintainer's private documentation, not in this
public repository. To produce one for your own machine, run the harness-log and permission tooling
in `scripts/` and `infra/jev/` against your own configs.
