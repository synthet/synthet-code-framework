---
name: lint-format-security
description: Run linters and security scanners with bounded scope — ruff, prettier, eslint, shellcheck, trivy, hadolint.
capability: "lint-format-security agent asset workflow"
side_effect_level: local_write
approval_required: false
requires_tools: "See asset body for tool requirements."
output_schema: "Markdown report or documented command output."
risk_class: medium
---

# Lint, format, and security

## Purpose

Static analysis and container/config scanning without silent auto-fix at scale.

## When to Use

- Python: `ruff`, `pyright`
- JS/TS: `eslint`, `prettier`
- Shell: `shellcheck`
- Containers/IaC: `hadolint`, `trivy`

## Required Tools

Project-defined; common: `ruff`, `eslint`, `prettier`, `shellcheck`, `trivy`.

## Install

Install blocks are shared — See [install-blocks.md](../cli-tools-overview/references/install-blocks.md).

### Windows PowerShell

Use winget blocks from the reference when provisioning a new machine.

### WSL2 Ubuntu

Use apt/curl blocks from the reference; symlink `fdfind` → `fd` if needed.

### macOS

Use Homebrew blocks from the reference.


## Common Commands

```bash
ruff check path/to/module --output-format=concise
ruff format --check path/to/module
eslint src/ --max-warnings 0
prettier --check 'src/**/*.{ts,tsx,json}'
shellcheck scripts/*.sh
trivy fs --scanners vuln --exit-code 0 .
```

## Agent-Safe Patterns

- Check mode before write/fix mode.
- Scope to changed paths.
- See [bounded-output-patterns.md](../cli-tools-overview/references/bounded-output-patterns.md).

## Commands Requiring Confirmation

`--fix`, `--write`, `--auto-fix` on broad trees. See [commands-requiring-confirmation.md](../cli-tools-overview/references/commands-requiring-confirmation.md).

## Troubleshooting

- Missing plugins: use project devDependencies / uv tools.
- trivy DB download: may need network once.

## Windows Notes

- Prefer project-local `npx eslint` over global installs.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## WSL2 Notes

- Match CI linter versions when possible.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## Verification Checklist

- [ ] Linters run on narrowest scope
- [ ] User approved any auto-fix

