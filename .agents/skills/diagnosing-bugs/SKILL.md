---
name: diagnosing-bugs
description: Use for hard bugs, flaky tests, confusing failures, regressions, or performance issues where the cause is not obvious. Applies a disciplined reproduce, minimise, hypothesise, instrument, fix, and regression-test loop.
capability: "Structured debugging and regression prevention"
side_effect_level: local_write
approval_required: false
requires_tools: "Repo test runner, logs, debugger or instrumentation as appropriate"
output_schema: "Bug diagnosis with reproduction, root cause, fix, and regression evidence"
risk_class: medium
---

# Diagnosing bugs

## Purpose

Debug by evidence. First make the bug observable and small, then form hypotheses, instrument only what distinguishes them, fix the root cause, and lock it with a regression test.

## When to Use

- A test, build, CLI, UI flow, or production-like workflow fails and the cause is unclear.
- A bug report is vague, intermittent, or seems inconsistent with the code.
- A performance regression needs measurement before optimization.
- The user asks to diagnose, investigate, root-cause, or fix a flaky failure.

For straightforward compile errors with an obvious one-line fix, use normal edit/test flow instead.

## Loop

1. **Reproduce:** capture the exact command, input, environment, observed output, and expected output.
2. **Minimise:** reduce to the smallest command, fixture, route, or test that still fails.
3. **Hypothesise:** list 1-3 plausible causes and what evidence would distinguish them.
4. **Instrument:** add temporary logs, assertions, breakpoints, or focused probes. Keep probes narrow and remove them unless they become useful permanent diagnostics.
5. **Fix root cause:** patch the smallest responsible boundary, not just the symptom.
6. **Regression-test:** add or update a test that fails before the fix and passes after it.
7. **Broaden:** run the relevant wider suite and document any unrelated remaining failures.

## Guardrails

- Do not rewrite large areas before proving the cause.
- Do not weaken assertions or delete tests just to go green.
- Do not hide errors with broad catch-all handling unless the product behavior requires it.
- Do not leave noisy debug output in production paths.
- If the bug touches data loss, auth, secrets, payments, or destructive actions, run a security review before finalizing.

## Root Cause Note

When the failure was non-obvious, add a short RCA entry to the project’s documented failure log if the repo has one. Include date, symptom, root cause, and the guard that prevents re-debugging.

## Final Response Evidence

Report:

- Reproduction command or scenario.
- Root cause in one paragraph.
- Files changed for the fix and regression test.
- Verification commands and whether any failures remain.
