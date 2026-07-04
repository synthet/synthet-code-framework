---
name: mcp-code-intelligence
description: Compare MCP code intelligence tiers — CLI wrappers, ast-grep, Serena, Zoekt, fff file search, embeddings. Prefer text search before heavy indexes.
---

# MCP code intelligence

## Purpose

Choose the right code-intelligence layer: shell tools, MCP servers, embeddings.

## When to Use

- Setting up agent MCP servers
- Deciding fff vs rg vs semantic/embedding search
- Evaluating Serena, Zoekt, codebase-memory-mcp

## Required Tools

Optional MCP: fff (`ffgrep`, `fffind`, `fff-multi-grep`), ast-grep MCP, Serena, Zoekt, embedding servers.

## Install

Install blocks are shared — See [install-blocks.md](../cli-tools-overview/references/install-blocks.md).

### Windows PowerShell

Use winget blocks from the reference when provisioning a new machine.

### WSL2 Ubuntu

Use apt/curl blocks from the reference; symlink `fdfind` → `fd` if needed.

### macOS

Use Homebrew blocks from the reference.


## Common Commands

**Tier recommendation:**

```text
Minimal:  rg + fd + read_file + git diff + patch_file (IDE/shell)
Better:   above + ast-grep + gh + task runner + fff MCP (optional)
Advanced: Serena or codebase-memory-mcp + Zoekt + optional embeddings
```

**fff MCP (optional):** Install [fff-mcp](https://github.com/dmtrKovalenko/fff); add to `.cursor/mcp.json` from `.cursor/mcp.example.json` `_examples.fff-mcp`. Reload MCP. Prefer fff for repeated repo file/content search when connected.

**Warning:** Embedding-first indexing is memory-heavy — use after rg/ast-grep/fff.

Compare:

| Layer | Best for |
|-------|----------|
| CLI rg/fd | Fast text, gitignore-aware |
| fff MCP | Indexed repo search, multi-pattern grep |
| ast-grep MCP / sg | Structural patterns |
| Serena / ctags | Symbols, refs |
| Zoekt | Large org code search |
| Embeddings | Fuzzy conceptual search (secondary) |

## Agent-Safe Patterns

- Read MCP tool schemas before CallMcpTool.
- No secrets in MCP args; See [bounded-output-patterns.md](../cli-tools-overview/references/bounded-output-patterns.md).

## Commands Requiring Confirmation

MCP tools that write files or run jobs need user intent. See [commands-requiring-confirmation.md](../cli-tools-overview/references/commands-requiring-confirmation.md).

## Troubleshooting

- fff not found: add `%LOCALAPPDATA%\fff-mcp\bin` to PATH or use full path in mcp.json.
- MCP server won't start: check WORKSPACE_ROOT env.

## Windows Notes

- fff-mcp runs natively on Windows; many MCP servers prefer WSL.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## WSL2 Notes

- Run Unix-first MCP servers here.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## Verification Checklist

- [ ] MCP tier matches task (text before embeddings)
- [ ] fff optional and documented as opt-in
- [ ] Tool schemas read before first call

