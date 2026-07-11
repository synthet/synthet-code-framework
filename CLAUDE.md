# ${PROJECT_NAME} — ${PROJECT_DESC}

> Seeded from **synthet-code-framework**. Replace this orientation with project specifics, but keep
> the **Backlog**, **Development Guidelines**, and **Documentation** sections — they encode reusable
> contracts. Run `python scripts/sync_assistant_trees.py` after editing `.claude/` assets; it updates
> both Cursor and Codex mirrors.

<!-- Optional: list sibling repos this one coordinates with.
## Related Projects

| Project | Repository | Role |
|---------|------------|------|
| ${PROJECT_NAME} (this) | ${REPO_URL} | … |
-->

## Backlog & queue (read this before picking work)

The canonical queue is the configured **backlog provider**, not ad hoc `TODO.md` notes. Generic projects default to Local Markdown; GitHub-hosted projects may use GitHub Issues; GitHub Projects is optional when a board is explicitly configured.

**Mandatory contract for every agent (human or AI). Do all five steps:**

1. **Pick from the ready queue**, sorted by priority. If ready work is empty, ask the maintainer — do not invent work.
2. **Claim** the item: `/task-claim <item-ref>` records ownership in the provider.
3. **Move to in progress** on your first commit.
4. **If blocked**, mark the item blocked and record the blocker + what would unblock it.
5. **Reference the item in the PR** with the provider-specific reference (`Refs <ID>` or `Closes #<N>`).

Do not add tasks to random `TODO.md` files, do not work without a backlog item, and do not skip provider status transitions.
Full contract: [`docs/project/00-backlog-workflow.md`](docs/project/00-backlog-workflow.md) and provider details in [`.agent/backlog/`](.agent/backlog/README.md).

## Architecture

<!-- Describe the system: major modules/components, data flow, runtime/environment. Keep a table. -->

| Module / component | Role |
|--------------------|------|
| … | … |

## Key Files

<!-- path — purpose -->
- `…` — …

## Commands

```bash
# Build / run / test / typecheck — fill in for ${STACK}
${BUILD_CMD}
${TEST_CMD}
${LINT_CMD}
```

## Testing

Tests live in `…`. Document how to run the fast subset vs. the full suite. If you have multiple kinds
of end-to-end tests, give each a distinct name and a one-line disambiguation table — avoid ambiguous
"E2E" wording.


## Tool permissions and write access

- **Default read-only mode:** the scaffolded `.claude/settings.json` only allows read-oriented inspection (`git status`, `git diff:*`, `git log:*`) plus `WebSearch`.
- **Local writes are opt-in:** to let an agent stage or commit local changes, copy or merge `.claude/settings.write.example.json` into the active Claude settings for that workspace, preferably enabling only the entries needed for the current task.
- **Remote writes are separate:** GitHub mutations through `gh pr:*`, `gh issue:*`, or `gh project:*` affect shared remote state and may notify people; enable them only after explicit task intent and target verification.
- **External export approval:** exporting code, prompts, logs, or generated artifacts to external services/providers requires explicit approval and a secrets check, even when local writes are already allowed.
- **Bootstrap inheritance:** seeded projects inherit the read-only `.claude/settings.json` so new repos begin with the safer default.

## Development Guidelines

- **No hardcoded paths** — use a config module / base-dir constant.
- **Use the logging facility** — no `print()` in library code.
- **Keep public interfaces stable** — API paths, config keys, shared types, DB column names.
- **Minimal diffs** — prefer targeted edits over rewrites; no drive-by refactors.
- **Secrets** (API keys, tokens) go in `secrets.json` / `.env` (git-ignored), never in committed config.
- **Never modify `.git/config`** — do not set `extensions.worktreeConfig`, change
  `core.repositoryformatversion`, or add git extensions. Third-party tools using embedded git libraries
  choke on non-standard extensions. If a worktree is needed, use a temporary one and clean it up immediately.

## Documentation

Start with [`docs/CANONICAL_SOURCES.md`](docs/CANONICAL_SOURCES.md) (authority map), then
[`docs/WIKI_SCHEMA.md`](docs/WIKI_SCHEMA.md) when adding/moving wiki pages.

- [`AGENTS.md`](AGENTS.md) — MCP config, tool surface, agent contract
- [`docs/ai-workflow/README.md`](docs/ai-workflow/README.md) — agent asset map + SDLC loop
- [`.agent/SAFETY.md`](.agent/SAFETY.md) — safety & hygiene rules
- [`.agent/AGENT_INFRA_INVENTORY.md`](.agent/AGENT_INFRA_INVENTORY.md) — full agent-infra inventory
