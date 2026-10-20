---
name: step-by-step
description: Use when executing an approved plan or complex task incrementally, one verifiable step at a time, running validation after each step before proceeding to the next. Apply when the user says "step by step", "one step at a time", "execute plan incrementally", or types /step-by-step.
capability: "Execute multi-step plans incrementally with per-step surgical edits, validation gates, and progress reporting."
side_effect_level: local_write
approval_required: false
requires_tools: "git status, git diff, project build/test/lint commands."
output_schema: "Per-step execution logs, test outputs, checklist progress, and checkpoint summaries."
risk_class: medium
---

# Step-by-step

## Purpose

Execute an approved plan or complex coding task incrementally—one discrete, verifiable step at a time. This prevents the primary failure mode of AI coding agents: making sweeping, unverified changes across multiple modules that break builds and make regression attribution difficult.

How this differs from neighbours:
- `/step-by-step` executes an approved plan one verified step at a time.
- `/implement` executes an approved plan in a standard single-pass implementation loop.
- `/next-steps` audits and reports what is finished vs remaining in the conversation.

## When to Use

Apply this skill when:
- The user explicitly asks for "step by step", "one step at a time", or types `/step-by-step`.
- A task has an approved multi-step plan with distinct dependencies.
- Performing delicate refactors, schema migrations, or multi-module wiring where failure isolation is essential.

## Core Rules

1. **One Step at a Time**
   - Announce the step being worked on: `### Executing Step X of Y: [Step Name]`.
   - Touch only the files designated for this step. Do not jump ahead to subsequent steps.

2. **Surgical, Minimal Edits**
   - Apply the minimum code necessary to satisfy the current step's acceptance criteria.
   - Do not perform drive-by formatting, renames, or refactors outside this step's boundary.

3. **Immediate Deterministic Verification**
   - Immediately run the narrowest verification check:
     - Targeted unit test: `npm test -- -t "name"`, `pytest path/to/test.py -k "name"`
     - Static check: `npm run typecheck`, `tsc --noEmit`, `cargo check`
     - Focused linter: `npm run lint`, `ruff check <file>`
   - Confirm the step actually passes before declaring it complete. Never guess or assume compilation succeeded.

4. **Progress Checkpoint**
   - Mark the step complete in the overall progress checklist.
   - Summarize the specific verified behavior and state what the next step will address.
   - Pause for user approval if the user requested interactive step-by-step guidance.

## Standard Checkpoint Template

After each step, report progress in this compact structure:

```markdown
### Step X: [Step Name] — Complete
- **Changes applied:** `path/to/file` (lines L..M)
- **Verification:** Ran `<command>` -> Exit 0 (passed)
- **Progress:**
  - [x] Step 1: [Name]
  - [x] Step X: [Name] (Completed)
  - [ ] Step X+1: [Next Step Name]
- **Ready for Step X+1:** [Brief 1-line summary of what will be done next]
```
