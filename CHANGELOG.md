# Changelog — synthet-code-framework

All notable changes to this framework are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-07-04

### Added

- GitHub Actions CI (`.github/workflows/ci.yml`): assistant-tree drift check, OKF docs lint,
  agent frontmatter contract, committed-secrets scan, script compilation, and tests.
- Stdlib CI validators: `scripts/ci/check_agent_frontmatter.py` and `scripts/ci/check_secrets.py`.
- `validate-implementation` skill: per-acceptance-criterion Verified/Failed/Unknown verdicts with
  evidence, separate from merge readiness.
- `release-bump` skill: semver bump rubric with Keep-a-Changelog promotion.
- `commit-and-push` skill: stage, commit, and push workflow with git safety rules (pairs with release-bump).
- Combinatorial bootstrap tests (`tests/test_bootstrap.py`) covering every supported stack.
- `--dry-run` flag for `bootstrap.py`; seeded projects now receive a fresh `CHANGELOG.md`.
- `env.example` documenting the env-var contract pattern.
- `.agent/SKILL_INVENTORY.md` with the frontmatter invariants contract.
- RCA / Failure Log section in `AGENTS.md`; SDD phase-gate map in `docs/ai-workflow/README.md`.
- `requirements-dev.txt` (PyYAML, pytest).
- Thirteen flat CLI tooling skills under `.claude/skills/` with shared references, `search-tool-selection`
  router, `scripts/validate_cli_skills.py`, and optional fff MCP templates in `.mcp.json` /
  `.cursor/mcp.example.json`.
- `install-tiers.md` and `agent-environment.md` references: tiered install order (Tier 0 → Block A →
  Block B → deferred), operator scopes, and Cursor PATH/restart contract for agent shells.
- `VERSION` file at repo root for framework semver tracking.

### Changed

- `/spec` now requires EARS-form acceptance criteria with stable `AC-n` IDs.
- `/pr-ready` (command, workflow, and `pr-ready-hygiene` agent) is an explicit definition-of-done
  gate, referencing `validate-implementation` for spec satisfaction.
- Subagent-review command headings normalized to the `# /<name>` convention.
- `cli-tools-overview` and `install-checklist` skills link install tiers and agent-environment
  references; `validate_cli_skills.py` enforces all six shared reference files.
