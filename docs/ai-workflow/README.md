---
type: Documentation Hub
title: AI Workflow & Asset Map
description: Where every agent asset lives (rules, commands, skills, agents, memory, workflows) and the SDLC loop they support.
resource: ai-workflow/README.md
tags: [docs, agents, workflow]
timestamp: 2026-06-16T00:00:00Z
okf_version: 0.1
---

# AI workflow & asset map

## Where agent assets live

| Asset | Location | Notes |
|-------|----------|-------|
| Claude commands | `.claude/commands/*.md` | **Canonical** authoring source |
| Claude skills | `.claude/skills/*/SKILL.md` | **Canonical** authoring source |
| Claude subagents | `.claude/agents/*.md` | **Canonical** authoring source |
| Claude rules | `.claude/rules/*.md` | Always-on guidance |
| Cursor mirror | `.cursor/{rules,commands,skills,agents}` | **Generated** from `.claude/` — do not edit by hand |
| MCP template | `.cursor/mcp.example.json`, `.mcp.json` | Copy to gitignored `.cursor/mcp.json` to attach servers |
| Agent governance | `.agent/` | Safety, inventory, subagent role matrix, workflow playbooks |
| Project memory | `.agent-memory/` | log → dream → promote (see `CURSOR_USAGE.md`) |
| Workflow playbooks | `.agent/workflows/*.md` | spec / plan / implement / pr-ready / test-and-fix / … |

**Single source of truth:** edit assets under `.claude/` + `.agent/`, then run
`python scripts/sync_assistant_trees.py` to regenerate the `.cursor/` mirror.

## The SDLC loop

```
/spec  →  /plan  →  /implement  →  /test-and-fix  →  /pr-ready  →  (optional) /subagent-review  →  /release-notes
```

- **Backlog first:** pick and claim work via the [backlog contract](../project/00-backlog-workflow.md) (`/task-claim`).
- **Review:** `/critical-commit-audit` for high-severity bug hunts; `/check-subagents` +
  `/run-codex-review` / `/run-gemini-review` for external second opinions.
- **Docs:** `/wiki-ingest`, `/wiki-lint`, `/wiki-query` keep `docs/` healthy (see [WIKI_SCHEMA](../WIKI_SCHEMA.md)).
- **Memory:** `/log-session` → `/dream-memory` → `/promote-memory` → `/memory-context`.

## Safety

All of the above operate under [`.agent/SAFETY.md`](../../.agent/SAFETY.md) and
[`security.md`](../security.md).
