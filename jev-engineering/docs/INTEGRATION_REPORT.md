# Jev engineering integration report

Date: 2026-10-18. Host: native Windows 11. WSL is installed only as `docker-desktop`, so every harness integration is native Windows.

## Architecture that was implemented

Jev stays a typed decision function. Coding models still write code. Deterministic policy still decides what may run.

```text
harness
  -> deterministic policy (deny / ask / defer)
  -> jev-engineering MCP (decide, route, context, risk)
  -> existing jev-mcp client
  -> TypeSafe System One, pinned to jev-1.14.0
```

The new project is `D:\Projects\_agent-infra\jev`. It does not replace `D:\Projects\jev-mcp` or the existing `jev-rw-systemone` server. `llmwiki-ro-core` was left registered.

`jev_assess_risk` returns only `deny`, `ask`, or `defer`. A missing credential, timeout, network error, or low-confidence answer cannot turn a denied or approval-required action into an automatic permit. Claude's PreToolUse hook uses the same rule and never emits `allow`.

Explicit state is a local SQLite file under `data\` (tasks, chunks, decisions, advisory file locks). Query-aware context scores chunks as `hide`, `short`, `long`, or `full` and keeps the source path. Secret chunks are hidden before any provider call. Routing estimates context-rebuild cost and keeps the current model when a cheaper handoff would reload a large session. The capability catalog returns snippets unless a caller asks for a schema. Conditional instruction packs are selected from the task text. None of this reads or writes a model's internal cache.

## Source notes

Read and used:

- `C:\Users\dmnsy\Downloads\Jev-Engineering-for-Coding-Agents.pdf`
- `D:\Downloads\Using TypeSafe Jev to Route Claude Agents and Reduce Approval Prompts and Clarifying Questions.md`
- `D:\Downloads\Cookbook_ Jev Engineering and Graph Engineering on Your Laptop (October 2026).md`
- `D:\Downloads\deep-research-report (2).md`
- `D:\Downloads\deep-research-report (3).md`

The requested names `deep-research-report (2)(1).md` and `deep-research-report (3)(1).md` are not on disk. Official question and model shapes were checked against `https://docs.typesafe.ai/llms.txt`. The pin remains `jev-1.14.0`.

## Files created

Project tree under `D:\Projects\_agent-infra\jev`:

- `src\jev_engineering\` — client, policy, routing, context, catalog, state, metrics, MCP server, Claude hooks, installer
- `evals\cases.json` — 36 labeled cases
- `tests\` — 48 tests
- `scripts\install.ps1`, `verify.ps1`, `rollback.ps1`, `route.ps1`, hook scripts, MCP handshake, live smoke
- `instructions\JEV_ENGINEERING.md` and `instructions\cursor-rule.mdc`

User configuration merged, with backups in `D:\Projects\_agent-infra\jev\backups\20261019T032208927291Z`:

- `C:\Users\dmnsy\.cursor\mcp.json`
- `C:\Users\dmnsy\.cursor\rules\jev-engineering.mdc` (new)
- `C:\Users\dmnsy\.claude.json`
- `C:\Users\dmnsy\.claude\settings.json` (hooks only)
- `C:\Users\dmnsy\.claude\CLAUDE.md`
- `C:\Users\dmnsy\.codex\config.toml`
- `C:\Users\dmnsy\.codex\AGENTS.md`
- `C:\Users\dmnsy\.gemini\settings.json`
- `C:\Users\dmnsy\.gemini\GEMINI.md`
- `C:\Users\dmnsy\.gemini\antigravity\mcp_config.json`
- `C:\Users\dmnsy\.gemini\config\mcp_config.json`

No repository under `D:\Projects` received a copied boilerplate tree. Credential values were not written into config. `JEV_ENV_FILE` still points at `D:\Projects\jev-mcp\.env`.

## Integration status

| Harness | Version | What is automatic | What was verified | Limitation |
| --- | --- | --- | --- | --- |
| Claude Code | 2.1.302 | User MCP entry, global `CLAUDE.md` block, `PreToolUse` and `UserPromptSubmit` hooks | `claude mcp list` reports `jev-engineering` connected. Hook script denies `rm -rf` and does not allow. | Hooks are advisory. `JEV_HOOK_LIVE` is unset, so the tool hook does not call TypeSafe. `defaultMode` remains `auto`. |
| Codex CLI | 0.163.0-alpha.10.2 | `config.toml` MCP entry and global `AGENTS.md` block | `codex mcp list` shows the server enabled, next to the existing Jev and llmwiki rows. | Those three stdio rows are labeled `Unsupported` by this CLI build. `approval_policy` remains `on-request` and `sandbox_mode` remains `workspace-write`. No Codex session was driven through a tool call. Codex help exposes no safe per-tool Jev hook, so routing there is MCP plus the launcher. |
| Cursor IDE 3.7.42 and CLI 2026.10.16-e3cb207 | User MCP entry and always-on rule | `agent mcp list` reports `jev-engineering: ready`. `agent mcp list-tools jev-engineering` lists the four tools. | The IDE process was not restarted. Cursor has no per-tool permission hook, so risk screening is a tool call or the launcher, not an interceptor. |
| Antigravity `agy` 1.4.2 | Both Gemini MCP configs and `GEMINI.md` | `agy mcp list` shows `jev-engineering` enabled and `llmwiki-ro-core` still enabled. `agy --help` documents `mcp` and does not require an invented flag. | The IDE UI was not reloaded. `agy` can launch with `--dangerously-skip-permissions`; this install does not set that. |
| Gemini CLI 0.62.0 | `settings.json` MCP entry | `gemini mcp list` reports `jev-engineering` connected. | Same instruction file as Antigravity. No Gemini session was driven through a coding task. |

Reload Claude Code, Cursor, Codex, and Antigravity before expecting an already-open session to see the new server. File installation alone is not a live GUI-session proof. The CLI checks above are the live proofs that were run.

## Tests and live checks

- `48 passed` from `.venv\Scripts\python.exe -m pytest` (36 evaluation cases plus policy, state, install/rollback, hook, and MCP registration tests).
- MCP handshake with `JEV_MOCK=1` listed `jev_assess_risk`, `jev_decide`, `jev_route_task`, `jev_select_context`.
- One live System One call succeeded and reported `model=jev-1.14.0`. No local latency, token, or dollar figure was recorded for that call.
- Mock launcher `scripts\route.ps1 -Task "add a docstring to the parser"` returned `haiku` at the task boundary and `allows_action: false`.
- PreToolUse hook returned `permissionDecision: deny` for `rm -rf /`.

No before/after count of human approvals or clarifying questions was measured. Vendor latency and cost multiples are not treated as local results.

## Security choices

- Deterministic deny covers destructive commands, force-push, secret paths, and secret-shaped text before Jev is called.
- Prompt text that says to ignore policy does not override those denies.
- Outbound state is refused when it contains secret material.
- Metrics and hook hints do not store or echo secret values.
- Claude `defaultMode`, Codex `approval_policy`, Codex `sandbox_mode`, and the selected models were not changed.
- `JEV_HOOK_LIVE` defaults off. Turning it on adds a semantic check; it still cannot return allow.
- Backups under `backups\` contain private configuration. They are gitignored. Do not commit or copy them.

## Rollback

```powershell
powershell -NoProfile -File D:\Projects\_agent-infra\jev\scripts\rollback.ps1
```

That restores only files whose current hash still matches this install. The receipt is `D:\Projects\_agent-infra\jev\backups\20261019T032208927291Z\receipt.json`. A created file (`jev-engineering.mdc`) is removed only when its hash still matches.

## Gaps

- Cursor, Codex, and Antigravity do not intercept every tool call. Their Jev use is the MCP tools, the global instruction, and `scripts\route.ps1`.
- The harnesses still load their own built-in tool schemas. The snippet catalog applies only when an agent calls it.
- The advisory file lock is local to this store. It does not schedule subagents inside a harness.
- Historical approval and token totals were not available, so this install does not claim a measured reduction.
- Open IDE sessions need a reload before they show the new server.
