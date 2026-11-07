# Changelog — synthet-code-framework

All notable changes to this framework are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `/ship-pr` skill: takes one PR from open to merged. It fixes CI failures at the root cause, runs the
  steps CI skipped after a failure, waits for green on the exact head commit, then merges and
  verifies. It runs only when the user types it, and it never weakens a check to pass it.
- `agent_setup.py plan --overlay <manifest>`: installs extra user-level skills from a local manifest,
  with the same ledger, receipts and rollback. The manifest and its skills stay outside this library.

- `/constitution` command and spec-layer vocabulary, folded in from agent-sdlc.
- `synthet-repos` skill: maps a task to the public repository that owns it.

### Changed

- `bg-status` finds repositories from `PROJECTS_ROOT` or the current repository, not a fixed path.
- Shorter descriptions for the five longest skills, which reduces listing cost in every harness.

### Fixed

- Credential checks no longer match hyphenated words that contain `sk-`, which blocked planning.
- `framework-*` aliases point at installed skills instead of keeping a command's relative paths.
- Installed skills no longer nest copies of sibling `SKILL.md` files under `references/shared/`.
- Links that resolve to nothing once installed keep only their label.

## [0.5.0] — 2026-11-04

### Added

- `/go` skill: takes the recommended options, settles the rest with Jev, works through open items in
  order and reports once. It runs only when the user types it, and it keeps a fixed list of actions
  it never approves. It can merge a PR it opened only when CI is green on that exact commit,
  and a PR already shown to the user in a private repository with no CI after a local check passes.
- `use-jev` skill: hands open decisions and blocked steps to Jev in one batched call, then acts only
  on what Jev clears.
- `app-icons` skill: designs Synth-family icons and favicons, renders every size from vector masters
  and wires web, Gradio, FastAPI, Electron and Expo surfaces.
- `bg-status` skill: a read-only snapshot of background tasks, workers, peer sessions and machine
  resources.

### Changed

- Skill tiers: shared skills install at user level, and repositories keep only their own skills and
  opted-in stack packs. `agent_setup.py plan` retires unmodified, unreferenced repository copies and
  reports collisions with global names. See `docs/skill-tiers.md`.
- `use-jev` is now in the library manifest, so it installs for every harness.
- `release-bump` covers repositories with no tag, changelog reconciliation and sub-package versions.
- `commit-and-push` no longer writes branch-tracking entries: its harness pushes without `-u`, and
  the skill says to use `--no-track`. It also checks repository visibility before a push and
  regenerates generated files in a clean worktree.
- `verification-before-completion` ties CI evidence to the exact commit and checks that a PR is still
  open before pushing to it.
- `windows-agent-tooling` covers `git show <ref>:<path>` in Git Bash, and `agent-setup` explains why
  raw hashes and empty plans don't prove installed copies match.
- Skills gained guidance on shared checkouts, read-only WAL access, Git Bash, native addons, harness
  hooks and adopting a foreign skill tree.

### Fixed

- NTFS junctions are treated as links on Python 3.11, so a junction is no longer a second project.
- `agent_setup.py rollback` restores the ownership ledger along with the files.
- The Jev hook returns a valid `ask` to Cursor. Cursor rejected the empty response and blocked the
  tool.
- `okf_lint.py` skips git-ignored `_local/` notes by default, so local runs match CI.
- The frontmatter check skips contract checks for generated command and rule aliases, which failed
  in every adopting project.

## [0.4.0] — 2026-10-25

### Added

- Centralized AI agent permission governance control plane with Git-backed hosting in
  `infra/jev/` (46 tracked files), managed via `scripts/manage_permissions.py` (`bootstrap`,
  `sync-infra`, `plan`, `apply`, `rollback`, `audit`, `verify`).
- Cross-harness permission inventory, live telemetry audit, and October 2026 lightweight model
  matrix in `docs/permissions-full-inventory.md` and `docs/centralized-permissions.md`.
- Two-stage T3 auto-permission gate with calibrated per-question Noul thresholds
  (`in_scope >= 0.88`, `local_effects >= 0.80`, `recoverable >= 0.75`) and Tier-2 Coin-Flip
  Adjudication (`0.45 <= min(scores) < threshold`) calling `synthet-agent-swarm decide`.
- Enriched `subagent-review` skill with `swarm_decide` structured decision support and
  synchronous `PATHEXT` discovery (~34ms startup).
- Enforced explicit `--harness` selection across all 5 harnesses in `export-chat` and enriched
  transcript format parsing in `resume-task`.
- Claude Code and Cursor marketplaces for the `agent-workflow` plugin. Manifests point at
  the existing `.claude` and `.cursor` trees and are refreshed by
  `scripts/build_plugin_manifests.py`.

### Fixed

- Antigravity Windows terminal sandbox compatibility: expanded tilde paths in `deny_read`
  rules to absolute Windows paths (`C:\Users\dmnsy\.ssh`) and enforced
  `allowNonWorkspaceAccess: true` on Windows to eliminate `readonly /: non-absolute file path`.
- Claude Code `PermissionRequest` hook ordering: placed the Jev gate hook (`timeout: 15s`)
  at index 0 ahead of notification hooks.
- Closed T4 regex classification blindspots for `git -C <repo>` and Antigravity brain scratchpad
  paths (`~/.gemini/antigravity-cli/brain/<id>/scratch/`).

### Changed

- `consume` examples use the user Downloads directory and no longer name personal
  filename patterns.

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
