---
name: tdd
description: Use when implementing behavior with tests, fixing bugs with regression coverage, or building risky changes one vertical slice at a time. Enforces a red-green-refactor loop before production edits whenever a practical test seam exists.
capability: "Test-driven development loop for behavior changes"
side_effect_level: local_write
approval_required: false
requires_tools: "Project test runner and edit access to tests/source files"
output_schema: "Plan of slices, red/green/refactor evidence, and final test commands"
risk_class: medium
---

# TDD

## Purpose

Build or fix behavior through short feedback loops: write a failing test, make it pass with the smallest production change, then refactor with tests still green.

Use this to keep agent changes grounded in executable evidence instead of broad speculative edits.

## When to Use

- Adding behavior where a unit, integration, CLI, or snapshot test can observe the outcome.
- Fixing a bug that should never regress.
- Refactoring behavior behind an existing public seam.
- Any change where the user asks for TDD, red/green/refactor, or tests first.

Do **not** force TDD when the work is purely documentation, mechanical formatting, generated asset sync, or when the repo has no practical test seam. In those cases, state the limitation and choose the closest verification.

## Loop

1. **Choose one vertical slice.** Name the externally visible behavior and the smallest seam that can verify it.
2. **Red:** add or update one focused test that fails for the right reason. Run the narrowest test command and capture the failure.
3. **Green:** make the smallest production change needed to pass that test. Avoid unrelated cleanup.
4. **Refactor:** improve naming, boundaries, or duplication only while tests stay green.
5. **Widen:** repeat for the next slice, then run the relevant broader suite.

## Test Quality Bar

Prefer tests that:

- Assert behavior at a stable public interface rather than implementation details.
- Would fail on the original bug or missing feature.
- Use small fixtures and deterministic data.
- Cover one reason to fail per test.
- Name the scenario in domain language.

Avoid tests that:

- Only assert mocks were called when visible behavior can be checked.
- Freeze incidental formatting or timestamps without a product reason.
- Require network, secrets, production services, or broad sleeps.
- Reproduce the implementation line-for-line.

## Agent-Safe Patterns

- Read existing nearby tests before inventing test infrastructure.
- Prefer the repo's documented test command over ad hoc runners.
- Keep each red/green step small enough to explain in the final response.
- If a failing test exposes a pre-existing unrelated issue, narrow the command or document the blocker before changing scope.

## Final Response Evidence

Report:

- The behavior slices implemented.
- The narrow red/green commands, including the initial failing test when available.
- The broader verification command.
- Any test seam that could not be created and why.
