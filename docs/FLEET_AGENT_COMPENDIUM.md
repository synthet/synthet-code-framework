---
type: Report
title: "Fleet Agent Compendium: Complete Inventory & Architecture"
description: "Inventory and architecture of agent assets across the project fleet and five harnesses."
resource: FLEET_AGENT_COMPENDIUM.md
tags: [agents, inventory, harnesses]
timestamp: 2026-10-19T00:00:00Z
okf_version: 0.1
---
# Fleet Agent Compendium (summary)

A fleet inventory counts the agent assets (skills, slash commands, subagents, hooks and MCP server
configs) deployed across a workstation's projects and five harnesses, finds duplicated or drifted
copies by content hash, and recommends which assets to harmonize into this framework.

## Harness discovery paths

| Harness | Global Skills Path | Global Rules Path | Global Commands Path | Global MCP Config |
|---|---|---|---|---|
| **Claude Code** | `~/.claude/skills/` | `~/.claude/rules/`, `CLAUDE.md` | `~/.claude/commands/` | `~/.claude.json` |
| **Cursor** | `~/.cursor/skills/` | `~/.cursor/rules/*.mdc` | `~/.cursor/commands/` | `~/.cursor/mcp.json` |
| **Codex** | `~/.agents/skills/` | `AGENTS.md` | Via agent definitions | `~/.codex/config.toml` |
| **Antigravity (Agy)** | `~/.gemini/config/skills/` | `~/.gemini/config/rules/`, `GEMINI.md` | Native slash commands | `~/.gemini/config/mcp_config.json` |
| **Grok** | `~/.grok/bundled/skills/` | `~/.grok/rules/` | Native CLI commands | `~/.grok/config.toml` |

## Per-machine inventory

The full compendium (per-project asset lists, private and machine-specific skills, MCP server
inventory and drift tables) describes one specific workstation, so it is kept in the maintainer's
private documentation rather than in this public repository. Generate an equivalent report for
your own fleet with the agent-setup and harness-log tooling in `scripts/`.
