# CLI tool skills — maintenance contract

Vendored from the agent CLI tools enablement prompt. **Canonical skill paths** in this repo:

```text
.claude/skills/<name>/SKILL.md
```

Mirror to `.cursor/skills/` via `python scripts/sync_assistant_trees.py`. Do not use repo-root `skills/`.

## Goal

Maintain practical agent skills for lightweight CLI tools on Windows, WSL2, macOS, and Linux: fast search, safe edits, bounded output, and reliable verification.

## Required deliverables (12 topic skills)

| Skill directory | Role |
|-----------------|------|
| `cli-tools-overview` | Router + links to shared references |
| `safe-command-patterns` | Bounded output, inspect-before-edit, confirmation gates |
| `install-checklist` | Human workstation provisioning (not agent-automated) |
| `search-and-navigation` | rg, fd, fzf, tree, eza, zoxide, bat, delta |
| `structural-code-search` | ast-grep, semgrep, tree-sitter, ctags |
| `git-and-diff-workflows` | git, gh, git-filter-repo, gitleaks |
| `data-config-tools` | jq, yq, dasel, sqlite3, curl, httpie |
| `task-env-package-tools` | just, mise, uv, docker, project runners |
| `lint-format-security` | ruff, prettier, eslint, trivy, shellcheck |
| `mcp-code-intelligence` | MCP tiers; CLI vs structural vs embeddings |
| `windows-agent-tooling` | Native Windows host guidance |
| `wsl2-agent-tooling` | WSL2 build/test/MCP guidance |

**Net-new router (13th CLI skill):** `search-tool-selection` — when to pick fd → rg → ast-grep (and fff MCP when connected).

Shared references live under `cli-tools-overview/references/` (install blocks, bounded output, confirmation gates, Windows/WSL split).

## Skill file requirements

Each `SKILL.md` must include these headings (in order):

1. Purpose
2. When to Use
3. Required Tools
4. Install (### Windows PowerShell, ### WSL2 Ubuntu, ### macOS)
5. Common Commands
6. Agent-Safe Patterns
7. Commands Requiring Confirmation
8. Troubleshooting
9. Windows Notes
10. WSL2 Notes
11. Verification Checklist

YAML frontmatter: `name` (first key, matches directory) + non-empty `description`.

## Agent-safe command rules

- Prefer bounded output; avoid dumping whole files.
- Prefer `rg`, `fd`, `sed -n`, `bat --line-range`, `git diff --stat`.
- Never recommend destructive commands without explicit confirmation.
- Always `git status --short` before editing; show `git diff --stat` before finalizing.
- Prefer project task runners (`just`, `npm run`, Makefile) over ad hoc commands.
- Do not assume repo language before inspecting files.

## Windows/WSL split (recommended)

```text
Windows host:
  VS Code / Cursor / Claude Desktop / Docker Desktop / local LLM apps

WSL2 Ubuntu:
  repositories, git, rg/fd/jq/yq, ast-grep, build tools, test commands, MCP servers
```

Native Windows is enough for: simple search, editing, GitHub CLI, Python with `uv`, Node with `pnpm`.

Prefer WSL2 for: Bash-heavy repos, Docker Compose, monorepos, MCP servers expecting Unix paths, CI-like test reproduction.

## MCP tiers (mcp-code-intelligence)

```text
Minimal:  rg + fd + read_file + git diff + patch_file
Better:   rg + fd + ast-grep + git tools + task runner + optional fff MCP
Advanced: Serena or codebase-memory-mcp + Zoekt + optional embeddings
```

Embedding-first indexing is heavier — secondary to text/structural search.

## Validation

Run after any CLI skill change:

```bash
python scripts/validate_cli_skills.py
python scripts/sync_assistant_trees.py --check
python scripts/ci/check_agent_frontmatter.py
```

Validator checks: all 13 CLI dirs exist, required headings, platform install subsections, no repo-root `skills/` directory.

## Quality bar

Usable by another coding agent without extra explanation. Practical commands, safe workflows, clear platform distinctions.
