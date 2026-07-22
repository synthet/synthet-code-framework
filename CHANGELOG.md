# Changelog — synthet-code-framework

All notable changes to this framework are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] — 2026-07-21

### Added

- Compiled skill harnesses (`scripts/harness.py`) for procedural workflows: `release-bump`,
  `commit-and-push`, `eval`, `lint-format-security`, `task-env-package-tools`,
  `search-tool-selection`, `validate-implementation`, and `verification-before-completion`.
- Spec-kit quality gates and a spec-driven task gate in the agent workflow.
- Bootstrap stack boilerplate generator (`--dry-run` / combinatorial coverage retained).
- Skill authoring guidance plus disciplined development skills (TDD, systematic debugging).
- Codex project infrastructure (`.codex/` agents/config) alongside Claude/Cursor mirrors.
- Agent memory metadata, static agent eval fixtures, and an agent export policy validator.
- MCP config examples/validation and starter GitHub workflows seeded by bootstrap.
- Provider-oriented backlog structure and docs; generated agent-assets inventory.

### Changed

- Consolidated duplicate skills and clarified skill conflict resolution / authoring guidance.
- Hardened default Claude permissions and GitHub Actions pin/dependency hygiene.
- Strengthened assistant-tree sync drift detection (directory drift, stale generated files).

### Fixed

- Dropped accidental plop contamination from bootstrap tests.
- Removed conflicting skill-authoring duplicate; normalized inventory drift diagnostics.
- Narrowed subagent eval forbidden-export check; avoided secret-like MCP test fixtures.

### Security

- Reject likely secrets in export validation; tighten secret placeholder allowances.
- Harden bootstrap source enumeration against unintended path inclusion.

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
