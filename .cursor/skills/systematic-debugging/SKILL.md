---
name: systematic-debugging
description: Use when encountering a bug, failing test, build failure, unexpected behavior, flaky behavior, regression, performance anomaly, or integration issue. Apply before proposing fixes so the agent finds root cause, compares working patterns, tests one hypothesis at a time, and avoids guess-and-check patches.
capability: "systematic debugging root cause workflow"
side_effect_level: read_only
approval_required: false
requires_tools: "git, project test/build commands, rg; optional logs or diagnostics appropriate to the stack."
output_schema: "Root-cause report with evidence, hypothesis, minimal fix plan, and verification commands."
risk_class: low
---

# Systematic debugging

## Purpose

Find and fix root causes instead of treating symptoms. Do not write a fix until the failure is reproduced or bounded, evidence identifies the failing layer, and a single testable hypothesis exists.

## Workflow

1. **Read the failure completely.** Capture exact command, exit code, stack trace, file paths, line numbers, warnings, and environment notes.
2. **Reproduce or bound it.** Re-run the smallest relevant command. If it is flaky, gather frequency, inputs, timing, and logs before changing code.
3. **Check recent changes.** Inspect `git diff`, touched files, dependencies, config, generated files, and environment differences.
4. **Trace the data path.** For multi-component flows, inspect each boundary: input, output, config/env propagation, state transitions, and side effects.
5. **Find a working pattern.** Locate similar passing code or tests in the repo and compare the broken path line-by-line.
6. **State one hypothesis.** Write: “I think the root cause is X because evidence Y.” Test the smallest possible change or diagnostic.
7. **Create or identify a regression test.** Prefer an automated failing test. If no harness exists, create a focused script or documented reproduction.
8. **Fix only the root cause.** Avoid bundled refactors or opportunistic cleanup until the regression is green.
9. **Verify the symptom and surrounding suite.** Run the targeted reproduction, then the appropriate broader checks.

## Stop Signals

- You are about to “just try” a fix without evidence.
- You have multiple simultaneous hypotheses.
- A test was edited to match the implementation rather than the requirement.
- Two fix attempts failed; before a third, re-open the root-cause analysis.
- Three fix attempts failed; pause and question the architecture or assumptions with the user.

## Evidence Template

```markdown
## Root Cause
- Symptom:
- Reproduction command:
- Evidence gathered:
- Working comparison:
- Hypothesis tested:
- Root cause:
- Fix plan:
- Verification:
```

## Verification Checklist

- [ ] Failure output read fully and cited in notes.
- [ ] Reproduction or bounded flaky behavior documented.
- [ ] Working examples or references compared where available.
- [ ] One hypothesis tested at a time.
- [ ] Regression test or equivalent reproduction verifies the fix.
