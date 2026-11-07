---
name: synthet-repos
description: "Use when choosing which public synthet tool or repository fits a task, or when a task mentions agent-flow, agent-mailbox, agent-swarm, llm-wiki, jev-mcp, win-gui-mcp, hetzner-mcp, lightroom-mcp or everypixel-mcp."
capability: "Map a task to the public synthet repository that owns it"
side_effect_level: read_only
approval_required: false
requires_tools: "None; see each repository's README for its tools."
output_schema: "The repository to use, and where to read next."
risk_class: low
---

# Synthet repositories

Use this map to find the public repository that owns a capability. Then read that repository's README and `AGENTS.md` before relying on details, because this list stays short on purpose.

## Agent workflow

| Repository | Use it for |
|---|---|
| `synthet-code-framework` | Reusable skills, commands, agents and the setup installer |
| `synthet-agent-flow` | Ticket tracking for coding agents, with a dependency-aware ready queue |
| `synthet-agent-swarm` | The same read-only judgement across installed harnesses, reported as strict-majority agreement |
| `synthet-agent-mailbox` | Direct encrypted messages between agents on two or more PCs |
| `llm-wiki` | A local, evidence-bound knowledge store of reviewed claims in SQLite |
| `jev-mcp` | TypeSafe Jev judgments exposed to agents |

## MCP servers

| Repository | Use it for |
|---|---|
| `win-gui-mcp` | Windows desktop automation with a snapshot and ref API |
| `hetzner-mcp` | Hetzner Cloud through fixed `hcloud` commands |
| `lightroom-mcp` | Adobe Lightroom Classic automation through a Lua plugin |
| `everypixel-mcp` | Everypixel Labs media analysis, generation and speech tools |

## Rules

- Keep this list to public repositories. Skills in public repositories must not name private ones.
- An installed tool may be unavailable on this machine. Check before assuming it is.
- Skills about one repository's internals belong in that repository, with a project prefix.
