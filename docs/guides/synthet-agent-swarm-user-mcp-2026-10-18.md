---
type: Guide
title: synthet-agent-swarm User MCP Cookbook
description: Register the local synthet-agent-swarm stdio server in the user config of Claude
  Code, Codex, Cursor, Grok, and Antigravity.
resource: guides/synthet-agent-swarm-user-mcp-2026-10-18.md
tags:
- docs
- agent-tooling
- mcp
- synthet-agent-swarm
- grok
timestamp: 2026-10-18 00:00:00+00:00
okf_version: 0.1
---

# synthet-agent-swarm user MCP cookbook

The judge swarm is a local read-only stdio MCP server. User-level registration makes
`swarm_search`, `swarm_run`, and `run_judge_panel` available in every project. The older
[MCP multi-harness cookbook](mcp-multi-harness-cookbook-2026-10-04.md) covers Claude Code, Cursor,
Codex, Antigravity, and Gemini CLI. This page adds Grok and the workspace-root rule for this
server.

Paths use `~` for the user profile and `<checkout>` for the `synthet-agent-swarm` repo. The
package directory stays `agent-orchestrator/`. The launch file is
`<checkout>/agent-orchestrator/dist/index.js`. `dist/` is gitignored, so run `npm run build` in
`agent-orchestrator/` before registering.

The public repo is `https://github.com/synthet/synthet-agent-swarm`.

## Where to write the user entry

| Harness | User file | Shape |
|---|---|---|
| Claude Code | `~/.claude.json` → top-level `mcpServers` | JSON. `~/.claude/settings.json` is not the user MCP store. |
| Codex | `~/.codex/config.toml` | `[mcp_servers."<name>"]` |
| Cursor | `~/.cursor/mcp.json` → `mcpServers` | JSON. `${workspaceFolder}` expands here. |
| Grok | `~/.grok/config.toml` | `[mcp_servers.<name>]`. A project `.grok/config.toml` with the same name replaces this entry for that repo. |
| Antigravity CLI, and the shared 2026 global file | `~/.gemini/config/mcp_config.json` | JSON `mcpServers`. |
| Antigravity app (legacy file, only when it already exists) | `~/.gemini/antigravity/mcp_config.json` | Same JSON shape. |

Leave `~/.gemini/antigravity-backup/` alone. Add `~/.gemini/antigravity-ide/mcp_config.json` only
when that IDE build is still the one that loads MCP. Do not create a project `.mcp.json` or
`.grok/config.toml` as a stand-in for the user entry.

Grok also imports Claude and Cursor MCP servers when `[compat.claude] mcps` and
`[compat.cursor] mcps` are on. The native `~/.grok/config.toml` entry wins when the name matches.

## Recipe 1 — Add the server

Add the name `synthet-agent-swarm` only when it is missing. If that name already exists and its
first argument is the current `dist/index.js`, leave it. If the name exists with a different
command or args, leave it and report the conflict.

Cursor and Antigravity may set the workspace. Claude Code, Codex, and Grok must not receive
`WORKSPACE_ROOT=${workspaceFolder}`: they do not expand that token, and a literal value becomes
the server's workspace root. The server uses `WORKSPACE_ROOT` when it is a real path, otherwise
the process working directory. It does not read `CLAUDE_PROJECT_DIR`.

Claude Code, inside the top-level `mcpServers` object:

```json
"synthet-agent-swarm": {
  "type": "stdio",
  "command": "node",
  "args": ["<checkout>/agent-orchestrator/dist/index.js"]
}
```

Cursor, when the entry is missing:

```json
"synthet-agent-swarm": {
  "type": "stdio",
  "command": "node",
  "args": ["<checkout>/agent-orchestrator/dist/index.js"],
  "env": { "WORKSPACE_ROOT": "${workspaceFolder}" }
}
```

Codex. Judge runs can take up to 15 minutes, so the tool timeout is 900 seconds:

```toml
[mcp_servers."synthet-agent-swarm"]
command = "node"
args = ["<checkout>/agent-orchestrator/dist/index.js"]
enabled = true
startup_timeout_sec = 30
tool_timeout_sec = 900
```

Grok:

```toml
[mcp_servers.synthet-agent-swarm]
command = "node"
args = ["<checkout>/agent-orchestrator/dist/index.js"]
enabled = true
```

Antigravity, in both live JSON files from the table:

```json
"synthet-agent-swarm": {
  "command": "node",
  "args": ["<checkout>/agent-orchestrator/dist/index.js"],
  "env": { "WORKSPACE_ROOT": "${workspaceFolder}" }
}
```

Edit JSON with a parser, or insert one object into the top-level `mcpServers` value. Append a
TOML table at the end of the file. Re-read immediately before writing. After writing, parse the
file again and check that every pre-existing server's command, args, and env are unchanged.
Do not print env values. Do not put tokens in `args`.

On 2026-10-18 the Cursor user file already had this entry, plus an alias
`subagent-orchestrator` aimed at the same `dist/index.js`. Claude, Codex, Grok, and both live
Antigravity files received the new name. The older `subagent-orchestrator` rows in Claude,
Codex, and Antigravity still pointed at the previous checkout and were left in place.

## Recipe 2 — Prove the process, then reload the client

Writing the file does not reconnect a client that is already running. Probe the built entry
before reloading:

```powershell
node <checkout>/agent-orchestrator/dist/index.js
```

Send one `initialize` request and then `tools/list`. A good process reports server name
`synthet-agent-swarm`, version `0.1.0`, and these tools:

- `swarm_search`
- `swarm_run`
- `run_judge_panel`
- `detect_subagents`
- `run_subagent`
- `run_judge_swarm`

The last three names are wrappers. New callers use the first three.

Then reload MCP in each client: a new Claude Code session, a new Codex session, Cursor's MCP
reload, `r` in Grok's `/mcps` modal or a new Grok session, and Antigravity's MCP reload.

## Gotchas

- `allowWrites: true` is rejected. The server does not render images and does not call Jev.
- A missing `dist/index.js` fails the handshake. Build first.
- An old `subagent-orchestrator` entry that still points at `subagent-orchestrator/agent-orchestrator/dist/index.js` will fail. Add `synthet-agent-swarm` beside it. Repoint the old name only when you mean to replace that entry.
- A project file that defines the same server name shadows the user entry. One definition is enough.
- Open sessions keep the MCP list they loaded at start.
