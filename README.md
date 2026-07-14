# synthet-code-framework

A generic, reusable **agentic-AI starting point** for new projects. It bundles the agent
infrastructure that proved its worth across many repos — slash commands, skills, subagents, safety
rules, an `.agent/` governance hub, a project-memory subsystem, and OKF docs tooling — stripped of
all domain specifics so any new project starts mature instead of from scratch.

## Seed a new project

```bash
python bootstrap.py --target ../my-app --name "My App" --stack python --desc "What it does"
# Optionally include runnable starter code/resources for python, node, or go:
python bootstrap.py --target ../my-api --name "My API" --stack python --include-boilerplate
```

This copies the scaffold into `../my-app`, substitutes `${PLACEHOLDER}` tokens, and leaves clearly
marked `TODO(...)` for things only you know (repo URL and optional backlog-provider IDs). Then:

1. `cd ../my-app && git init`
2. Fill in build/test/lint commands in `CLAUDE.md` + `AGENTS.md`.
3. Choose a backlog provider in `.agent/backlog/`; fill GitHub Projects `TODO(...)` markers only if you use that provider.
4. Run `python scripts/sync_assistant_trees.py` whenever you edit `.claude/` assets.

`--stack` accepts `python | node | go | generic` (sets default build/test/lint commands). Use
`--include-boilerplate` to generate lightweight starter code/resources for `python`, `node`, or `go`;
the same generator is available later via
`python scripts/generate_project_boilerplate.py --stack <stack> --project-slug <slug> --project-desc '...'`.

## What's inside

| Area | Path | What it gives you |
|------|------|-------------------|
| Orientation | `CLAUDE.md`, `AGENTS.md` | Project + agent contract templates |
| Slash commands | `.claude/commands/` | `/spec /plan /implement /test-and-fix /pr-ready /release-notes`, wiki, memory, external-review, `/task-claim` |
| Skills | `.claude/skills/` | agent-memory, commit-conventions, security-review, critical-commit-audit, systematic-debugging, test-driven-development, verification-before-completion, karpathy-guidelines, subagent-review, backlog-queue, mcp-server-design, threat-modeling-agentic-tools, validate-implementation, release-bump, plus CLI/tooling skills |
| Subagents | `.claude/agents/` | pr-ready-hygiene, critical-commit-audit, external-cli/codex/gemini reviewers |
| Rules | `.claude/rules/` | Always-on safety, SDLC core, and Karpathy coding guardrails |
| Cursor mirror | `.cursor/` | **Generated** from `.claude/` by `scripts/sync_assistant_trees.py` |
| Codex skills | `.agents/skills/` | **Generated** repository skills for Codex |
| Codex setup | `.codex/` | Project config plus generated custom subagents |
| Governance | `.agent/` | SAFETY, provider-oriented backlog docs, inventory, subagent role matrix, SDLC workflow playbooks |
| Memory | `.agent-memory/` + `scripts/agent-memory/` | log → dream → promote → context (deterministic, no LLM) |
| Docs tooling | `scripts/okf_lint.py`, `wiki_lint.py`, `scripts/generate_agent_asset_inventory.py`, `docs/` | OKF-aligned knowledge bundle, asset inventory, and linters |

## Single source of truth

Author agent assets under **`.claude/`** + **`.agent/`**; the Cursor and Codex mirrors are generated.
After editing `.claude/`, run:

```bash
python scripts/sync_assistant_trees.py          # regenerate Cursor + Codex mirrors
python scripts/sync_assistant_trees.py --check  # CI: fail if out of sync
```

## Optional dependency

The external-CLI-review cluster (`subagent-review` skill, `/run-codex-review`, etc.) depends on a
sibling **`subagent-orchestrator`** MCP server, which is **not bundled** here. See
[`docs/EXTERNAL_CLI_REVIEWS.md`](docs/EXTERNAL_CLI_REVIEWS.md). The rest of the framework works
without it.

## Verify the framework itself

```bash
python scripts/okf_lint.py --profile project --exclude-prefix archive/ docs   # 0 errors/0 warnings
python scripts/sync_assistant_trees.py --check                                # all mirrors in sync
python scripts/generate_agent_asset_inventory.py --check                       # agent inventory docs in sync
python -m py_compile bootstrap.py scripts/*.py scripts/**/*.py                 # scripts compile
python scripts/ci/check_agent_frontmatter.py                                  # asset frontmatter contract
python scripts/ci/check_secrets.py                                            # no committed secrets
python -m pytest tests -q                                                      # bootstrap test suite
```

The same checks run in CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).
Dev dependencies: `pip install -r requirements-dev.txt`.

## Conventions

- **Backlog provider:** default to Local Markdown for generic/offline projects or GitHub Issues for GitHub-hosted repos; GitHub Projects is optional, and board/card requirements apply only when that provider is selected; its IDs live under `.agent/backlog/providers/github-projects.md`; use `/task-claim` + the five-step contract.
- **Safety first:** secrets in `secrets.json`/`.env`; never touch `.git/config`; the default
  `.claude/settings.json` is read-only, write-capable commands are opt-in via
  `.claude/settings.write.example.json`, and external exports require explicit approval. See
  [`.agent/SAFETY.md`](.agent/SAFETY.md).
- **OKF docs:** `docs/` is an Open Knowledge Format bundle — markdown + YAML frontmatter, file path =
  identity, links = graph. See [`docs/OKF_ADOPTION.md`](docs/OKF_ADOPTION.md).

## Not in v0 (next steps)

- A `cookiecutter` wrapper or GitHub "template repository" publishing.
- Language-specific test/lint runner skills (each project supplies its own).
- Auto-generating the MCP tool inventory (the marker convention ships; the generator does not).
