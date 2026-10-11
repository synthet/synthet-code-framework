# Changelog — synthet-code-framework

All notable changes to this framework are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] — 2026-10-11

### Added

- Explicit multi-harness inventory, reviewed plan, apply, receipt verification and rollback
  for user/global and project agent setups, with ownership tracking and per-file backups.
- A portable library of 55 core and specialist skills, including `resume-task`, transcript
  archiving, native setup, database/container workflows and evaluation panels.
- Generated Antigravity rules and subagents alongside the existing Claude, Cursor and Codex
  assets; preserve each adopted project's canonical source and native sync conversions.
- `/mine`, `/compile-skill`, `/audit-instructions` and expanded decomposition workflows,
  plus `lesson-to-skill` and `autonomous-run-contract` skills.
- Restored the `rust` bootstrap stack (`cargo build` / `cargo test` / `cargo fmt` + clippy),
  including command detection, starter boilerplate, and a lint-router stack.
- Generic `rust-testing` skill for cargo/nextest unit tests beside modules.
- `bootstrap.py --adopt` merges the scaffold into an existing repo without overwriting product
  files; imports project skills from a `.claude/skills` symlink; defaults to `--no-include-ci`.
- Rust command detection uses `./script/clippy` when `script/clippy` or `script/clippy.ps1` exists.

### Fixed

- Portable helpers resolve bundled runtimes from their skill directory; mirror generation
  and comparison exclude Python interpreter caches without relaxing content checks.
- Preserve live harness configuration when applying reviewed additive MCP registrations;
  retain existing credentials, permissions, model settings, hooks and provider packages.
- Restore protected acceptance-verification wording in `pr-ready` and
  `validate-implementation` assets.
- `--adopt --auto-detect` only rewrites commands inside the AGENTS.md scaffold block, so an
  existing engineering guide is not rewritten (for example `cargo test --doc`).
- `--adopt` skips instruction-file pointers (`AGENTS.md` / `CLAUDE.md` / `GEMINI.md` whose
  entire contents are a sibling path such as `.rules`), so Zed-style shared `.rules` files
  are not rewritten.

### Security

- Resume recovery uses explicit profile scope, redacts serialized report fields and rejects
  output inside harness stores or on input transcripts.
- Agent frontmatter validation requires supported model aliases; evaluation panels require
  explicit export authorization, and MCP adapters exclude unsupported literal credentials.

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
