---
name: verification-before-completion
description: Use before claiming work is complete, fixed, passing, ready to commit, or ready for PR. Apply to ensure fresh command output supports every success claim and to report warnings or failures honestly.
capability: "Completion verification evidence workflow"
side_effect_level: read_only
approval_required: false
requires_tools: "Project test/build/lint commands, git status, git diff"
output_schema: "Verification summary listing each claim, exact command, result, and any limitations"
risk_class: low
---

# Verification before completion

## Purpose

Make evidence-backed completion claims. Do not say work is done, fixed, clean, or passing until the
relevant checks have run in the current context and their output supports that statement.

Confidence, previous runs, agent reports, and partial checks do not support broad success claims.

## Use with

- [`validate-implementation`](../validate-implementation/SKILL.md) when acceptance criteria must be
  marked Verified/Failed/Unknown (spec satisfaction), not merely “looks done.”
- [`commit-and-push`](../commit-and-push/SKILL.md) when preparing an actual commit/push workflow.
- Repo-specific quality gates in [`task-env-package-tools`](../task-env-package-tools/SKILL.md).

## Gate

Before saying work is done, fixed, clean, passing, ready, or complete:

1. **Name the claim.** Example: tests pass, bug fixed, assets synced, branch ready.
2. **Choose the proof.** Pick the command or inspection that would falsify that claim.
3. **Run it after the final edit.** If the full command is impossible, explain the limitation.
4. **Read the output.** Check exit code, warnings, skipped tests, and actual scope.
5. **Report only supported claims.** Use pass, warning, or fail with the exact command.

## Claim-to-proof map

| Claim | Required proof | Not enough |
| --- | --- | --- |
| Tests pass | Relevant test command exits 0 with no unexpected failures | Previous run or narrow subset for a broad claim |
| Build succeeds | Build command exits 0 | Lint passing or plausible logs |
| Lint/typecheck clean | Lint/typecheck command exits 0 or warnings are explained | Formatting only |
| Bug fixed | Original reproduction or regression test now passes | Code changed and looks plausible |
| Regression test works | Red-green evidence: fails without fix, passes with fix | Test only passed after implementation |
| Requirements met | Acceptance criteria checked with evidence — prefer `validate-implementation` | Tests pass but requirements were not reread |
| Generated assets in sync | Sync/check command exits 0 and diff is reviewed | Manual copy or assumed sync |
| Ready to commit | `git status --short` and `git diff --check` reviewed | Memory of earlier status |

## Agent reports

Treat another agent's success report as a lead, not proof. Inspect the diff and run the relevant
checks locally. If independent verification is impossible, mark it as a warning.

## Warning language

Use a warning, not a pass, when verification is incomplete for an external reason such as missing
services, unavailable credentials, network limits, or intentionally skipped slow suites. Include the
concrete limitation and what was verified instead.

## Red flags

- “Should,” “probably,” “seems,” “looks good,” “done,” or “ready” before proof.
- Output is from before final edits.
- A narrow check is being used for a broad claim.
- Skipped warnings or unavailable services are not disclosed.

## Output

```markdown
## Verification
- ✅ `command` — what it proved
- ⚠️ `command` — limitation and partial evidence
- ❌ `command` — failure and next action
```
