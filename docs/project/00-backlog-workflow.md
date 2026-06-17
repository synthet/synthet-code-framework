---
type: Runbook
title: Backlog Workflow
description: The canonical backlog/board contract — pick, claim, transition Stage, and reference issues in PRs.
resource: project/00-backlog-workflow.md
tags: [docs, project, backlog, workflow]
timestamp: 2026-06-16T00:00:00Z
okf_version: 0.1
---

# Backlog workflow

The canonical task queue is a **GitHub Project board** (not `TODO.md`). The full agent-facing rules
live in the [`backlog-queue`](../../.claude/skills/backlog-queue/SKILL.md) skill; this page is the
human reference and the place to record your board's IDs.

## The five-step contract

1. **Pick** from `Stage = Ready`, sorted by `priority:p0..p3`. If empty, ask the maintainer — do not
   invent work.
2. **Claim** the issue (`/task-claim <N>`): assigns you and moves the card to `Stage = Claimed`.
3. **In Progress** on your first commit.
4. **Blocked** → move the card to `Stage = Blocked` *and* comment the blocker + what would unblock it.
5. **Reference** the issue in the PR (`Closes #<N>`); move to `Stage = Review` while open; merge
   closes it and flips `Status = Done`.

## Board IDs (fill in per project)

Read them with `gh project field-list <PROJECT_NUMBER> --owner <OWNER>` and record here:

| Thing | Value |
|-------|-------|
| Board URL | `${PROJECT_BOARD_URL}` |
| Owner | `${PROJECT_OWNER}` |
| Project number | `${PROJECT_NUMBER}` |
| Project node id | `${PROJECT_NODE_ID}` |
| Stage field id | `${STAGE_FIELD_ID}` |
| Stage option ids | Backlog / Ready / Claimed / In Progress / Blocked / Review / Done |

These placeholders are also consumed by [`/task-claim`](../../.claude/commands/task-claim.md).
