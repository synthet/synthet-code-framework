---
type: Runbook
title: External CLI Reviews
description: Set up and run review-only Codex/Gemini reviews through the subagent-orchestrator MCP server.
resource: EXTERNAL_CLI_REVIEWS.md
tags: [docs, agents, review, mcp]
timestamp: 2026-06-16T00:00:00Z
okf_version: 0.1
---

# External CLI reviews

Run external CLI coding agents (Codex, Gemini) as **review-only** second opinions through the
**subagent-orchestrator** MCP server — never by shelling out to `codex` / `gemini` directly.

## Dependency

This subsystem depends on a sibling **`subagent-orchestrator`** MCP server (not bundled in this
framework). Check it out alongside this repo and build it once, then expose it as an MCP server.

## Setup

1. Build the orchestrator (in its own checkout): `npm install && npm run build`.
2. Add it to `.cursor/mcp.json` (gitignored) as project key **`cli-review`**, or to your user-level
   `~/.cursor/mcp.json` as **`subagent-orchestrator`**.
3. Reload Cursor / restart the MCP client so the server is picked up.

## Use

- `/check-subagents` — detect which external agents are available and runnable.
- `/run-codex-review`, `/run-gemini-review`, `/run-subagent-review` — run a review (or a sequential
  panel / tie-breaker).
- Skill: [`.claude/skills/subagent-review/SKILL.md`](../.claude/skills/subagent-review/SKILL.md);
  tool reference: [`.claude/skills/subagent-review/references/mcp-tools.md`](../.claude/skills/subagent-review/references/mcp-tools.md).

## Safety

- Review-only: never set `allowWrites: true`.
- External review exports source, prompts, and context to another provider; obtain explicit approval before each export and scope files narrowly.
- Never include secrets, `.env`, or a full `config.json` in the task/files/context.
- Outputs land in `.agent-runs/` (gitignored); treat as sensitive. See [`../.agent/SAFETY.md`](../.agent/SAFETY.md).
