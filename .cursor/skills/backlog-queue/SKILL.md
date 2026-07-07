---
name: backlog-queue
description: A GitHub Project board is the canonical task queue. Use whenever picking work, claiming an issue, transitioning Stage, or filing/closing a backlog issue.
capability: "backlog-queue agent asset workflow"
side_effect_level: remote_write
approval_required: true
requires_tools: "See asset body for tool requirements."
output_schema: "Markdown report or documented command output."
risk_class: medium
---

# Backlog queue

> The canonical task queue is a GitHub Project board: **${PROJECT_BOARD_URL}**
>
> `TODO.md` files (if any) are pointers only — **never** add tasks there.
>
> **Setup:** fill the `${...}` placeholders (board URL, owner, project/field/option IDs) from your
> own Project before first use. Read them with `gh project field-list <N> --owner <OWNER>`.

## When to use

- The user asks to pick the next task, start work, or "what's next".
- The user asks to file a new backlog item.
- A PR is being prepared and needs a `Closes #N` reference.
- A task has hit a blocker, is ready for review, or is finished.
- The user mentions `Stage`, `Ready`, `Backlog`, `Claimed`, `Blocked`, `Review`, or `Done`.
- An agent picks up a task without a corresponding issue — stop and file one first.

## The five-step contract

Every contributor (human or AI) follows the same five steps. Do **all** of them; skipping a step
puts the queue out of sync.

### 1. Pick from `Stage = Ready`

Open the board, filter to **Stage = Ready**, sort by `priority:p0..p3`. Pick the highest-priority
unassigned card. If `Ready` is empty, stop and ask the maintainer to promote items from `Backlog`.
**Do not invent new work.**

### 2. Claim the issue

Use `/task-claim <issue-number>` (preferred) or `gh` directly: verify the issue is claimable,
`--add-assignee @me`, find the project item id, and move it to the `Claimed` option. The exact
`gh` commands + IDs live in [`/task-claim`](../../commands/task-claim.md).

### 3. Flip to `In Progress` on first commit

Move the card to the `In Progress` option (`${STAGE_IN_PROGRESS_ID}`).

### 4. If blocked, mark + comment

Move to `Blocked` (`${STAGE_BLOCKED_ID}`) **and** comment the reason + unblock condition:

```bash
gh issue comment <N> --repo $OWNER/<repo> --body "Blocked: <reason + what would unblock>."
```

### 5. PR references the issue

Your PR description **must** contain `Closes #<N>`. Move the card to `Stage = Review`
(`${STAGE_REVIEW_ID}`) when opening the PR. On merge, manually move `Stage = Done`
(`${STAGE_DONE_ID}`).

## Filing a new task

1. Confirm there isn't already an issue (`gh issue list --search "<keywords>"`).
2. Open the issue with title, body, and labels matching the taxonomy below.
3. Add to the board: `gh project item-add ${PROJECT_NUMBER} --owner $OWNER --url <issue-url>`.
4. Set `Stage = Backlog` by default; promote to `Ready` only with maintainer signoff.

## Label taxonomy (adapt per project)

| Family | Example values |
|--------|----------------|
| `area:*` | one per major module/domain of your repo |
| `priority:*` | `p0`, `p1`, `p2`, `p3` |
| `type:*` | `bug`, `feature`, `refactor`, `test`, `chore`, `epic` |
| (special) | `cross-repo` (multi-repo programs) |
| (status) | `status:obsolete` — superseded/deferred; stays open on Backlog |

### Epics

- Parent issues use `type:epic` and link children via **GitHub sub-issues** (same repo).
- Cross-repo programs: one epic per repo + `cross-repo` label + counterpart URL in the body.

## Reference IDs (fill in per project)

| Thing | ID |
|-------|----|
| Project node id | `${PROJECT_NODE_ID}` |
| Project number | `${PROJECT_NUMBER}` |
| Owner | `${PROJECT_OWNER}` |
| `Stage` field id | `${STAGE_FIELD_ID}` |
| `Backlog` option | `${STAGE_BACKLOG_ID}` |
| `Ready` option | `${STAGE_READY_ID}` |
| `Claimed` option | `${STAGE_CLAIMED_ID}` |
| `In Progress` option | `${STAGE_IN_PROGRESS_ID}` |
| `Blocked` option | `${STAGE_BLOCKED_ID}` |
| `Review` option | `${STAGE_REVIEW_ID}` |
| `Done` option | `${STAGE_DONE_ID}` |

## Don'ts

- **Don't** add tasks to `TODO.md`.
- **Don't** start work on an issue without claiming it (assignee + Stage transition).
- **Don't** silently abandon a `Claimed` or `In Progress` card — move to `Blocked` with a comment.
- **Don't** open a PR without `Closes #N`.
- **Don't** skip Stage transitions — drift makes the queue lie about who's doing what.

## Mirrors

This skill is mirrored to `.cursor/skills/backlog-queue/SKILL.md`. `.claude/` is canonical — keep
them aligned (regenerate via `python scripts/sync_assistant_trees.py`).
