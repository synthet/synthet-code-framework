---
name: step-by-step
description: Use when executing an approved plan or complex task incrementally, one verifiable step at a time, running validation after each step and continuing until every feasible step is done. Apply when the user says "step by step", "one step at a time", "execute plan incrementally", "work through the list", or types /step-by-step.
capability: "Execute multi-step plans to completion with a success check per step, surgical edits and one final evidence table."
side_effect_level: local_write
approval_required: false
requires_tools: "git status, git diff, project build/test/lint commands; the harness task list when available."
output_schema: "One line per finished step, then a final table of step, status and evidence."
risk_class: medium
---

# Step-by-step

Carry the plan all the way to done, proving each step as you go. The user can walk away and come back to
finished, verified work, not a checklist that stopped after step 1.

How this differs from neighbours:
- `/step-by-step` carries out a plan to completion, one verified step at a time.
- `/implement` carries out an approved plan in a single pass.
- `/next-steps` reports what's finished and what's left.
- `/go` decides open questions and finishes the items without asking.

## 1. Find the plan

Use the first that exists: the user's message, a plan in this conversation, a plan or checklist file, the
latest `/next-steps` report. With none, write a short plan from the request.

Quote the pinned goal (the task list item `Goal: <request>`, or the user's first request word for word; see
`next-steps`). Never reword it.

**The user typing `/step-by-step` on a list is their go-ahead for it.** Claim every item you can do
yourself, including ones the list handed to the user that you could do:

- "Reply X and I'll do it", "say 'check replay'" or a paste-ready `!` command you're allowed to run: these
  are your steps. Do them.
- Committing on a branch, pushing a non-default branch without force and opening a PR, when the list showed
  that item: your steps. Merging, deploying, deleting data and editing permission policy stay with the user
  (or `/go`).
- A decision with a recommended, reversible option: take it, note "chose X (recommended)", carry on.
- A decision with no recommendation, or one that's irreversible: ask it **once, before you start**, in one
  consolidated question, then do every step that doesn't depend on the answer.
- Waiting on a job or CI: don't stop. Do the independent steps first, then wait with a background watcher
  or monitor (CI and jobs due within about 15 minutes). For longer waits, leave a watcher running and say
  when it'll fire.
- Items held by another session aren't yours. Mention them once at the end.

Stop with "nothing to do" only when every item really is the user's own judgement or someone else's work,
and then say in one line what would make it actionable. Don't re-check or reprint the list.

For each step, write down before doing it:
- **Action:** what you'll do, and the files it touches.
- **Success check:** an objective test, such as a command and its expected exit code or output, a test
  that should pass, or a number that should match. "Looks right" isn't a check.

Put the steps in the task list when one is available.

## 2. The loop

For each step, in dependency order:

1. **Do it.** Touch only this step's files. No drive-by formatting, renames or refactors.
2. **Validate.** Run the success check and read the real output. A command that didn't crash hasn't
   passed.
3. **Record** one line: `Step 2/5 done: 12/12 tests pass`. Don't reprint the checklist or narrate.
4. **Decide:**
   - Passed: move on to the next step without waiting for the user.
   - Failed: find the cause, fix it, check again. If the same fix fails twice, try a different approach.
     After about 3 real attempts, mark the step blocked with what you learned and carry on with steps that
     don't depend on it.
   - The check itself was wrong: fix the check and say so. Don't quietly lower the bar.

When a later step could have broken an earlier one, re-run the earlier check too.

## 3. When to stop

Keep going through every feasible step. Pause only for:
- **Irreversible or outward-facing actions the list didn't show**: deleting data, force-push, merges,
  deploys, sending messages, spending money, or changing permissions or shared config. Prepare everything up
  to that point, state the decision, and stop that step only.
- **Real ambiguity**, where a wrong guess would waste substantial work.
- **Missing access**: credentials, files or permissions you don't have.

A blocked step doesn't end the run. Skip it, finish the independent steps, and report it.

## 4. Finish

Run an end-to-end check of the whole result, then report once:

```markdown
**Goal:** "<user's words>"

| # | Step | Status | Evidence |
|---|------|--------|----------|
| 1 | … | Done | tests 12/12 |
| 2 | … | Blocked | needs API key |

**Needs you:** … (one line per item; unchanged items from earlier reports as one line in total)
**Next step:** <one, if any>
```

Clean up scratch files and temporary hacks you added, or list the ones that must stay.
