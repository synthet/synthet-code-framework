---
name: cli-tools-overview
description: Router for CLI tooling skills — install checklist, safe patterns, search, git, MCP. Start here for agent command-line workflows.
---

# CLI tools overview

> For **which search tool to use**, see [`search-tool-selection`](../search-tool-selection/SKILL.md).

## Purpose

Index of CLI tooling skills and shared references for coding agents on Windows, WSL2, and macOS.

## When to Use

- Starting work in an unfamiliar repo
- Choosing which specialized CLI skill to load
- Provisioning a human workstation (via install-checklist)

## Required Tools

Varies by topic skill; core: `git`, `rg`, `fd`, `jq`.

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
# Orientation
tree -L 2 -I 'node_modules|dist|build'
rg --files | head -20
git status --short
```

Benchmark/watch helpers (human): `hyperfine`, `entr`, `watchexec` — use for perf comparisons, not in agent loops.

## Agent-Safe Patterns

- Load `safe-command-patterns` before destructive or broad commands.
- Load `search-tool-selection` before repo-wide search.
- See [bounded-output-patterns.md](../cli-tools-overview/references/bounded-output-patterns.md).

## See also

| Skill | Topic |
|-------|-------|
| [search-tool-selection](../search-tool-selection/SKILL.md) | fd vs rg vs ast-grep vs fff MCP |
| [safe-command-patterns](../safe-command-patterns/SKILL.md) | Bounded output, git hygiene |
| [install-checklist](../install-checklist/SKILL.md) | Human provisioning |
| [search-and-navigation](../search-and-navigation/SKILL.md) | rg, fd, bat, tree |
| [structural-code-search](../structural-code-search/SKILL.md) | ast-grep, semgrep |
| [git-and-diff-workflows](../git-and-diff-workflows/SKILL.md) | git, gh |
| [data-config-tools](../data-config-tools/SKILL.md) | jq, yq, curl |
| [task-env-package-tools](../task-env-package-tools/SKILL.md) | just, uv, docker, project gates |
| [lint-format-security](../lint-format-security/SKILL.md) | ruff, eslint, trivy |
| [mcp-code-intelligence](../mcp-code-intelligence/SKILL.md) | MCP tiers |
| [windows-agent-tooling](../windows-agent-tooling/SKILL.md) | Native Windows |
| [wsl2-agent-tooling](../wsl2-agent-tooling/SKILL.md) | WSL2 workflows |

## Commands Requiring Confirmation

See [commands-requiring-confirmation.md](../cli-tools-overview/references/commands-requiring-confirmation.md).

## Troubleshooting

See topic skill for tool-specific failures.

## Windows Notes

- Prefer `rg` and `fd` from winget; PowerShell aliases may shadow Unix names — use full binary names if commands fail.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## WSL2 Notes

- Use Linux packages in WSL; avoid calling Windows binaries for repo work when Linux equivalents exist.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## Verification Checklist

- [ ] Required tools respond (`--version` or `--help`)
- [ ] Commands use bounded output (See [bounded-output-patterns.md](../cli-tools-overview/references/bounded-output-patterns.md).)
- [ ] Destructive ops gated per confirmation reference


