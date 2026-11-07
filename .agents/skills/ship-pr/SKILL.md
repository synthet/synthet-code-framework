---
name: ship-pr
description: "Take one GitHub PR from open to merged: read its failing CI jobs, find the root cause, fix and push, wait for green on the exact head commit (in a repository with no CI, a local run of its documented checks on that commit), merge, verify and clean up. Runs only when the user types /ship-pr, with a PR number, URL or branch; with none it uses the current branch's PR."
capability: "Fix a pull request's CI failures and merge it once CI is green on its exact head commit (or, with no CI, once its documented checks pass locally on that commit), within fixed limits."
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

## 2. Monitor CI

Monitoring CI is a required step. **Never merge until a watch on the exact head commit has finished
and passed,** even when the checks already look green. A new commit on the PR restarts this step.

1. **Wait for checks to register.** A fresh push can show no checks for a minute or two. Wait up to
   five minutes before treating that as no checks.
2. **Watch in the background.** Don't poll in a loop.

   ```bash
   gh pr checks <number> --watch --interval 30 > /dev/null
   ```

   The exit status is the result, so nothing may follow the watch. A trailing `echo` or a pipe to
   `tail` reports success whatever happened.
3. **Read the results for the exact head commit.**
   - **An empty conclusion is not a pass.** A check with no result is still running.
   - **No checks at all is not green.** Find out which of these it is:
     - **CI exists but didn't run.** The base or head branch has workflow files, recent base commits
       have check runs or commit statuses, or branch protection requires checks. Stop and report:
       the workflow may skip these paths, or be disabled or broken.
     - **The repository has no CI.** Neither branch has workflow files, and neither the head commit
       nor the base branch's latest commits have any check runs or commit statuses. Go to step 2a,
       which takes the place of the watch.
   - **Failed:** read the failing step with `gh run view <run> --job <job> --log-failed`.

## 2a. No CI: run the project's checks locally

With no CI, the merge gate is a local run of the project's own checks on the exact head commit.
Typing `/ship-pr` on such a repo accepts that gate.

1. **Find the commands.** Use the test command the project documents (`AGENTS.md`, `CLAUDE.md`, the
   README, or a task runner such as `package.json` scripts or a Makefile), plus any documented lint or
   typecheck. If the project documents none, stop and report: there is nothing to gate on.
2. **Run them on a clean checkout of the head commit,** in a temporary worktree
   (`git worktree add --detach <tmp> <sha>`). Ignored or uncommitted files in the main checkout can
   pass a check that the commit itself would fail. Reuse the project's existing environment, such as
   its virtualenv, unless the PR changes dependency files; then install the documented way.
3. **Every command must exit 0.** A failure goes through step 3 like a CI failure, with the local
   command in place of the workflow's. A new commit means a new run.
4. **Branch protection still applies.** If `gh pr view` shows `mergeStateStatus` `BLOCKED`, stop and
   report: the repository requires something this run can't provide.

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
8. **Wait for CI on the new head,** then go back to step 2. With no CI, rerun step 2a on the new head.

Stop after **three** fix-and-push rounds, and report what you learned. Don't rerun a job in the hope
that it turns green: a rerun can hide a real race.

## 4. Merge

Merging is the last step. Immediately before it, re-read the PR and confirm all of this:

- the head commit is the one the step 2 watch, or the step 2a local run, passed on;
- every required check passed on that commit;
- the PR is mergeable with no conflicts, and no review has changed;
- no new commits arrived.

Use the merge method the repository's recent PRs used, and pin the commit so nothing newer can slip in:

```bash
gh pr merge <number> --merge --delete-branch --match-head-commit <sha>
```

## 5. Verify and clean up

- Confirm the PR shows as merged and its linked issues closed.
- Monitor CI on the base branch the same way. List the runs for the merge commit, allowing up to five
  minutes for them to start, and watch each with `gh run watch <id> --exit-status > /dev/null`. The
  run isn't finished until they have all completed. Report a failure; don't push a fix without a new
  request. With no CI there is nothing to watch; say so.
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

Then give the merge commit, what ran on the final commit, the base branch CI result, anything
skipped, and each item left with its reason and command. Say plainly what wasn't verified, and any cause you didn't establish.
When step 2a was the gate, say the merge rested on a local run, list each command with its result,
and suggest adding CI.
