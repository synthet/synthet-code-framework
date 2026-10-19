---
type: Guide
title: MCP Multi-Harness Cookbook
description: Where Claude Code, Cursor, Codex, Antigravity, and Gemini CLI read MCP config, how
  to move a server to user level, and how to diagnose servers that show error.
resource: guides/mcp-multi-harness-cookbook-2026-10-04.md
tags:
- docs
- agent-tooling
- mcp
- cursor
- claude-code
- codex
- antigravity
timestamp: 2026-10-04 00:00:00+00:00
okf_version: 0.1
---

# MCP multi-harness cookbook

One Windows PC runs Claude Code, Cursor (IDE and `agent` CLI), Codex, Antigravity (app, IDE, and
`agy` CLI), and Gemini CLI. Each reads MCP servers from different files. These recipes keep them in
step. Paths use `~` for the user profile and `<checkout>` for a repo.

## Where each harness reads MCP config

| Harness | User level | Project level | Health check |
|---|---|---|---|
| Claude Code | `~/.claude.json` → `mcpServers` | `<repo>/.mcp.json`, enabled by `enabledMcpjsonServers` in `.claude/settings*.json` | `claude mcp list` |
| Cursor IDE and `agent` CLI | `~/.cursor/mcp.json` | `<repo>/.cursor/mcp.json`, gated by `~/.cursor/projects/<slug>/mcp-approvals.json` | `agent mcp list` (does **not** prove chat sessions attach it; see below) |
| Codex | `~/.codex/config.toml` → `[mcp_servers.<name>]` | `<repo>/.codex/config.toml` (repo must be trusted in `[projects.'<path>']`) | `codex mcp list` |
| Antigravity app | `~/.gemini/antigravity/mcp_config.json` | `<repo>/.agents/mcp_config.json` | the app's MCP panel |
| Antigravity IDE | `~/.gemini/antigravity-ide/mcp_config.json` | — | the IDE's MCP panel |
| Antigravity CLI (`agy`) | `~/.gemini/config/mcp_config.json` | **none** | `agy mcp list` |
| Gemini CLI | `~/.gemini/settings.json` → `mcpServers` | `<repo>/.gemini/settings.json` | `gemini mcp list` |

Rule of thumb: servers that should exist everywhere (mail, wiki, GitHub, Jev) go at user level.
Servers tied to one repo go at project level. `agy` is the exception: it has no project scope.
Grok, and the workspace-root rule for synthet-agent-swarm, are in the
[synthet-agent-swarm user MCP cookbook](synthet-agent-swarm-user-mcp-2026-10-18.md).

## Recipe 1 — Add a stdio server at user level everywhere

Use an absolute path to the entry point. Cursor and Antigravity expand `${workspaceFolder}` in
user config. Claude Code, Codex, and Grok do not, so leave that token out of their env values.

Claude Code:

```powershell
claude mcp add --scope user agent-mail -- node <checkout>/dist/cli.js mcp --no-listen --harness claude-code --agent-name claude --model claude
```

Cursor, Antigravity app/IDE, Gemini CLI (same JSON shape under `mcpServers`):

```json
"agent-mail": {
  "command": "node",
  "args": ["<checkout>/dist/cli.js", "mcp", "--no-listen", "--harness", "cursor", "--agent-name", "cursor", "--model", "composer"]
}
```

Codex:

```toml
[mcp_servers.agent-mail]
command = "node"
args = ["<checkout>/dist/cli.js", "mcp", "--no-listen", "--harness", "codex", "--agent-name", "codex", "--model", "codex"]
enabled = true
```

Antigravity CLI (writes `~/.gemini/config/mcp_config.json`; flags go before the name, no `cwd`):

```powershell
agy mcp add agent-mail node <checkout>/dist/cli.js mcp --no-listen --harness antigravity --agent-name antigravity --model gemini
```

Before editing by hand, back up each file (`copy file file.bak-<date>`), then edit with a JSON
parser, not regex. Re-read the file right before writing. Another agent may have changed it.

## Recipe 2 — Drop a server from project level

1. Remove it from `.mcp.json`, `.cursor/mcp.json`, `.codex/config.toml`, `.agents/mcp_config.json`.
2. Remove stale approvals: in `~/.cursor/projects/<slug>/mcp-approvals.json` delete the
   `<name>-<hash>` entries; in `.claude/settings*.json` delete the name from
   `enabledMcpjsonServers`.
3. Make sure the user-level entry exists **under the same name** in every harness you use, or
   tool names change for prompts and skills that reference them.

## Recipe 3 — Verify a server outside any harness

`<harness> mcp list` only shows that a server spawned. To prove the tools work, run the MCP
handshake yourself and call one read-only tool:

```js
// probe.mjs — node probe.mjs servers.json [timeoutMs]
// servers.json: {"name": {"command","args","cwd","env","call": {"name","arguments"}}}
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
const servers = JSON.parse(readFileSync(process.argv[2], "utf8"));
const timeoutMs = Number(process.argv[3] ?? 30000);
const send = (c, m) => c.stdin.write(JSON.stringify({ jsonrpc: "2.0", ...m }) + "\n");
for (const [name, cfg] of Object.entries(servers)) {
  const t0 = Date.now(), seen = new Set();
  let buf = "", err = "", done = false;
  const child = spawn(cfg.command, cfg.args ?? [], { cwd: cfg.cwd, env: { ...process.env, ...cfg.env }, windowsHide: true });
  const finish = (s) => { if (done) return; done = true; child.kill(); console.log(`== ${name} [${Date.now() - t0}ms] ${s}`); if (!s.includes("OK")) console.log(err.slice(-1500)); };
  child.on("error", (e) => finish("SPAWN ERROR " + e.message));
  child.on("exit", (code) => finish("EXITED " + code));
  child.stderr.on("data", (d) => (err += d));
  child.stdout.on("data", (d) => {
    buf += d;
    for (const line of buf.split("\n")) {
      let msg; try { msg = JSON.parse(line); } catch { continue; }
      if (seen.has(msg.id)) continue; seen.add(msg.id);
      if (msg.id === 1) { send(child, { method: "notifications/initialized" }); send(child, { id: 2, method: "tools/list" }); }
      if (msg.id === 2) cfg.call ? send(child, { id: 3, method: "tools/call", params: cfg.call }) : finish(`OK ${msg.result?.tools?.length} tools`);
      if (msg.id === 3) finish((msg.error || msg.result?.isError ? "CALL FAILED " : "CALL OK ") + JSON.stringify(msg.result ?? msg.error).slice(0, 300));
    }
  });
  setTimeout(() => finish("TIMEOUT"), timeoutMs);
  send(child, { id: 1, method: "initialize", params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "probe", version: "0" } } });
}
```

If a server bridges to a worker (Python in Docker, a DB), call a tool that goes through the bridge.
A `search` that only reads a local catalog proves nothing about the worker.

## Recipe 4 — A server shows `error` in a harness

Work down the list; stop at the first hit.

1. **Probe it standalone** (Recipe 3). Spawn error, early exit, or timeout means the command is
   broken. Common causes: missing `dist/` build, Python without the `mcp` package, a legacy HTTP
   endpoint that now answers 404, bare `uv`/`python` not on the host's `PATH` (use absolute exe
   paths). If the handshake works but tool calls fail, check the backing service: a stopped
   Docker Desktop shows up as `PostgreSQL connection pool is not initialized` or a `docker`
   pipe error, not as an MCP error.
2. **Slow cold start.** A first spawn can take 20–30 s (large graph files, antivirus scanning a
   fresh exe). Retry once before changing config; raise `startup_timeout_sec` in Codex.
3. **Same name at user and project level.** The project entry shadows the user entry. If the
   project copy fails to load, for any reason, the working user copy disappears too. Keep one.
4. **Stale entries in a config you forgot existed.** Grep every file in the table above for the
   server name, including the Antigravity IDE and Gemini CLI files.
5. **Cursor chat only** — `agent mcp list` says `ready`, chat panel says `error` and
   "is not connected. Check the agent logs…": see Recipe 5.
6. **Long-running sessions** load MCP once at startup. After a fix, start a new chat; resuming the
   old one keeps the old state.

## Recipe 5 — Cursor Agent: project servers ready in `mcp list`, error in chat

**Symptom.** In a repo with `.cursor/mcp.json`, every project server shows `error` in the chat's
MCP panel. User-level servers work. `agent mcp list` reports the project servers as `ready`, and
`agent mcp enable <name>` says "already enabled and approved". `agent -p --approve-mcps` attaches
them; plain `agent -p` does not.

**Cause** (agent CLI 2026.10.01). A project server is approved when
`<name>-<first 16 hex of sha256(JSON.stringify({path, server}))>` is in
`~/.cursor/projects/<slug>/mcp-approvals.json`, where `server` is the config entry without `_`
keys. `mcp list`/`mcp enable` hash `path` with backslashes; chat sessions hash the same
`<local-project>` path with forward slashes. Only the backslash key ever gets stored, so chat sessions treat the server as
unapproved and drop it without logging why.

**Fix.** From the repo root, add both path forms:

```js
// cursor-approve.mjs — node cursor-approve.mjs [--dry-run]
import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
const root = process.cwd();
const servers = JSON.parse(readFileSync(join(root, ".cursor", "mcp.json"), "utf8")).mcpServers ?? {};
const slug = root.replace(/[:\\/]+/g, "-").replace(/^-|-$/g, "");
const approvalsPath = join(homedir(), ".cursor", "projects", slug, "mcp-approvals.json");
const approvals = existsSync(approvalsPath) ? JSON.parse(readFileSync(approvalsPath, "utf8")) : [];
const added = [];
for (const [name, entry] of Object.entries(servers)) {
  const server = Object.fromEntries(Object.entries(entry).filter(([k]) => !k.startsWith("_")));
  for (const path of [root.replace(/\\/g, "/"), root.replace(/\//g, "\\")]) {
    const key = `${name}-${createHash("sha256").update(JSON.stringify({ path, server })).digest("hex").slice(0, 16)}`;
    if (!approvals.includes(key)) { approvals.push(key); added.push(key); }
  }
}
console.log(`${approvalsPath}\nadded: ${added.join(", ") || "none"}`);
if (added.length && !process.argv.includes("--dry-run")) writeFileSync(approvalsPath, JSON.stringify(approvals, null, 2) + "\n");
```

Then start a **new** chat. Confirm with:

```powershell
agent -p --trust --output-format text "Without calling any tools, list the MCP namespace names you have."
```

The key covers the exact server config. Rerun the script after any edit to that server in
`.cursor/mcp.json`. One-off alternative: start the session with `agent --approve-mcps`.

**How it was found.** A `--require` preload that wraps `crypto.createHash` and logs any input
starting with `{"path":` shows the two path spellings side by side:

```powershell
$env:HASHLOG_FILE = "$PWD\hashlog.txt"; $env:NODE_OPTIONS = "--require=<dir>\hashlog.cjs"
agent mcp list; agent -p --trust "Reply ok."
```

## Recipe 6 — Antigravity CLI has no project scope

`agy` ignores `.agents/mcp_config.json`. For a repo-specific server, add it at user level with
`agy mcp add` and make sure the server does not depend on `cwd` (it has no `cwd` option). A server
that resolves its root from its own file path (`import.meta.url`) is safe.

## Gotchas

- Several harnesses on one PC can each spawn the same peer server. If the server also listens on a
  port, start every copy with a no-listen flag and run one listener separately.
- Do not commit `.cursor/mcp.json`, `.mcp.json`, or `.codex/config.toml` if they hold tokens or
  machine paths; commit `*.example.*` versions with placeholders.
- A harness's own `mcp list` spawns a fresh process. It can be green while an open session is red.
- When another agent is working in the same configs, re-read before every write and do not undo
  its renames. Agree on one server name per harness instead.
