---
name: next-steps
description: Use when the user asks what to do next, what remains, asks for next steps, summarizes progress, or types /next-steps. Evaluates current session progress, inspects working tree diffs, audits verification evidence, and produces an actionable, prioritized roadmap for continuing.
capability: "Report conversation status, audit verification evidence, and generate prioritized next steps."
side_effect_level: read_only
approval_required: false
requires_tools: "git status, git diff, project test/lint commands."
output_schema: "Status summary, verification audit, prioritized next steps with runnable commands."
risk_class: low
---

# Next steps

## Purpose

Report status for the work *in this conversation*, reconcile claims against the actual working tree, audit verification evidence, and provide immediate, prioritized next actions.

How this differs from neighbours:
- `/next-steps` reports status and roadmap for the work *in this conversation*.
- `/step-by-step` executes an approved plan one step at a time.
- `/resume-task` recovers a thread from *earlier sessions across tools*, then hands off here.

## When to Use

Apply this skill when:
- The user asks "what's next?", "what are our next steps?", "where are we?", "what remains?", or types `/next-steps`.
- An implementation phase or milestone has just completed.
- Wrapping up an agent session or preparing for review.
- Handing off the current workspace to another agent or developer.

## Core Workflow

1. **Working Tree & History Audit**
   - Run `git status --short` to see all staged, unstaged, and untracked changes.
   - Inspect recent diffs (`git diff --stat`) to verify what files were actually modified.
   - Reconcile with the active request or approved specification.

2. **Verification State Audit**
   - Check what verification actually ran in this session with passing exit codes (e.g. `npm run typecheck`, test suites, linters).
   - Flag any modified code that lacks test execution or fresh command receipts.
   - Note warnings, skipped tests, or regressions.

3. **Triage Remaining Work**
   - **Critical Path:** Must be completed to satisfy user request and project acceptance criteria.
   - **Verification & Hygiene:** Tests, linter, typecheck, or manual probes required before committing.
   - **Deferred:** Useful improvements or cleanup that are out of scope for the current task.

4. **Produce Actionable Next Steps**
   - Keep to 2–4 prioritized, concrete actions.
   - For each step, provide:
     - Specific files/components affected.
     - Observable outcome (how to know it worked).
     - Exact runnable command or paste-ready prompt.

## Output Format

Present the findings cleanly:

```markdown
### 1. Active Goal
[Brief 1-line statement of the current task and its scope]

### 2. Completed & Verified
- [Feature/Fix] — Verified via `<command>` (Exit 0)
- [Feature/Fix] — Tested in `<file>`

### 3. Unverified or Remaining
- [Item needing test or code edit]

### 4. Immediate Next Steps (Prioritized)
1. **[Step Name]**: [Description]
   - *Target:* `path/to/file`
   - *Command/Action:* `npm test ...`
2. **[Step Name]**: [Description]
   - *Target:* `path/to/file`
```
