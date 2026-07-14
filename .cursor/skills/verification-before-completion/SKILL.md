---
name: verification-before-completion
description: Use before claiming work is complete, fixed, passing, ready to commit, or ready for PR. Apply to ensure fresh command output supports every success claim and to report warnings or failures honestly.
capability: "completion verification evidence workflow"
side_effect_level: read_only
approval_required: false
requires_tools: "Project test/build/lint commands, git status, git diff."
output_schema: "Verification summary listing each claim, exact command, result, and any limitations."
risk_class: low
---

# Verification before completion

## Purpose

Make evidence-backed completion claims. Do not say work is done, fixed, clean, or passing until the relevant checks have run in the current context and their output supports that statement.

## Gate

Before any completion claim:

1. **Identify the claim.** Examples: tests pass, lint is clean, bug is fixed, generated mirrors are in sync, branch is ready.
2. **Choose the proof.** Select the exact command or inspection that would falsify the claim.
3. **Run it fresh.** Use the full relevant command, not a stale or partial result, unless explicitly documenting a limitation.
4. **Read the output.** Check exit code, failures, warnings, skipped tests, and whether the command covered the intended scope.
5. **State only what evidence supports.** Report pass, fail, or warning with the exact command.

## Common Claims and Proof

| Claim | Required proof |
| --- | --- |
| Tests pass | Relevant test command exits 0 with no unexpected failures |
| Build succeeds | Build command exits 0 |
| Lint/typecheck clean | Lint/typecheck command exits 0 or documented warnings are understood |
| Bug fixed | Original reproduction or regression test now passes |
| Generated assets in sync | Sync/check command exits 0 and `git diff` shows intended generated changes |
| Ready to commit | `git status --short` and `git diff --check` reviewed |

## Warning Language

Use a warning, not a pass, when verification is incomplete for an external reason such as missing services, unavailable credentials, network limits, or intentionally skipped slow suites. Include the concrete limitation and what was verified instead.

## Verification Summary Template

```markdown
## Verification
- ✅ `command` — what it proved
- ⚠️ `command` — limitation and partial evidence
- ❌ `command` — failure and next action
```

## Stop Signals

- You are about to write “should,” “probably,” “looks good,” or “done” without a fresh check.
- You are relying on a previous run from before the final edits.
- You are trusting another agent’s success report without inspecting output or diff.
- You ran a narrow check but are making a broad claim.
