---
name: task-env-package-tools
description: Use for synthet-code-framework task runners, uv, Docker, sync checks, frontmatter validation, OKF lint, pytest, and project verification gates. Apply when running repo-specific tests/checks or diagnosing environment/package tooling.
capability: "task-env-package-tools agent asset workflow"
side_effect_level: local_write
approval_required: false
requires_tools: "See asset body for tool requirements."
output_schema: "Markdown report or documented command output."
risk_class: medium
---

# Task, environment, and package tools

## Purpose

Run builds/tests/lint via project conventions; manage Python/Node envs safely.

## When to Use

- Running framework or bootstrapped project checks
- Docker compose for local services
- Choosing `just`/`mise`/`npm run` over ad hoc commands

## Required Tools

Project-defined; framework defaults: `python`, `uv`, optional `docker`, `just`, `mise`, `pnpm`.

## Install

Install blocks are shared — See [install-blocks.md](../cli-tools-overview/references/install-blocks.md).

### Windows PowerShell

Use winget blocks from the reference when provisioning a new machine.

### WSL2 Ubuntu

Use apt/curl blocks from the reference; symlink `fdfind` → `fd` if needed.

### macOS

Use Homebrew blocks from the reference.


## Common Commands

Framework quality gates (this repo):

```bash
python scripts/sync_assistant_trees.py --check
python scripts/ci/check_agent_frontmatter.py
python scripts/okf_lint.py --profile project --exclude-prefix archive/ docs
python -m pytest tests -q
python scripts/validate_cli_skills.py
```

Bootstrapped projects use tokens from AGENTS.md:

```bash
${BUILD_CMD}
${TEST_CMD}
${LINT_CMD}
```

Docker (when compose file exists):

```bash
docker compose config
docker compose up -d --build
docker compose logs --tail=50 service_name
```

## Agent-Safe Patterns

- Read AGENTS.md / Makefile / package.json scripts before inventing commands.
- Docker down/prune needs confirmation. See [bounded-output-patterns.md](../cli-tools-overview/references/bounded-output-patterns.md).

## Commands Requiring Confirmation

See [commands-requiring-confirmation.md](../cli-tools-overview/references/commands-requiring-confirmation.md).; `docker system prune`, broad `pip install`, production deploy scripts.

## Troubleshooting

- Sync drift: run `python scripts/sync_assistant_trees.py` after editing `.claude/` to update Cursor and Codex mirrors.
- pytest failures: narrow to failing test file first.

## Windows Notes

- Run Python from project venv when documented.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## WSL2 Notes

- Prefer WSL for Linux CI parity.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## Verification Checklist

- [ ] `${TEST_CMD}` or pytest green for touched area
- [ ] sync + frontmatter checks when agent assets changed
