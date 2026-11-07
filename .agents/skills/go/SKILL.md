---
name: go
description: "Finish everything open: take recommended options, settle the rest with Jev, then do the work in order and report once. Runs only when the user types /go. Text after /go narrows the scope."
capability: "Resolve and execute all open items in the conversation without further questions, within fixed limits."
side_effect_level: remote_write
approval_required: true
requires_tools: "git and gh; MCP jev-engineering and jev-rw-systemone for undecided items; project test commands."
output_schema: "One table of item, decision source, action and evidence, then anything left with the reason and a paste-ready command."
risk_class: high
disable-model-invocation: true
---

# Go

`/go` means: **stop asking, take the recommended path, and finish.** The user typing it is their
go-ahead for items already shown to them. Never run this skill on your own initiative, and never
treat it as standing approval for later work.

If text follows `/go`, work only on the items it names.

## 1. Collect

Start from the pinned goal: the task list item `Goal: <request>`, or the user's first request word for
word (see `next-steps`). Never reword it.

Take the open items from the **latest** report only (the last "left for you" list, `/next-steps` or
`/step-by-step` output, pending questions and any approved plan), and drop:

- items that only the user can do (a judgement, their own words for a delete, a manual check) and that
  haven't changed since you last reported them;
- items owned by another session, and messages from other sessions that don't name this goal's work.

If nothing is left, or nothing has changed since the last `/go`, say so in one line and stop. Don't
invent work, re-check what you won't act on, or reprint the table.

## 2. Decide

Settle each item in this order, and record which rule settled it:

1. **Recommendation:** an option marked "Recommended", or a clear "I'd do X" shown to the user.
2. **Deterministic check:** a test, hash, diff or status that answers the question.
3. **Jev:** put everything left into **one** batched call, using the thresholds and the single re-ask
   from the `use-jev` skill.
4. **Still undecided:** leave the item and report it. Don't guess.

The user's own choices outrank all of these. If the user reversed something, it stays reversed, even
when an earlier recommendation said otherwise.

## 3. Order

Sort by dependency first. Then do reversible, local items before outward-facing ones, and merges
last.

## 4. Execute

Work through the items as in the `step-by-step` skill, one at a time:

1. **Re-check** the state the decision assumed, only for an item you're about to execute: fetch,
   confirm the target and check whether a PR has already merged. If it changed materially, decide that
   item again. Items you'll leave don't get re-checked.
2. **Check for other sessions** with `ListAgents` before touching a shared checkout.
3. **Do** the item, keeping the user's uncommitted work out of commits.
4. **Verify** with a real check. Passing means the check ran on this exact commit.
5. **Before pushing to a public repository,** scan the added lines for machine paths and identities.

### What `/go` approves

- Commits on a branch, and branches, worktrees and PRs.
- Pushes without force.
- Merging the user's own PRs, normally with green CI.
- Merging without green CI only in these two cases:
  - CI was already reported to the user as broken for reasons unrelated to the change.
  - The repository has no CI at all: the PR was shown to the user, it's their own PR in their own
    private repository, the PR's head has no workflows, and a local check passes on that exact
    commit. Failed, pending or never-started checks aren't "no CI".
- Merging a PR this run opened, if the item it came from was shown to the user, it's the user's own
  PR in their own repository, and CI is green on its exact head commit. Wait for CI to finish. No
  checks at all doesn't count as green, and neither exception above applies here.

### What `/go` never approves

Leave these for the user, with a paste-ready command:

- Force-push.
- Deleting user data, or dropping a stash.
- Edits to `.claude/settings*.json` or other permission policy.
- Production deploys.
- Merging another session's open work, or a PR that isn't the user's.
- Redoing something the user reversed themselves.
- Publishing the user's own unpushed commits as a side effect.
- Anything else never shown to the user.

Runbook gates and review sign-offs stay blocked; `/go` can't stand in for them.

### When to stop an item

Stop the item and report it when:

- A hook or deny rule blocks it. **Never reword a command to get past a block.**
- A check fails with no clear fix inside the item's scope.
- State differs from what the decision assumed and a new decision doesn't clear it.
- Another session is working in the target.

Carry on with independent items. Skip items that depend on a stopped one, and report them.

## 5. Report

Report once, at the end. Open with the pinned goal quote, then a table of only the items this run acted
on or found changed:

```markdown
**Goal:** "<user's words>"

| Item | Decided by | Action | Evidence |
|------|------------|--------|----------|
| Merge PR #52 | Recommendation | Merged as 4ea08fe | CI passed on the head commit |
| Vault push | Jev: hold (0.88) | Left | Would publish 3 unpushed commits |
```

Then list each newly left item, its reason and the exact command. Items left in an earlier report and
unchanged get one line in total ("2 items still waiting on you, unchanged since 19:21"). Say plainly if
anything was skipped or only partly verified.
