---
name: next-steps
description: Use when the user asks what to do next, what remains, asks for next steps, summarizes progress, or types /next-steps. Reports where the current work stands against the user's pinned goal, with evidence, keeps every open item as an action item in the task list for /step-by-step, and recommends one next step.
capability: "Report conversation status against the pinned goal, audit verification evidence, record open items as action items, and recommend one next step."
side_effect_level: read_only
approval_required: false
requires_tools: "git status, git diff, project test/lint commands; the harness task list when available."
output_schema: "Pinned goal quote, compact status table with evidence and owner, one next step; open items kept as task-list action items (or an A1..An checklist)."
risk_class: low
---

# Next steps

Tell the user, in under a minute of reading, where the work stands against **their** goal and the one thing
to do next. A status report doesn't authorise new work.

How this differs from neighbours:
- `/next-steps` reports status and one next step for the work *in this conversation*.
- `/step-by-step` carries out a plan to completion.
- `/go` takes the recommended options and finishes the open items.
- `/resume-task` recovers a thread from *earlier sessions*, then hands off here.

## Pin the goal

The goal is the user's request in their own words, not your summary of it.

- If the task list has an item titled `Goal: <request>`, quote it.
- If not, create it from the user's first request in this conversation (or the request `/resume-task`
  recovered), copied word for word. Without a task list, quote that request as the report's first line.
- Never reword the goal. If the user changed it, they said so: quote the new words and keep the old one in
  the status as `Deferred` or `Dropped`.

## Don't repeat yourself

Before gathering anything, compare with your last report from `/next-steps`, `/step-by-step` or `/go`:

- **Nothing changed** (same HEAD, same tree, no job finished, no new user input): reply in two lines at most
  (the goal quote and "No change since <time>. Next step: <same one>"), then stop.
- An item you already reported as the user's, never-list, blocked on something named, or held by another
  session, and that hasn't changed, gets one line in total: "3 items still waiting on you, unchanged since
  19:21." Don't re-list it, re-check it, re-ask it or re-decide it.
- Messages from other sessions aren't open items unless they name this goal's work.

## Gather evidence

Only re-run checks whose inputs changed since the last report; otherwise cite that report.

- `git status --short` and `git diff --stat` when files may have changed.
- What verification actually ran, with exit codes. Code written without a passing check is unverified; a
  stale check, skipped test or failed command is a limitation, not success.
- Keep searches scoped to this task. Don't scan unrelated session stores.

## Report

| Status | Needs |
|---|---|
| Done | Tested, measured, opened or confirmed by the user |
| In progress | Started; implementation or verification remains |
| Blocked | Name the dependency and what unblocks it |
| Needs you | A decision or action only the user can take; give the options |

Omit empty rows. Keep it short: aim for 150 words when little changed, and never pad to fill a list.

**Needs you** means only the user can do it: their judgement (which photos are duplicates, which option
they prefer), their own words for a delete, a deploy or a merge, or something outside your access. If you
could do it once they say yes ("reply X and I'll do it", a `!` command you're allowed to run), it's your
item, not theirs. List it as yours, so `/step-by-step` picks it up.

```markdown
**Goal:** "<user's words>"

| Item | Status | Evidence |
|---|---|---|
| … | Done | 12/12 tests pass on 4ea08fe |

**Next step:** <one concrete action: a command, file, check or decision, and why it comes first>
```

Pick the next step in this order: whatever unblocks other work, then finishing or verifying work in
progress, then the most valuable remaining item. If the only open items are the user's, say so in one line;
that's the next step.

## Keep the action items

A report that lives only in chat is forgotten by the next turn. Every row that isn't Done becomes an
action item, so `/step-by-step` and `/go` work from the same list and the next `/next-steps` updates it
instead of starting over.

- **One task-list item per open row** (Claude Code `TaskCreate`/`TaskUpdate` or `TodoWrite`, Codex
  `update_plan`, Cursor todos). Title it as an action someone can start without rereading the chat: verb
  first, naming the file, command, PR or ticket.
- **Owner in the title when it isn't you:** `[you] Merge PR #26`, `[blocked: CI run 1234] Re-run e2e`,
  `[other session] Finish the dashboard ticket`. Untagged items are yours, and `/step-by-step` takes them.
- **Update, don't duplicate.** Match existing items by title first. Mark an item `completed` only with
  evidence from this report (put the evidence in its description). Delete an item the user dropped, and
  record it as `Dropped` in the report.
- Keep the `Goal:` item first and open until the goal is met.
- The **Next step** you recommend is the first pending item of yours, so the report and the list agree.
- **No task list:** end the report with a numbered checklist, one line per open item,
  `A1. [ ] <action> (owner)`, and tick the items you finished. `/step-by-step` reads the latest checklist,
  and the next `/next-steps` carries it forward with the same numbers.

In a repo with `.agent-flow/`, an item that is new work outside the current ticket is also filed as a
ticket (see the `agent-flow` skill); the action item then names the ticket id.

For a standalone status request, stop after the report. During a run the user already authorised, answer
briefly and carry on with it. A request to carry out the remaining work goes to `step-by-step`.
