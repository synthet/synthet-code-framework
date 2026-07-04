---
name: search-tool-selection
description: Choose the right search tool before running commands — fd vs rg vs grep vs ast-grep vs fff MCP vs IDE Grep. Use at the start of any code-finding task.
---

# Search tool selection

## Purpose

Route agents to the correct search tool **before** running commands.

## When to Use

- Any code-finding or exploration task
- `rg` returns too many false positives
- Unsure whether to use shell, MCP, or IDE tools

## Required Tools

Optional: `fd`, `rg`, `ast-grep`, fff MCP (`ffgrep`, `fffind`, `fff-multi-grep`), IDE Grep/SemanticSearch/Glob.

## Install

Install blocks are shared — See [install-blocks.md](../cli-tools-overview/references/install-blocks.md).

### Windows PowerShell

Use winget blocks from the reference when provisioning a new machine.

### WSL2 Ubuntu

Use apt/curl blocks from the reference; symlink `fdfind` → `fd` if needed.

### macOS

Use Homebrew blocks from the reference.


## Common Commands

**Default escalation:** `fd` (filename) → `rg` (content) → `ast-grep` (syntax) → `bat`/`Read` (slice).

| Task | Use | Avoid |
|------|-----|-------|
| File by name/path | `fd` | `grep -r` for filenames |
| Text/literals in contents | `rg` | bare `grep -r .` |
| grep fallback | `grep` with path scope | when `rg` available |
| Syntax/AST shapes | `ast-grep` | regex alone |
| Security rule packs | `semgrep scan` | ad hoc rg for policy |
| Symbol index / cross-ref | `ctags`, Serena MCP, Zoekt | rg for every ref |
| Repo layout | `tree -L 3` | loading all paths |
| Interactive pick (human) | `fzf` | **agents** (non-interactive) |
| Config keys in JSON/YAML | `jq` / `yq` | rg on minified JSON |
| Repeated repo search (MCP connected) | **fff** `ffgrep`/`fffind` | many grep tool roundtrips |
| Cursor agent | Grep / SemanticSearch / Glob | shell when tool bound |

**grep vs rg:** Always prefer `rg`. Use `grep` only if `rg` is unavailable.

**fff MCP:** When connected, prefer fff tools for repo-wide file/content search; keep one-off bounded probes as `rg`/`fd`.

**fzf:** Humans only — agents use `--max-count`, `-l`, `-g`, explicit paths.

Exclude globs: `node_modules`, `dist`, `build`, `.git` (add domain dirs in downstream projects).

## Agent-Safe Patterns

- See [bounded-output-patterns.md](../cli-tools-overview/references/bounded-output-patterns.md).
- Stop escalating when the task is satisfied — do not chain all tools by default.

## Commands Requiring Confirmation

See [commands-requiring-confirmation.md](../cli-tools-overview/references/commands-requiring-confirmation.md).

## Troubleshooting

- Too many rg hits: narrow path, add `-g '!tests'`, or switch to ast-grep.
- fff MCP unavailable: fall back to `rg`/`fd`; see mcp-code-intelligence for setup.

## Windows Notes

- IDE tools often beat shell on Windows for first pass.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## WSL2 Notes

- ast-grep and semgrep often smoother in WSL for large repos.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## Verification Checklist

- [ ] Picked tool matches task type (name vs text vs syntax)
- [ ] Output bounded before reading files
- [ ] fff MCP used only when server is connected

