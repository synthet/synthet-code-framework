---
name: ship-pr
description: "Take one GitHub PR from open to merged: read its failing CI jobs, find the root cause, fix and push, wait for green on the exact head commit, merge, verify and clean up. Runs only when the user types /ship-pr, with a PR number, URL or branch; with none it uses the current branch's PR."
capability: "Fix a pull request's CI failures and merge it once CI is green on its exact head commit, within fixed limits."
side_effect_level: remote_write
approval_required: true
requires_tools: "git and gh; the project's own test commands."
output_schema: "One table of each CI failure with its cause, fix and evidence, then the merge commit, what was verified, and anything left with the reason and a paste-ready command."
risk_class: high
disable-model-invocation: true
---

# Ship PR

`/ship-pr` means: **take this PR from open to merged, fixing CI on the way.** Typing it approves
pushing fixes to this PR's branch and merging this PR, and nothing else. It is not standing approval.
Never run this skill on your own initiative.

One PR per run. If the user names none, use the current branch's PR. If that's ambiguous, stop and ask.

## 1. Confirm the target

Read `gh pr view` for state, author, base, head commit, draft flag, mergeability, review decision and
linked issues, then `gh repo view` for visibility.

- Already merged: report it and stop.
- Stop and report if it isn't the user's PR, is a draft, has changes requested, or another session is
  working on its branch (`ListAgents`). A PR based on another open PR waits for that one.
- Check out the PR's branch without disturbing uncommitted work in a shared checkout. If that isn't
  possible, use a temporary worktree.

## 2. Read CI

Look at the checks for the **exact head commit**.

- **Pending:** wait with a background watch. Don't poll in a loop.
- **An empty conclusion is not a pass.** A check with no result is still running.
- **No checks at all is not green.** Stop and report.
- **Failed:** read the failing step with `gh run view <run> --job <job> --log-failed`.

## 3. Fix

Handle every failing job, one cause at a time.

1. **Reproduce** with the exact command from the workflow file. CI often runs a different command
   from the one you ran locally, such as with coverage on.
2. **Classify** the failure, and name your evidence:

   | Class | Evidence | Action |
   |---|---|---|
   | Caused by this PR | Fails here, passes on the base branch | Fix the code |
   | Already broken on base | The base branch's latest run fails the same way | Stop and report |
   | Flaky test | Force the timing, and show it fail the same way | Fix the race in the test |
   | Infrastructure | The log shows a runner, network or quota error | One rerun, then stop |

3. **Find the root cause before editing.** A test that passes locally and fails in CI is usually a
   race. Force it, for example by delaying a mock, and confirm the same error before changing anything.
4. **Run the steps CI never reached.** A failed step skips everything after it, so more failures can
   be hiding. Run those steps from the workflow file locally before you push.
5. **Treat a local-only failure as unproven.** Ignored files can fail checks that CI would pass.
   Confirm on a clean checkout of the same commit before fixing it.
6. **Fix minimally.** Keep each cause in its own commit, staged by path. Keep unrelated files out.
7. **Push** with `git push origin <branch>`. If the repository is public, first scan the added lines
   for machine paths, identities and credentials. If the branch is behind and needs updating, merge
   the base branch in, because a rebase would need a force-push.
8. **Wait for CI on the new head,** then go back to step 2.

Stop after **three** fix-and-push rounds, and report what you learned. Don't rerun a job in the hope
that it turns green: a rerun can hide a real race.

## 4. Merge

Merging is the last step. Immediately before it, re-read the PR and confirm all of this:

- the head commit is the one CI passed on;
- every required check passed on that commit;
- the PR is mergeable with no conflicts, and no review has changed;
- no new commits arrived.

Use the merge method the repository's recent PRs used, and pin the commit so nothing newer can slip in:

```bash
gh pr merge <number> --merge --delete-branch --match-head-commit <sha>
```

## 5. Verify and clean up

- Confirm the PR shows as merged and its linked issues closed.
- Check CI on the base branch if the merge starts a run there. Report a failure; don't push a fix
  without a new request.
- Return a shared checkout to its default branch, and fast-forward it only if it's clean.
- **Leave worktrees for the user.** Removing a worktree can follow links inside its `node_modules`
  and empty the real folder they point at, including another repository. Give the user the steps
  instead: remove the links first, then the worktree.

## Never

Leave these for the user, with a paste-ready command where one helps:

- Force-push, or merging with admin rights to get past branch protection.
- Weakening a check to pass it: skipping or deleting tests, loosening assertions, raising timeouts or
  coverage thresholds, or skipping commit hooks. A timeout may change only with evidence that the
  limit itself is the bug.
- Changing a CI workflow or a required check, unless that file is the proven cause and the PR is
  about it.
- Editing permission policy, or tagging, releasing or deploying.
- Merging any PR other than the one named.

## When to stop

Stop and report when:

- A hook or deny rule blocks a command. **Never reword a command to get past a block.**
- A failure has no clear fix inside this PR's scope.
- The fix would change what the PR does, or needs a product decision.
- Conflicts need a judgment call about someone else's work.
- The PR's state changes under you, or another session starts working on it.

Stopping is a good result. A blocked PR with a clear reason beats a green one that hides a problem.

## Report

Report once, at the end:

```markdown
| Failure | Class | Fix | Evidence |
|---------|-------|-----|----------|
| KeepOne test | Flaky test | abc1234: wait for the load | Forced the race; same error, then passes |
```

Then give the merge commit, what ran on the final commit, anything skipped, and each item left with
its reason and command. Say plainly what wasn't verified, and any cause you didn't establish.
