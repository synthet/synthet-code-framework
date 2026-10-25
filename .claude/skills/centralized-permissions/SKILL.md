---
name: centralized-permissions
description: "Use when setting up, reconfiguring, auditing, or restoring the centralized AI agent permission decision gate (hook → Jev → audit → approve | ask) across Claude Code, Cursor/Grok, Codex, and Antigravity, or when reconciling global and project permission policies in D:\\Projects."
capability: "Configure, audit, reconcile, apply, and restore centralized cross-harness permission review and safe command tiers."
side_effect_level: local_write
approval_required: true
requires_tools: "uv; Python 3.11+; scripts/harness_logs; _agent-infra/jev"
output_schema: "Tier catalog, plan diffs, audit summary, or receipt report."
risk_class: high
---

# Centralized Permissions Management

Use this skill when auditing, establishing, updating, or rolling back the centralized permission auto-approval gate across all coding agents.

The core path is:
`harness hook → deterministic screen (T0/T1) → Tier-1 Jev Noul (T3, >= 0.88/0.80/0.75) → Tier-2 Coin-Flip Adjudicator (0.45..thresh via synthet-agent-swarm decide) → SQLite audit log → approve | fallback to ask`

---

## 1. Quick Reference Commands

All management actions run through `scripts/manage_permissions.py` (canonical stateless source in `infra/jev/` synced with runtime `D:\Projects\_agent-infra\jev\`):

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

# 7. Test how a specific command classifies (Note: test T0 strings via pytest `verify`, not raw shell args)
python -m scripts.manage_permissions classify -- "docker exec db psql -c 'select 1'"

# 8. Run full verification test suite and infra/jev SHA-256 parity check
python -m scripts.manage_permissions verify
```

---

## 2. When to Use

### Activate when:
- Establishing centralized permission auto-approval on a new machine or newly installed agent harness.
- A harness has accumulated too many one-off allow rules (e.g. Codex `default.rules` > 100 entries, Cursor allowlist > 50 tokens, Antigravity allowlist > 50 entries).
- Reconciling contradictory project-level allow rules across `D:\Projects`.
- Tuning command classification tiers, thresholds, or regex patterns in `D:\Projects\_agent-infra\jev\config\permission-policy.json`.
- Auditing recent permission decisions, latency, or denials across harnesses.
- Rolling back permission settings after unexpected behavior or test failures.

### Do NOT use for:
- Routine coding tasks where permissions are already active.
- Granting ad-hoc, unbounded bypasses (e.g. `--yolo`, `--dangerously-skip-permissions`).
- Modifying `.git/config` or modifying production infrastructure directly.

---

## 3. Workflows

### Workflow A: Plan & Apply Global Settings
1. **Dry-Run Plan:**
   ```bash
   python -m scripts.manage_permissions plan
   ```
   Inspect the output table and unified diffs. Ensure only managed permission keys are modified.
2. **Review Invariants:**
   - Claude: `defaultMode: "auto"` with `PermissionRequest` hook (`matcher: "Bash|PowerShell"`, `timeout: 15`) placed at index `0` ahead of notification hooks.
   - Codex: `approvals_reviewer = "auto_review"`, `on-request` + `workspace-write` (`network_access = false`).
   - Cursor CLI: `approvalMode = "auto-review"`, `sandbox: {"readBoundary": "workspace"}`, `terminalAllowlist`.
   - Antigravity CLI: `agentMode: "auto"`, `allowNonWorkspaceAccess: true` on Windows (setting `false` on Windows injects POSIX `readonly /` causing `sandbox configuration error: readonly /: non-absolute file path`), `user_home` stripped from `trustedWorkspaces`, and `~` expanded via `os.path.expanduser()` on all `read_file`/`write_file` deny rules (preventing `deny ~/.ssh: non-absolute file path`).
   - Grok: `permission_mode: "auto"`.
3. **Apply & Verify:**
   ```bash
   python -m scripts.manage_permissions apply
   python -m scripts.manage_permissions verify
   ```
   A timestamped backup is saved to `_agent-infra/jev/backups/<stamp>/` with a `receipt.json`.

---

### Workflow B: Reconfiguring Policy Tiers & Syncing `infra/jev/`
1. Edit the canonical source of truth in `infra/jev/config/permission-policy.json` (or `D:\Projects\_agent-infra\jev\config\permission-policy.json`) and sync both trees:
   ```bash
   python -m scripts.manage_permissions sync-infra --direction to-runtime
   ```
2. Test a specific command (do not pass literal T0 destructive strings on the shell command line, as the active `PreToolUse` hook will block the outer shell call; test T0 cases via `verify` pytest instead):
   ```bash
   python -m scripts.manage_permissions classify -- "my-tool --arg"
   ```
3. Run the verification suite (runs 64+ unit tests and verifies SHA-256 parity between `infra/jev/` and `_agent-infra/jev/`):
   ```bash
   python -m scripts.manage_permissions verify
   ```
4. Regenerate and apply native harness configs:
   ```bash
   python -m scripts.manage_permissions plan
   python -m scripts.manage_permissions apply
   ```

---

### Workflow C: Restoring / Emergency Rollback
If any harness encounters issues after applying new settings:
```bash
python -m scripts.manage_permissions rollback
```
To roll back a specific historical receipt:
```bash
python -m scripts.manage_permissions rollback D:\Projects\_agent-infra\jev\backups\<timestamp>\receipt.json
```
Every modified file is restored to its exact byte-identical state and verified by hash.

---

## 4. Option Routing (Implementation Choices)

When coding agents prompt with multiple implementation options (e.g., Antigravity `ask_question`, Claude choice prompts), the request can be evaluated through Jev Choice:
1. Question, options, and project context are sent to `DecisionClient`.
2. Jev evaluates against project architecture, conventions, and acceptance criteria.
3. If Jev returns a choice with confidence $\ge 0.90$, the choice is selected automatically.
4. If confidence is below threshold, the prompt falls back to human review.

---

## 5. Security & Safety Rules

- **Fail Closed:** Any error, timeout (>8s), or missing credential falls back to the native prompt. Errors never auto-approve.
- **Redaction First:** Secrets (`.env`, `secrets.json`, tokens) are never sent to Jev or logged in plaintext.
- **Auditing Mandatory:** An unaudited decision cannot approve. If SQLite WAL write fails, the gate abstains.
- **Preserve Credentials:** Never touch API keys, tokens, or `.git/config` during permission setup.
