---
capability: "plan agent asset workflow"
side_effect_level: local_write
approval_required: false
requires_tools: "See asset body for tool requirements."
output_schema: "Markdown report or documented command output."
risk_class: medium
---

> **Claude Code:** Same intent as Cursor `/plan`. When customizing, keep in sync with `.cursor/commands/plan.md`.

# /plan — Implementation plan

Use after a spec exists (or for small tasks, a verbal agreement). Prefer **plan mode** or explicit user approval before large edits.

## Inputs

- Approved spec or tight task description.
- Relevant files the user pointed at.

## Output

1. **Goal** — What “done” means.
2. **Files / areas to touch** — Paths or components.
3. **Approach** — Steps in order; call out risky changes.
4. **Tests** — Failing test stubs to write *before* touching implementation, derived from spec
   acceptance criteria. List the test file paths and the assertion names.
5. **Rollback / flags** — If feature-flagged or migratory.

## Done when

- Another developer could execute the plan without guessing.
- Failing test stubs (step 4) are identified and ready to write before implementation begins.
- Test plan matches project conventions.

## Note

If the user has not approved implementation, **do not** apply code changes until they confirm.
