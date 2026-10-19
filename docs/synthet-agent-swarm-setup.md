---
type: Guide
title: synthet-agent-swarm setup
description: Build the judge swarm, register it for every user harness, and install the subagent-review skill.
resource: synthet-agent-swarm-setup.md
tags: [docs, agents, mcp, synthet-agent-swarm]
timestamp: 2026-10-19T00:00:00Z
okf_version: 0.1
---

# synthet-agent-swarm setup

The judge swarm is a local read-only stdio server. One user registration makes `swarm_search`, `swarm_run`, and `run_judge_panel` available in every project. The file-by-file registration recipes live in the vault guide `docs/guides/agent-tooling/synthet-agent-swarm-user-mcp-2026-10-18.md`. This page is the setup order.

`<checkout>` is the `synthet-agent-swarm` repo. The launch file is `<checkout>/agent-orchestrator/dist/index.js`.

## 1. Build

```powershell
Set-Location <checkout>\agent-orchestrator
npm install
npm run build
```

`dist/` is gitignored. A missing `dist/index.js` fails the MCP handshake.

## 2. Register the user server

Add the name `synthet-agent-swarm` only when it is missing. If that name already points at the current `dist/index.js`, leave it. Re-read each file immediately before writing, and leave every other server unchanged. Do not print env values.

| Harness | User file | `WORKSPACE_ROOT` |
|---|---|---|
| Cursor | `~/.cursor/mcp.json` | `${workspaceFolder}` |
| Claude Code | `~/.claude.json` top-level `mcpServers` | omit |
| Codex | `~/.codex/config.toml` | omit. Set `tool_timeout_sec = 900` |
| Antigravity CLI | `~/.gemini/config/mcp_config.json` | `${workspaceFolder}` |
| Antigravity app | `~/.gemini/antigravity/mcp_config.json` when that file already exists | `${workspaceFolder}` |
| Grok | `~/.grok/config.toml` | omit |
| Gemini CLI | `~/.gemini/settings.json` | omit |

Claude Code, Codex, Grok, and Gemini CLI do not expand `${workspaceFolder}`. A literal token becomes the server workspace root. Do not add a project `.mcp.json` or `.grok/config.toml` for this server. A project entry with the same name hides the user entry.

Repoint a `subagent-orchestrator` entry only when its args still end in `subagent-orchestrator/agent-orchestrator/dist/index.js`. Point it at the same `dist/index.js`.

## 3. Install the skill

The consumer skill is `subagent-review`. Its canonical copy in this repo is [`.claude/skills/subagent-review/SKILL.md`](../.claude/skills/subagent-review/SKILL.md). The library id is already global in [`.agent/setup/library.json`](../.agent/setup/library.json).

From this repo, plan the user install and apply only the `subagent-review` operations:

```powershell
python -X utf8 scripts/agent_setup.py plan --projects-root <projects-root> --user-root $env:USERPROFILE --scope global --out .agent/local/setup/swarm-skill.json
```

That writes `~/.claude/skills`, `~/.agents/skills`, `~/.gemini/config/skills`, and `~/.gemini/antigravity-cli/skills`. Cursor discovers the Claude and agents copies. Codex uses the agents copy. Grok has no separate skill directory; its user MCP entry is the wiring, and it sees the skill in a workspace that contains it.

Review the plan before apply. Do not apply unrelated library updates in the same receipt.

## 4. Call it

Run judges through the MCP server. Do not spawn `codex`, `agy`, `claude`, or `agent` in the terminal. Writes stay off.

1. `swarm_search`
2. `swarm_run` for a review or one judgement. Omit `harnesses` for every available harness.
3. `run_judge_panel` for a frozen manifest. Blind panels reject `extraContext`. The tool does not call Jev.

Agreement is evidence. It is not a human label.

## 5. Prove it, then reload

```powershell
node <checkout>\agent-orchestrator\dist\index.js
```

Send `initialize`, then `tools/list`. Expect server name `synthet-agent-swarm`, version `0.1.0`, and `swarm_search`, `swarm_run`, `run_judge_panel`. Then reload each client. An open session keeps the MCP list it loaded at start.

Before passing a file list from this framework repo to a review, run `python scripts/agent_policy/validate_export.py --external-export --approval-marker APPROVED_EXTERNAL_EXPORT <files...>`.
