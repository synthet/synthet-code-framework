# AI Agents Configuration — ${PROJECT_NAME}

## Overview

This repo ships agent scaffolding for Claude Code, Cursor, and Codex: commands, skills, subagents,
safety rules, an `.agent/` governance hub, a project-memory subsystem, and OKF docs tooling. This
file is the **source of truth** for how agents build/test/run and which tools they may use.

## Authoring & skill source of truth

- **Canonical** assets are authored under `.claude/` (+ `.agent/`).
- The **`.cursor/`** tree and Codex-native **`.agents/skills/`** + **`.codex/agents/`** trees are
  **generated** by `python scripts/sync_assistant_trees.py` — do not hand-edit generated files.
- When you change a skill/command/agent, run the sync and commit all generated mirrors in the **same PR**
  (see [`.agent/SKILL_CHANGE_AST10_REVIEW.md`](.agent/SKILL_CHANGE_AST10_REVIEW.md)).

## Commands

```bash
# Fill in for ${STACK}
${BUILD_CMD}     # build
${TEST_CMD}      # tests (document the fast subset vs full)
${LINT_CMD}      # lint / typecheck / format
```

## MCP servers

- Define project servers in [`.mcp.json`](.mcp.json) (Claude Code), copy
  [`.cursor/mcp.example.json`](.cursor/mcp.example.json) → `.cursor/mcp.json` (gitignored) for Cursor,
  and use [`.codex/config.toml`](.codex/config.toml) or `~/.codex/config.toml` for Codex.
- **Naming:** `<scope>-<role>-*` (e.g. `${MCP_PREFIX}-data`, `${MCP_PREFIX}-diag`).
- **Surface:** prefer a compact **`search` + `dispatch`** pair over dozens of raw tools when the
  domain is large.
- **Secrets via env only**, never CLI args. Reload the MCP client after changing keys.
- User-level `~/.cursor/mcp.json` holds cross-repo tools; project keys live in this repo.

### Optional: fff file-search MCP

[fff](https://github.com/dmtrKovalenko/fff) provides fast indexed repo search via MCP (`ffgrep`, `fffind`, `fff-multi-grep`). **Opt-in** — clones work without it.

1. Install `fff-mcp` from fff releases (Windows: `%LOCALAPPDATA%\fff-mcp\bin\fff-mcp.exe`; add to PATH).
2. Copy the `fff-mcp` entry from [`.cursor/mcp.example.json`](.cursor/mcp.example.json) `_examples` into gitignored `.cursor/mcp.json`, or register at user level as `fff`.
3. Rename server key to `${MCP_PREFIX}-fff` in bootstrapped projects if desired.
4. Reload MCP in Cursor (Settings → MCP, or restart IDE).
5. Agents: prefer fff for repeated repo-wide search when connected; one-off probes may still use `rg`/`fd` (see `search-tool-selection` skill).

## Available tools

<!-- BEGIN MCP TOOL INVENTORY -->
<!-- Auto-generated; do not edit by hand. Regenerate when your MCP tools change. -->
| Server (example key) | Tools (when fff-mcp connected) | Notes |
|----------------------|--------------------------------|-------|
| `fff-mcp` / `${MCP_PREFIX}-fff` | `ffgrep`, `fffind`, `fff-multi-grep` | Opt-in; see `.cursor/mcp.example.json` |
<!-- END MCP TOOL INVENTORY -->

## Common workflows

`/spec → /plan → /implement → /test-and-fix → /pr-ready`. See
[`docs/ai-workflow/README.md`](docs/ai-workflow/README.md) for the full asset map and loop, and
[`.agent/workflows/`](.agent/workflows/) for playbooks.

## Git configuration — do not modify

Never modify `.git/config` or add non-standard git extensions (do not set
`extensions.worktreeConfig` or change `core.repositoryformatversion`). Embedded git libraries in
third-party tooling choke on non-standard extensions and break workspace resolution. If a worktree is
needed, use a temporary one and clean it up immediately.

## Test vocabulary

If the project has more than one test tier, disambiguate them here (one row per tier) so an agent
knows exactly which suite "E2E" means:

| You say | Canonical name | Where | How to run |
|---------|----------------|-------|------------|
| … | … | … | … |

## Coding-agent contract

- **Code style:** match the surrounding code; follow the repo's formatter/linter.
- **Package boundaries:** touch one module/package per task; use shared types. Do not reach across
  boundaries (UI ↔ data layer ↔ transport) without an explicit contract change.
- **Security (hard rules):** secrets via env/`secrets.json` only; validate external inputs;
  side-effecting/destructive ops require confirmation; never modify `.git/config`. See
  [`docs/security.md`](docs/security.md) and [`.agent/SAFETY.md`](.agent/SAFETY.md).
- **Change control:** minimal diffs, tests for behavior changes, no unrelated refactors.
- **Prohibited:** committing secrets, disabling/weakening tests to go green, drive-by reformatting,
  inventing API paths / config keys / schema names (check
  [`docs/CANONICAL_SOURCES.md`](docs/CANONICAL_SOURCES.md)).

## RCA / Failure Log

Append-only record of **non-obvious failures** and their root causes, so the next agent does not
re-debug them. Add an entry after `/test-and-fix` (or any debugging session) uncovers something
that was not obvious from the error message. Keep entries short: date, symptom, root cause, fix.

| Date | Symptom | Root cause | Fix / guard |
|------|---------|------------|-------------|
| _(none yet)_ | | | |

## AI workspace assets

| Asset | Location |
|-------|----------|
| Claude commands | `.claude/commands/*.md` |
| Claude skills | `.claude/skills/*/SKILL.md` |
| Claude subagents | `.claude/agents/*.md` |
| Claude rules | `.claude/rules/*.md` |
| Cursor mirror (generated) | `.cursor/{rules,commands,skills,agents}` |
| Codex skills (generated) | `.agents/skills/*/SKILL.md` |
| Codex subagents (generated) | `.codex/agents/*.toml` |
| Codex project config | `.codex/config.toml` |
| MCP templates/config | `.mcp.json`, `.cursor/mcp.example.json`, `.codex/config.toml` |
| Agent governance | `.agent/` |
| Project memory | `.agent-memory/` |
| Workflow playbooks | `.agent/workflows/*.md` |
| Workflow index | `docs/ai-workflow/README.md` |
