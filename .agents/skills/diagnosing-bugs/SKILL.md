---
name: diagnosing-bugs
description: Use when a failure, flaky test, regression, or performance issue is not yet understood. Focuses on reproduction, minimization, hypotheses, targeted instrumentation, and root-cause evidence before handing off to a fix workflow.
capability: "Evidence-first bug diagnosis and root-cause analysis"
side_effect_level: local_write
approval_required: false
requires_tools: "Repo test runner, logs, debugger or instrumentation as appropriate"
output_schema: "Bug diagnosis with reproduction, root cause, fix handoff, and verification evidence"
risk_class: medium
---

# Diagnosing bugs

## Purpose

Reduce uncertainty before changing behavior. Make the bug observable, minimize it, distinguish plausible causes with evidence, and identify the smallest root-cause fix. Once the cause and regression seam are known, use `tdd` for the fix when practical.

## Boundary

Use this skill for:

- Confusing test, build, CLI, UI, or production-like failures.
- Vague bug reports or symptoms that do not match the code at first glance.
- Flaky tests, regressions, and performance issues that need measurement.
- Requests to diagnose, investigate, root-cause, or debug.

Do not use it as ceremony for obvious compile errors or one-line fixes; fix and verify those directly.

## First Minute

Capture the investigation frame:

| Item | Question |
|------|----------|
| Symptom | What exact output, failure text, or wrong behavior was observed? |
| Reproduction | Which command, input, route, or workflow shows it? |
| Expected | What should have happened instead? |
| Scope | Which package, platform, data shape, or environment seems affected? |

If reproduction is missing, create or request one before guessing at code changes.

## Loop

1. **Reproduce:** record the exact command, input, environment, observed output, and expected output.
2. **Minimize:** reduce to the smallest command, fixture, route, or test that still fails.
3. **Hypothesize:** list 1-3 plausible causes and the evidence that would distinguish them.
4. **Instrument:** add narrow logs, assertions, breakpoints, or probes; remove temporary noise before finalizing.
5. **Identify root cause:** name the responsible boundary and why the evidence supports it.
6. **Handoff/fix:** if a regression seam exists, switch to `tdd`; otherwise make the smallest safe fix and explain why a test was not practical.
7. **Broaden:** run the relevant wider suite and document unrelated remaining failures.

## Pattern Notes

- **Flaky tests:** check seed/order/time sensitivity, shared state, clocks, sleeps, and parallelism before changing assertions.
- **Performance bugs:** capture comparable before/after measurements with the same command.
- **Data-shape bugs:** preserve the smallest failing fixture and assert the validation or normalization boundary.
- **Integration bugs:** isolate contract, transport, serialization, auth, and environment before rewriting internals.

## Guardrails

- Do not rewrite large areas before proving the cause.
- Do not weaken assertions or delete tests just to go green.
- Do not hide errors with broad catch-all handling unless product behavior requires it.
- Do not leave temporary debug output in production paths.
- Run a security review if the bug touches data loss, auth, secrets, payments, or destructive actions.

## Root Cause Note

When the failure was non-obvious, add a short RCA entry to the repo’s documented failure log if one exists: date, symptom, root cause, and guard.

## Output Evidence

Report reproduction, minimized case, root cause, fix or TDD handoff, regression test status, verification commands, and any remaining failures.
