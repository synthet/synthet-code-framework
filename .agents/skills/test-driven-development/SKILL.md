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

## Purpose

Use tests to define expected behavior before changing production code. A passing test that never failed does not prove the behavior is covered.

## Red-Green-Refactor

1. **RED — write one failing test.** Name the behavior clearly, exercise real code, and keep the assertion focused.
2. **Verify RED.** Run the smallest relevant test command. Confirm it fails for the expected reason, not because of typos, setup errors, or missing imports.
3. **GREEN — write minimal production code.** Implement only enough behavior to pass the failing test. Do not add unrequested options, broad abstractions, or cleanup.
4. **Verify GREEN.** Re-run the targeted test. If it fails, fix production code rather than weakening the test.
5. **REFACTOR — improve structure while staying green.** Remove duplication or clarify names only after the behavior passes.
6. **Broaden verification.** Run the surrounding package/module tests or the documented fast suite before committing.

## Test Quality Rules

- Test behavior and public contracts, not private implementation details.
- Prefer real collaborators; mock only when the boundary is slow, nondeterministic, external, or impossible to instantiate.
- Keep one behavior per test. If the test name needs “and,” split it.
- Cover edge cases and errors that define the contract.
- For bug fixes, the regression test must fail before the fix and pass after it.

## If Production Code Already Exists

If exploratory code was written first, treat it as a spike: either discard it or avoid copying it while writing the test. Then implement fresh from the red test. If discarding would be risky or expensive, tell the user and convert the existing behavior into tests before changing it further.

## TDD Log Template

```markdown
## TDD Log
- RED test file:
- RED command and failure:
- GREEN change:
- GREEN command and pass:
- Refactor notes:
- Broader verification:
```

## Verification Checklist

- [ ] New behavior has a focused test.
- [ ] The test failed for the intended reason before implementation.
- [ ] Production code is the minimal change needed to pass.
- [ ] Targeted and relevant broader tests pass.
- [ ] No test was weakened to fit the implementation.
