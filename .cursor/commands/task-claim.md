> **Claude Code:** Same intent as Cursor `/task-claim`. When customizing, keep in sync with `.cursor/commands/task-claim.md`.

# /task-claim — claim a board issue and move it to Stage=Claimed

Use when starting work on a backlog item. `$ARGUMENTS` is the issue number (and optional repo).

**Usage:**
```
/task-claim <issue-number> [--repo <repo>]
```

If `--repo` is omitted, default to the current repo.

> **Setup:** fill the placeholders below from your GitHub Project before first use, then commit.
> See [`docs/project/00-backlog-workflow.md`](../../docs/project/00-backlog-workflow.md) for how to
> read the project/field/option IDs (`gh project field-list <N> --owner <OWNER>`).

## Action

Run the steps in order. Stop and report on any failure — do not proceed to the next step.

### 1. Resolve repo + verify the issue is claimable

```bash
OWNER="${PROJECT_OWNER}"
REPO="${PROJECT_REPO}"           # override via --repo
N="<issue-number>"

# Confirm the issue exists, isn't closed, and isn't already assigned to someone else.
gh issue view "$N" --repo "$OWNER/$REPO" --json number,state,assignees,title
```

If `state == "CLOSED"`, abort: report "issue is closed".
If `assignees` is non-empty and you are not in it, abort: report who has it (require explicit override).

### 2. Assign yourself

```bash
gh issue edit "$N" --repo "$OWNER/$REPO" --add-assignee @me
```

### 3. Find the project item id

```bash
ITEM_ID=$(gh project item-list ${PROJECT_NUMBER} --owner "$OWNER" --format json --limit 200 \
  | jq -r --argjson n "$N" --arg repo "$REPO" '
      .items[]
      | select(.content.number == $n)
      | select((.content.repository // "") | endswith($repo))
      | .id')

if [ -z "$ITEM_ID" ]; then
  echo "ERROR: issue #$N is not on the Project board"
  exit 1
fi
```

### 4. Move the card to `Stage = Claimed`

```bash
gh project item-edit \
  --id "$ITEM_ID" \
  --project-id ${PROJECT_NODE_ID} \
  --field-id ${STAGE_FIELD_ID} \
  --single-select-option-id ${STAGE_CLAIMED_ID}
```

### 5. Confirm + remind

Report back to the user:

- Issue URL: `https://github.com/$OWNER/$REPO/issues/$N`
- Title (from step 1)
- "Claimed. Move to `Stage = In Progress` (option id `${STAGE_IN_PROGRESS_ID}`) on your first commit.
  PR description must include `Closes #$N`."

## Reference IDs (fill in per project)

| Thing | ID |
|-------|----|
| Project node id | `${PROJECT_NODE_ID}` |
| Stage field id | `${STAGE_FIELD_ID}` |
| Backlog | `${STAGE_BACKLOG_ID}` |
| Ready | `${STAGE_READY_ID}` |
| Claimed | `${STAGE_CLAIMED_ID}` |
| In Progress | `${STAGE_IN_PROGRESS_ID}` |
| Blocked | `${STAGE_BLOCKED_ID}` |
| Review | `${STAGE_REVIEW_ID}` |
| Done | `${STAGE_DONE_ID}` |

Full contract: [`docs/project/00-backlog-workflow.md`](../../docs/project/00-backlog-workflow.md).
