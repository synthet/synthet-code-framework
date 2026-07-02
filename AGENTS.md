# AI Agents Configuration — ${PROJECT_NAME}

## Overview

This repo ships agent scaffolding for Claude Code and Cursor: slash commands, skills, subagents,
safety rules, an `.agent/` governance hub, a project-memory subsystem, and OKF docs tooling. This
file is the **source of truth** for how agents build/test/run and which tools they may use.

## Authoring & skill source of truth

- **Canonical** assets are authored under `.claude/` (+ `.agent/`).
- The **`.cursor/`** tree (rules/commands/skills/agents) is **generated** by
  `python scripts/sync_assistant_trees.py` — do not hand-edit it; edit `.claude/` and re-run sync.
- When you change a skill/command/agent, run the sync and commit both trees in the **same PR**
  (see [`.agent/SKILL_CHANGE_AST10_REVIEW.md`](.agent/SKILL_CHANGE_AST10_REVIEW.md)).

## Commands

```bash
# Fill in for ${STACK}
${BUILD_CMD}     # build
${TEST_CMD}      # tests (document the fast subset vs full)
${LINT_CMD}      # lint / typecheck / format
```

## MCP servers

- Define project servers in [`.mcp.json`](.mcp.json) (Claude Code) and copy
  [`.cursor/mcp.example.json`](.cursor/mcp.example.json) → `.cursor/mcp.json` (gitignored) for Cursor.
- **Naming:** `<scope>-<role>-*` (e.g. `${MCP_PREFIX}-data`, `${MCP_PREFIX}-diag`).
- **Surface:** prefer a compact **`search` + `dispatch`** pair over dozens of raw tools when the
  domain is large.
- **Secrets via env only**, never CLI args. Reload the MCP client after changing keys.
- User-level `~/.cursor/mcp.json` holds cross-repo tools; project keys live in this repo.

## Available tools

<!-- BEGIN MCP TOOL INVENTORY -->
<!-- Auto-generated; do not edit by hand. Regenerate when your MCP tools change. -->
_(none yet)_
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
| MCP templates | `.mcp.json`, `.cursor/mcp.example.json` |
| Agent governance | `.agent/` |
| Project memory | `.agent-memory/` |
| Workflow playbooks | `.agent/workflows/*.md` |
| Workflow index | `docs/ai-workflow/README.md` |
