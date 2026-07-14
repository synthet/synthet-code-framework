---
name: systematic-debugging
description: Use when encountering a bug, failing test, build failure, unexpected behavior, flaky behavior, regression, performance anomaly, or integration issue. Apply before proposing fixes so the agent performs root-cause investigation, compares working patterns, tests one hypothesis at a time, and avoids guess-and-check patches.
capability: "systematic debugging root cause workflow"
side_effect_level: read_only
approval_required: false
requires_tools: "git, project test/build commands, rg; optional logs or diagnostics appropriate to the stack."
output_schema: "Root-cause report with evidence, hypothesis, minimal fix plan, and verification commands."
risk_class: low
---

# Systematic debugging

## Iron rule

No fixes before root-cause evidence. If the investigation is incomplete, gather evidence instead of patching.

## Use with

- [`test-driven-development`](../test-driven-development/SKILL.md) when the bug can be captured by a regression test.
- [`verification-before-completion`](../verification-before-completion/SKILL.md) before claiming the bug is fixed.

## Workflow

1. **Read the whole failure.** Capture command, exit code, stack trace, warnings, paths, line numbers, inputs, and environment notes.
2. **Reproduce or bound it.** Run the smallest relevant command. For flaky failures, record frequency, timing, inputs, and logs.
3. **Inspect recent change.** Review `git diff`, recent commits, dependency/config/generated-file changes, and environment differences.
4. **Trace backward from the symptom.** For bad values or state, follow the call/data path to the first wrong source. For multi-component flows, inspect each boundary: input, output, env/config propagation, state transition, and side effect.
5. **Compare with working patterns.** Find similar passing code, tests, configs, or docs in this repo. List meaningful differences before selecting one.
6. **Test one hypothesis.** State “I think root cause is X because Y.” Change or instrument one variable at a time to confirm or falsify it.
7. **Fix the root cause only.** Prefer a failing regression test or minimal reproduction before the fix. Avoid unrelated refactors.
8. **Verify with the original reproduction.** Then run the relevant neighboring tests/checks.

## Escalation

After two failed fix attempts, stop and re-open the root-cause analysis. After three, pause and question the architecture, assumptions, or selected working pattern with the user.

## Red flags

- “Just try this.”
- “Probably obvious.”
- “Skip reproduction.”
- “Test after the fix.”
- Multiple simultaneous changes.
- Another fix attempt after repeated failures.
- A human asks: “Is that actually happening?”, “Will that show us?”, or “Are we stuck?”

## Output

```markdown
## Root Cause
- Symptom:
- Reproduction:
- Evidence:
- Working comparison:
- Hypothesis tested:
- Root cause:
- Fix:
- Verification:
```
