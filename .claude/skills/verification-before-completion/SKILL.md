---
name: verification-before-completion
description: Use before claiming work is complete, fixed, passing, ready to commit, or ready for PR. Apply to ensure fresh command output supports every success claim and to report warnings or failures honestly.
capability: "Completion verification evidence workflow"
side_effect_level: read_only
approval_required: false
requires_tools: "python .claude/skills/verification-before-completion/scripts/harness.py; project test/build/lint; git status"
output_schema: "Verification summary listing each claim, exact command, result, and any limitations"
risk_class: low
---

# Verification before completion (compiled harness)

Do not claim done/fixed/passing/ready until fresh command output supports the claim.

## Invoke

```bash
# List catalog
python .claude/skills/verification-before-completion/scripts/harness.py --json

# Run selected proofs
python .claude/skills/verification-before-completion/scripts/harness.py \
  --claim tests_pass --claim assets_synced --run --json

# Framework self-verify suite
python .claude/skills/verification-before-completion/scripts/harness.py --framework --run
```

## LLM judgment slots

1. **Name the claim** and pick the falsifying proof (catalog ids or custom command).
2. **Interpret output** after the final edit — exit code, warnings, skipped tests, scope.
3. Report ✅ / ⚠️ / ❌ with the exact command; never upgrade incomplete verification to pass.
4. **Prove the real path, not a proxy.** A native addon can import fine and still fail on first use (bindings load lazily): check it with a real call, run by the same interpreter the launcher uses, e.g. `node -e "new (require('better-sqlite3'))(':memory:')"` with the `node` an MCP config starts. An import or `--version` alone does not prove it works.
5. **Tie CI to the exact commit.** A CI result only proves the commit it ran on, and `gh pr checks --watch` can show an earlier run right after a push. Run `gh run list --commit <sha> --json headSha,status,conclusion` for the commit you're claiming. No run yet means not passed. Before pushing to a PR, check `gh pr view <n> --json state`, because commits pushed after a merge never reach the base branch.

## Use with

- `validate-implementation` when an AC matrix is required
- `commit-and-push` before an actual commit
