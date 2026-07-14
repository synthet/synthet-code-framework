---
name: tdd
description: Use when the target behavior is known and a practical test seam exists: new features, root-caused bug fixes, or risky refactors that should proceed through red-green-refactor slices.
capability: "Test-driven development loop for known behavior changes"
side_effect_level: local_write
approval_required: false
requires_tools: "Project test runner and edit access to tests/source files"
output_schema: "TDD slice plan with red, green, refactor, and verification evidence"
risk_class: medium
---

# TDD

## Purpose

Turn a known behavior change into small, evidenced red-green-refactor slices. This skill starts **after** the intended behavior is clear; if the failure is still unclear, use `diagnosing-bugs` first.

## Boundary

Use this skill for:

- New behavior with an observable unit, integration, CLI, or snapshot seam.
- A bug fix after the root cause or failing scenario is understood.
- A refactor where existing behavior must stay stable.
- Any request for TDD, tests-first, or red-green-refactor.

Do not force this skill for docs-only edits, generated mirror sync, mechanical formatting, or changes with no practical test seam. State the limitation and choose the closest verification instead.

## First Minute

Before production edits, identify four items:

| Item | Question |
|------|----------|
| Behavior | What user-visible outcome should change or remain stable? |
| Seam | Which existing test surface can observe it? |
| Slice | What is the smallest end-to-end increment worth making? |
| Command | Which narrow command should fail first? |

If the seam is unknown, inspect nearby tests before creating new test infrastructure.

## Loop

1. **Red:** write one focused test for the slice and run the narrow command. Confirm it fails for the intended reason.
2. **Green:** make the smallest production change that passes the focused test. Avoid unrelated cleanup.
3. **Refactor:** improve naming, duplication, or local boundaries only while the focused test stays green.
4. **Widen:** repeat for the next slice, then run the relevant broader suite.

Avoid batching multiple red tests unless one small implementation step should make them pass together.

## Test Quality Bar

Prefer tests that assert stable behavior, use deterministic fixtures, and would fail on the original bug or missing feature. Avoid tests that only assert mock calls, freeze incidental formatting, depend on network/secrets/sleeps, or restate the implementation.

## Refactor Gate

A refactor is in scope only when it keeps public behavior unchanged, stays near the touched slice, and is covered by the same focused test plus related existing tests. Stop and report if cleanup crosses package boundaries or changes public contracts.

## Output Evidence

Report the behavior slices, red failure evidence when practical, green/refactor commands, broader verification, and any missing test seam with the reason.
