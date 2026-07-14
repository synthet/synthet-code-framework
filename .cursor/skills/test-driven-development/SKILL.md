---
name: test-driven-development
description: Use when implementing a feature, bug fix, refactor, or behavior change that can be tested. Apply before production code changes to enforce red-green-refactor, prove tests fail for the intended reason, and keep implementation minimal.
capability: "test-driven development red green refactor workflow"
side_effect_level: local_write
approval_required: false
requires_tools: "Project test runner and editor; use repo-specific test commands when documented."
output_schema: "TDD log with failing test evidence, minimal implementation, passing verification, and refactor notes."
risk_class: medium
---

# Test-driven development

## Iron rule

No production behavior change without a failing test first. A test that never failed does not prove coverage.

## Use with

- [`systematic-debugging`](../systematic-debugging/SKILL.md) when a bug's root cause is not yet known.
- [`verification-before-completion`](../verification-before-completion/SKILL.md) before claiming the implementation is complete.

## Workflow

### 1. RED — write one failing test

- Name the behavior clearly.
- Exercise public contracts and real code where practical.
- Assert one behavior; split tests that need “and.”
- For bug fixes, reproduce the reported symptom.

Run the smallest relevant command and confirm the failure is for the intended reason, not typos, imports, fixtures, or setup. If the test passes immediately, rewrite it.

### 2. GREEN — implement the minimum

- Write only enough production code to pass the RED test.
- Do not add unrequested options, abstractions, cleanup, or “while here” changes.
- If the test is hard to write, treat that as design feedback and improve the seam/interface.

Re-run the targeted test. If the expectation still matches the requirement, fix production code rather than weakening the test.

### 3. REFACTOR — improve while green

- Remove duplication, clarify names, or extract helpers only after GREEN.
- Do not add behavior during refactor.
- Re-run targeted tests after each meaningful refactor, then run relevant neighboring tests.

## Existing production code

If code was written first, treat it as a spike: set it aside, write the failing test, then implement from the test. If strict TDD is no longer possible, document the exception explicitly.

## Test quality rules

- Test behavior, not private implementation details.
- Prefer real collaborators; mock only slow, nondeterministic, external, or impractical boundaries.
- Avoid tests that only prove mocks were called.
- Cover edge cases and errors that define the contract.
- Regression tests must fail without the fix and pass with it.

## Red flags

- Code before test.
- Test added after implementation.
- Test passes immediately.
- “Manual testing is enough.”
- “Too simple to test.”
- “This is different because…”

## Output

```markdown
## TDD Log
- RED test:
- RED command and failure:
- GREEN change:
- GREEN command and pass:
- Refactor notes:
- Broader verification:
```
