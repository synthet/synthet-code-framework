---
name: commit-and-push
description: Use when the user asks to commit and push, publish, ship, or prepare a release commit. Guides staging only intended changes, writing a Conventional Commit, committing, and pushing to origin after verifying status and diff.
capability: "commit-and-push agent asset workflow"
side_effect_level: local_write
approval_required: false
requires_tools: "python .claude/skills/commit-and-push/scripts/harness.py; git; gh optional"
output_schema: "Inspect/verify report; commit/push only when explicitly executed"
risk_class: medium
---

# Commit and push (compiled harness)

Ship local work only when the user explicitly asks. Pair with `release-bump` when
`VERSION` / `CHANGELOG.md` were promoted.

## Invoke

```bash
# Dry-run inspect (default)
python .claude/skills/commit-and-push/scripts/harness.py --json

# Release prep: list + run framework verify
python .claude/skills/commit-and-push/scripts/harness.py --release --run-verify --json

# Only after explicit user request to commit/push:
python .claude/skills/commit-and-push/scripts/harness.py \
  --execute --commit -m "feat(scope): summary" --json
python .claude/skills/commit-and-push/scripts/harness.py --execute --push --json
```

## LLM judgment slots

- Draft Conventional Commit subject/body (`commit-conventions`).
- Prefer explicit path staging when unrelated dirty files exist (inspect `paths` first).
- **Shared checkouts:** before writing in a repo, `git fetch` and check `HEAD..origin/<default>` and peer sessions; commit on a branch but return the checkout to its default branch; stage only your hunks when a file also holds someone else's edits; regenerate generated files in a clean worktree. Recipes: [references/shared-checkouts.md](references/shared-checkouts.md). Why: other sessions merge, switch branches and commit in the same checkout.
- **Repository visibility:** before pushing or recommending a push, run `gh repo view --json visibility`. If it's `PUBLIC`, first scan the added lines for machine paths and identities. Why: a public push can be copied at once, so deleting it later doesn't undo it.

## Human / safety (enforced)

- Harness **defaults to dry-run**; `--execute` required for commit/push.
- Secret-looking paths (`.env`, `secrets.json`, keys) block staging.
- Never modify `.git/config`, never `--no-verify` unless user asked.
- Branch-tracking entries count as `.git/config` writes: push with `git push origin <branch>`, never `-u`, and add `--no-track` when a new branch starts from a remote ref.
- Never force-push `main`/`master` unless user asked.
- Do not amend after a failed hook — new commit instead.
