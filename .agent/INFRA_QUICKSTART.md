# Infra quickstart — ${PROJECT_NAME}

One page: what to run, what's safe, and what never to touch.

## Purpose

Get an agent productive fast without breaking safety invariants.

## Safe commands (read-only first)

```bash
git status && git log --oneline -n 20      # repo state
python scripts/okf_lint.py --profile project --exclude-prefix archive/ docs   # docs health
python scripts/agent-memory/context.py     # load project memory
${TEST_CMD}                                # tests (see AGENTS.md)
```

## After changing agent assets

```bash
python scripts/sync_assistant_trees.py     # regenerate .cursor/ mirror from .claude/
```

## Known pitfalls

- Edit assets under `.claude/` (canonical), not `.cursor/` (generated).
- Memory: never hand-edit `.agent-memory/memory.md`; use log → dream → promote.
- `.agent/scratch/`, `.agent-memory/raw-sessions/`, `.agent-memory/dreams/`, `.agent-runs/` are gitignored.

## Do not

- Do not modify `.git/config` or add git extensions.
- Do not commit secrets (`secrets.json`, `.env`).
- Do not run write-capable MCP tools without an explicit request ([`SAFETY.md`](SAFETY.md)).
