# Skill inventory — ${PROJECT_NAME}

**Last reviewed:** 2026-07-10. Companion to [SKILL_CHANGE_AST10_REVIEW.md](SKILL_CHANGE_AST10_REVIEW.md).
Update this file (new row or **Last reviewed** date) in the same PR as any skill change.

Risk tiers: **L1** = advisory/read-mostly (writes limited to docs/reports); **L2** = can run
commands or edit code/config as part of its procedure.

## Skills (`.claude/skills/`)

### SDLC and governance

| Skill | Purpose | Risk | Last reviewed |
|-------|---------|------|---------------|
| agent-memory | Log sessions, dream consolidation, promote memory, load context | L2 | 2026-07-01 |
| backlog-queue | GitHub Project board as canonical queue; Stage transitions | L2 | 2026-07-01 |
| commit-conventions | Conventional Commits and PR title wording | L1 | 2026-07-01 |
| commit-and-push | Stage, commit, and push with git safety rules; pairs with release-bump | L2 | 2026-07-04 |
| critical-commit-audit | Deep post-commit hunt for high-severity bugs | L2 | 2026-07-01 |
| eval | Capture task quality signals to agent memory | L2 | 2026-07-01 |
| mcp-server-design | Design MCP servers with safe transport and validation | L1 | 2026-07-01 |
| release-bump | Semver bump, changelog promotion, release commit prep | L2 | 2026-07-01 |
| security-review | Lightweight pre-merge security sanity check | L1 | 2026-07-01 |
| subagent-review | Review-only external CLI orchestration via MCP | L1 | 2026-07-01 |
| threat-modeling-agentic-tools | Threat-model MCP/tool abuse and injection | L1 | 2026-07-01 |
| validate-implementation | Per-AC Verified/Failed/Unknown verdicts with evidence | L2 | 2026-07-01 |

### CLI tooling ([cli-tools-skills-spec.md](cli-tools-skills-spec.md))

| Skill | Purpose | Risk | Last reviewed |
|-------|---------|------|---------------|
| search-tool-selection | Choose fd vs rg vs ast-grep vs fff MCP vs IDE search | L1 | 2026-07-03 |
| safe-command-patterns | Bounded output, inspect-before-edit, confirmation gates | L1 | 2026-07-03 |
| search-and-navigation | rg, fd, bat, tree, navigation | L1 | 2026-07-03 |
| git-and-diff-workflows | git, gh, bounded diffs | L1 | 2026-07-03 |
| cli-tools-overview | Router for CLI skills + shared references (install-tiers, agent-environment) | L1 | 2026-07-04 |
| task-env-package-tools | Task runners, sync/frontmatter/pytest gates | L1 | 2026-07-03 |
| structural-code-search | ast-grep, semgrep, ctags | L1 | 2026-07-03 |
| data-config-tools | jq, yq, curl, sqlite | L1 | 2026-07-03 |
| install-checklist | Human workstation provisioning (not agent-automated) | L2 | 2026-07-03 |
| lint-format-security | ruff, eslint, trivy, shellcheck | L2 | 2026-07-03 |
| mcp-code-intelligence | MCP tiers; fff, Serena, Zoekt, embeddings | L2 | 2026-07-03 |
| windows-agent-tooling | Native Windows agent workflows | L2 | 2026-07-03 |
| wsl2-agent-tooling | WSL2 build/test/MCP workflows | L2 | 2026-07-03 |

## Subagents (`.claude/agents/`)

| Agent | Purpose | Risk | Last reviewed |
|-------|---------|------|---------------|
| critical-commit-audit | High-severity post-commit bug hunt with minimal fixes | L2 | 2026-07-01 |
| external-cli-reviewer | Coordinate review-only Codex + Gemini panel | L1 | 2026-07-01 |
| external-codex-review | Codex-only external review | L1 | 2026-07-01 |
| external-gemini-review | Gemini-only external review | L1 | 2026-07-01 |
| pr-ready-hygiene | Definition-of-done checks and paste-ready PR text | L2 | 2026-07-01 |

Commands (`.claude/commands/`) and rules (`.claude/rules/`) are catalogued in
[AGENT_INFRA_INVENTORY.md](AGENT_INFRA_INVENTORY.md); they follow the same review process.

## Frontmatter invariants (CI-enforced)

`scripts/ci/check_agent_frontmatter.py` enforces these on every PR:

- **Skills:** YAML frontmatter required; `name` is the **first** key and matches the directory
  name; `description` is non-empty; skill names are unique across the tree.
- **Agents:** frontmatter required; `name` matches the file stem; `description` non-empty; names unique.
- **Rules:** frontmatter required with non-empty `description`.
- **Commands:** H1 heading of the form `# /<file-stem> …`.
- **All files:** plain scalar frontmatter keys only — no exotic YAML tags (`!!`).

Violations fail CI; fix the asset rather than the checker. If the contract itself must change,
update the checker, this file, and [SKILL_CHANGE_AST10_REVIEW.md](SKILL_CHANGE_AST10_REVIEW.md)
in the same PR.

CLI skill structure is additionally checked by `scripts/validate_cli_skills.py`.
