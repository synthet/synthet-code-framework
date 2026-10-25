# Centralized Permission Auto-Approval & Harness Governance

This document specifies the unified permission auto-approval gate, command classification tiers, cross-harness hook contracts, and operational workflows across Claude Code, OpenAI Codex, Cursor Agent/IDE, Google Antigravity, and Grok CLI.

---

## 1. Context & Motivation

A 30-day audit of cross-harness session transcripts and configuration files in `D:\Projects` revealed significant security and operational issues:
- **Codex:** Accumulated 1,111 persisted one-off `prefix_rule`s in `rules/default.rules` (including `git push`, `Remove-Item`, and destructive SQL calls).
- **Cursor CLI:** Defaulted to `approvalMode: "unrestricted"` with sandbox disabled on Windows.
- **Cursor IDE (`state.vscdb`):** 683 `yoloCommandAllowlist` entries, including dangerous tokens like raw `cmd`, `powershell`, and parse noise (`}`, `$_`).
- **Antigravity CLI:** 1,069 allow rules (including wildcards `python:*`, `pwsh -Command:*`, `git:*`), with `trustedWorkspaces` extending to the user's home root `C:\Users\dmnsy`.
- **Grok CLI:** Global `permission_mode = "always-approve"`.
- **Project Repos:** Accumulated gitignored and committed `.claude/settings.json` allowlists containing `gh pr:*`, `docker exec *`, and scratchpad paths.

The centralized permission architecture replaces disparate, ever-expanding local allowlists with a single, verifiable, audited decision path.

---

## 2. Decision Pipeline Architecture

```
harness hook ──► adapter.normalize ──► gate.decide ────────────────────────────────────────► adapter.encode
 (per harness)    Operation{harness,     1 Hard screen  (policy.screen: deny/ask)              approve  │ fallback
                  tool, command, cwd,    2 Segment classify (T0..T4)                            (native  │ (ask /
                  mode, session}         3 Enrollment  (repo under D:\Projects)                 allow)   │ abstain)
                                         4 Tier-1 Jev: per-question Noul >= (0.88/0.80/0.75)
                                         5 Tier-2 Coin-Flip (0.45 <= min < thresh):
                                           synthet-agent-swarm decide (Flash/Mini <= 4.5s)
                                         6 Audit write (SQLite WAL) — failure ⇒ fallback
```

> **Full Cross-Harness Inventory & Live Telemetry Audit:** See [`docs/permissions-full-inventory.md`](permissions-full-inventory.md) for the complete 5-harness configuration reference, 63-project matrix, live `state.db` audit analysis, and October 2026 lightweight model matrix.

### Invariants & Non-Negotiables
1. **Errors and Timeouts Fail Closed:** Any network failure, credential absence, timeout (>8s), or SQLite audit write failure immediately falls back to the native user prompt. Nothing on the error path ever auto-approves.
2. **Deterministic Screen Overrides AI:** If a command matches a T0 deny or T1 human-ask rule, Jev is never called. Jev cannot soften or override a deterministic denial.
3. **Data Protection / Redaction:** Only the redacted command, enrolled repo path, and approved scope are passed to Jev. Secrets (`.env`, `secrets.json`, tokens, private keys) are scrubbed before evaluation.
4. **Audit Immutability:** Every decision (approved, denied, asked, or fallen back) is recorded in `data/state.db` under the `permission_audit` table.

---

## 3. Command Classification Tiers

Compound commands are split on `&&`, `||`, `;`, `|`, and newlines for both bash and PowerShell. The riskiest segment determines the overall tier.

| Tier | Meaning | Native Floor | Jev Called? | Representative Operations |
|---|---|---|---|---|
| **T0** | **Deny** | Native deny rule | No | `diskpart`, `format`, `reg delete`, `Set-ExecutionPolicy`, destructive disk/VM resets, `.git/config` mutations. |
| **T1** | **Human Ask** | Native prompt | No | `git push`, `gh pr create/merge`, `git reset --hard`, `git clean`, `docker compose down`, dependency installs (`npm/pip/uv install`), remote network requests (`curl` to external hosts), process termination (`Stop-Process`, `taskkill`). |
| **T2** | **Static-Safe** | Broad native allow | No | Read-only inspection: `git status/diff/log/show/branch/rev-parse/merge-base/check-ignore`, `rg`, `grep`, `findstr`, `netstat`, `ls`, `dir`, `cat`, `head`, `tail`, `wc`, read-only `sed` (no `-i`), `Get-Content`, `Get-ChildItem`, `Test-Path`. |
| **T3** | **Jev-Eligible** | Native prompt | **Yes** ($\ge 0.98$) | Project code execution within workspace: `python <script>`, `pytest`, `npm test`, `dotnet build/test`, `cargo check/test`, `uv run`, local git writes (`git add`, `git commit -m`, `git switch`), local file creation/moving in repo/scratch. |
| **T4** | **Unclassified** | Native prompt | No | Unknown commands or custom binaries. Abstains and prompts the user; mined for future classification. |

### Container & Wrapper Unwrapping
- Wrappers (`cmd /c`, `pwsh -Command`, `bash -c`) are unwrapped up to two levels deep so inner commands inherit their proper tier.
- Container executions (`docker exec <container> <cmd>`) unwrap `<cmd>` without host path restrictions:
  - Inner static-safe inspection (`ls`, `cat`) is elevated from T2 to **T3** (shared state requires Jev approval).
  - Inner test runners (`pytest`, `python scripts/...`) evaluate as **T3**.
  - Unknown or mutating inner tools evaluate as **T1** (prompting human review).

---

## 4. Per-Harness Hook Wire Contracts

| Harness | Intercept Point | Approve Wire Signal | Ask / Fallback Wire Signal |
|---|---|---|---|
| **Claude Code** | `PermissionRequest` (`Bash\|PowerShell`) | `{"decision": {"behavior": "allow"}}` | `{}` (abstain to native auto mode prompt) |
| **Codex** | `PermissionRequest` | `{"decision": {"behavior": "allow"}}` | `{}` (abstain to native reviewer prompt) |
| **Cursor** | `beforeShellExecution`, `beforeMCPExecution` | `{"permission": "allow"}` | `{"permission": "ask"}` |
| **Antigravity** | `PreToolUse` (`run_command\|ask_permission`) | `{"decision": "allow"}` | `{"decision": "force_ask"}` (T1) / `{"decision": "ask"}` |
| **Grok** | `PreToolUse` | *(Cannot approve directly; allow = "not blocked")* | `{"decision": "ask"}` (T1) / defer |

---

## 5. Option Routing (Implementation Choices)

When an agent prompts with architectural or implementation choices (e.g., Antigravity `ask_question`, Claude option prompts), the request can be evaluated through Jev Choice:
1. The question and options are sanitized.
2. Jev evaluates the options against project conventions, `AGENTS.md`, and acceptance criteria.
3. If Jev returns a choice with confidence $\ge 0.90$, the option is selected automatically.
4. If confidence is below threshold or options are ambiguous, the prompt falls back to the user.

---

## 6. Management & Operational Commands

The unified CLI `scripts/manage_permissions.py` coordinates all operations:

```bash
# 0. Bootstrap D:\Projects\_agent-infra\jev from git-tracked infra/jev (first-time machine setup)
python -m scripts.manage_permissions bootstrap

# 1. Sync stateless infra/jev code with D:\Projects\_agent-infra\jev (or --check for SHA-256 parity)
python -m scripts.manage_permissions sync-infra --direction to-runtime
python -m scripts.manage_permissions sync-infra --direction from-runtime
python -m scripts.manage_permissions sync-infra --check

# 2. Preview changes across global configs and D:\Projects repos without touching disk
python -m scripts.manage_permissions plan

# 3. Apply reviewed changes with automatic backups and receipt.json
python -m scripts.manage_permissions apply

# 4. Roll back changes byte-identically if needed
python -m scripts.manage_permissions rollback

# 5. View recent audited decisions and latency
python -m scripts.manage_permissions audit --since 7d

# 6. Mine command catalog from transcripts across all harnesses
python -m scripts.manage_permissions catalog --since 30d --out catalog.json

# 7. Test how a specific command classifies
python -m scripts.manage_permissions classify -- "docker exec db psql -c 'select 1'"

# 8. Run full verification test suite and infra/jev parity check
python -m scripts.manage_permissions verify
```

---

## 7. Policy Reconfiguration & Remote-Backed Git Hosting (`infra/jev/`)

The canonical Git-tracked source tree for `_agent-infra/jev` lives at:
`D:\Projects\synthet-code-framework\infra\jev\`

And the active runtime installation (holding `.venv/`, `data/state.db`, and `backups/`) lives at:
`D:\Projects\_agent-infra\jev\`

To adjust policy or gate logic:
1. Edit `infra/jev/config/permission-policy.json` (or `D:\Projects\_agent-infra\jev\config\permission-policy.json`).
2. Run `python -m scripts.manage_permissions sync-infra --direction to-runtime` (or `from-runtime`) so both trees match.
3. Run `python -m scripts.manage_permissions plan` to review rendered diffs across all harnesses.
4. Run `python -m scripts.manage_permissions verify` to verify all unit tests and SHA-256 parity.
5. Run `python -m scripts.manage_permissions apply` to deploy updates.

---

## 8. Architecture & Location Rationale (`_agent-infra`)

`D:\Projects\_agent-infra\jev` is placed outside both `synthet-code-framework` and `jev-mcp` by architectural design:

1. **Separation of Concerns & Lifecycles:**
   - **`synthet-code-framework`** is a portable, clean repository template and specification monorepo for project scaffolding, agent rules, and workflow playbooks. It is designed to be committed, reviewed, and synced across repositories without machine-specific state.
   - **`jev-mcp`** is a dedicated Model Context Protocol tool server library providing semantic judgment primitives (`jev_choice`, `jev_score`, `jev_noul`, `jev_box`). It is an API tool provider, not a security or access enforcement engine.
   - **`_agent-infra\jev`** is the machine's central agent governance control plane, managing command classification, deterministic screening, audit logging, and cross-harness hook adapters across all projects.

2. **State & Backup Isolation:**
   - `_agent-infra\jev` stores mutable, machine-local operational data:
     - `data/state.db`: SQLite WAL database auditing every command decision, approval, latency, and session ID across all harnesses on the machine.
     - `backups/<timestamp>/`: Byte-for-byte snapshots of user settings (`~/.claude/settings.json`, `~/.codex/config.toml`, Cursor `state.vscdb`, etc.) generated before every apply.
   - Housing this state in a clean framework or library repo would risk committing private session logs, sensitive commands, or host snapshots into Git.

3. **Tamper Resistance & Authority Boundary:**
   - The permission gate intercepts and governs operations executed inside `synthet-code-framework` and `jev-mcp`.
   - If the gate code and policies resided inside `synthet-code-framework`, an agent modifying the framework could inadvertently mutate, bypass, or break the active security gate that monitors its own session.
   - Keeping the authority plane in `_agent-infra` preserves a strict boundary between the governor and the governed.

4. **Underscore Prefix (`_agent-infra`):**
   - The leading underscore visually and programmatically excludes the folder from project discovery tools, worktree enumerators, Graphify indexers, and backlog claims in `D:\Projects`.

---

## 9. Windows Hook Execution & Timeout Rules

On Windows workstations, cross-harness lifecycle and permission hooks have specific execution constraints:

1. **Process Startup Overhead:**
   - Spawning `pwsh -NoProfile` on Windows requires 1.5–2.5s for .NET CLR initialization.
   - Invoking Python afterwards adds 0.5–1.0s. Under disk I/O or background CPU load (e.g. running test suites), total execution time reaches 2.5–3.5s.
   - **Rule:** Hook timeouts in harness configurations (`~/.claude/settings.json`, etc.) must be set to at least **12–15 seconds** (e.g., `UserPromptSubmit: 15s`, `PreToolUse: 15s`). A 3s or 5s timeout will intermittently fail and discard hook output under normal development workloads.

2. **GUI Environment PATH Boundaries:**
   - GUI desktop applications (Cursor IDE, Antigravity) do not run shell profile scripts (such as PowerShell `$PROFILE`) on startup. Consequently, binaries located in WinGet or Cargo paths (such as `uv.exe`) may not be on their `PATH`.
   - **Rule:** Hook definitions for GUI harnesses must invoke Python directly via the resolved virtual environment path (`D:\Projects\_agent-infra\jev\.venv\Scripts\python.exe`) rather than relying on bare `uv run`. Terminal-native harnesses (Claude Code in PowerShell) can safely use `uv run`.
