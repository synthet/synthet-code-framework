# /spec — Feature or change specification

Use when starting non-trivial work. Produce a **spec** the user can review before implementation.

## Inputs

- Problem statement or feature request.
- Constraints: time, scope, tech stack (see [AGENTS.md](../../AGENTS.md)).

## Steps

1. **Research** the context of the requested change.
2. **Draft the Spec** containing:
    - **Summary**: One paragraph.
    - **Users / stakeholders**: Who benefits.
    - **Non-goals**: What is explicitly out of scope.
    - **User stories**: Short "As a ... I want ... so that ..." bullets.
    - **Acceptance criteria**: One **EARS-form** sentence per criterion, numbered `AC-1`, `AC-2`, …
      (When/While/If/Where … the system shall …). Flag vague verbs, multi-`shall` sentences, or
      unclear subjects as **AMBIGUOUS** and rewrite before approval.
    - **Open questions**: Unknowns and decisions needed from humans.
3. **Present to User** for approval before moving to `/plan`.

## Done when

- Every criterion is one EARS sentence with a stable `AC-n` ID; none are AMBIGUOUS.
- Non-goals prevent scope creep.
- The `AC-n` list is the contract later checked by the `validate-implementation` skill.
