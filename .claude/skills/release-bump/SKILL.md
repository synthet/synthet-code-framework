---
name: release-bump
description: Use when cutting a release, bumping project version, promoting the changelog Unreleased section, tagging release prep, or applying a semver rubric. Includes verification steps before committing release changes.
capability: "release-bump agent asset workflow"
side_effect_level: local_write
approval_required: false
requires_tools: "python .claude/skills/release-bump/scripts/harness.py; git log; project verify commands"
output_schema: "Harness JSON/summary with current/proposed version, Unreleased bullets, verify commands"
risk_class: medium
---

# Release bump (compiled harness)

Thin bootloader. Deterministic work lives in the harness; you only decide the semver level.

## Invoke

```bash
# Inspect current version + Unreleased bullets (no writes)
python .claude/skills/release-bump/scripts/harness.py --json

# After choosing major|minor|patch, apply VERSION + CHANGELOG
python .claude/skills/release-bump/scripts/harness.py --level minor --apply --json
```

## LLM judgment slots

1. **Choose bump level** from `git log <last-tag>..HEAD` and harness `unreleased_bullets`:
   - **major** — breaking API/config/schema/CLI change
   - **minor** — backward-compatible capability
   - **patch** — bugfix, docs, internal refactor

   No tag yet? Use the last release commit as the base:
   `git log -1 --format=%h --grep='^chore(release)'`.
2. **Reconcile the changelog first.** Compare the user-facing commits since the base with
   `unreleased_bullets` and add any missing entries before `--apply`, which promotes only what is
   already under Unreleased.
3. State the level and 1–2 justifying changes, then pass `--level`.

## After apply

The harness writes only the first version source it finds (`VERSION`, else the root
`pyproject.toml`, else `package.json`), never nested packages. Run
`git show --stat <previous release commit>` and bump the same version strings it touched
(sub-package `pyproject.toml`, `__version__`, `package.json`, both root entries in
`package-lock.json`). Verify with `git grep -n '"<old version>"\|= "<old version>"'`, which should
leave only third-party matches. Why: otherwise sub-packages ship with the old version.

## Human authority

Do **not** commit, tag, or push unless the user explicitly asks. Suggest
`chore(release): vX.Y.Z` and an annotated tag only after the applicable
verify commands and the workspace `AGENTS.md` checks both pass.

## Verify

Run every command listed in harness `verify_commands` (or the self-verify set in `README.md`)
before any release commit.

A listed command is not applicable, and is not a release failure, when its script
is not in the workspace, or when it is `python -m pytest tests -q` and the workspace
has no `tests/` directory. Record that command as not applicable.

Then run the test and typecheck commands documented in the workspace `AGENTS.md`.
Skip install, start, and full end-to-end app drives unless the user asks for them.
Suggest the release commit only after those project checks pass.
