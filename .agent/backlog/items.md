# Local backlog

| ID | Status | Priority | Owner | Title | Notes |
|----|--------|----------|-------|-------|-------|
| L-001 | In Progress | p1 | agent | Compile skill wave 2: task-env, lint-format-security, eval | Harnesses + thin bootloaders; Refs L-001. GitHub Issues create blocked (403). |
| L-002 | Done | p1 | agent | Centralized permission auto-approval gate (hook → Jev → audit → approve/ask) | Plan: ~/.claude/plans/immutable-tinkering-pebble.md. Parsers in scripts/harness_logs; gate in _agent-infra/jev. Skill: centralized-permissions. Docs: docs/centralized-permissions.md. CLI: scripts/manage_permissions.py. Applied receipt: backups/20261024T173100294698Z/receipt.json. Zero drift verified. |
| L-005 | In Progress | p1 | claude:8b1e2653 | agent-flow as the default backlog provider when installed | `bootstrap.py --backlog auto` (default) picks agent-flow when its CLI is on PATH; `--backlog agent-flow` runs init + install --framework; backlog README + backlog-queue skill updated. Uncommitted. Wiki export side: synthet-agent-flow af-a1e16. Refs L-005. |
| L-006 | In Progress | p2 | claude:8b1e2653 | synthet-project-template generated from bootstrap | `scripts/build_project_template.py` (build/--check) + generated `init_project.py`; built into D:/Projects/synthet-project-template (not a git repo yet). Test proves template + init == direct seed. Refs L-006. |
| L-007 | Backlog | p2 | — | Stop seeding the Jev control plane into every project | bootstrap copies `infra/jev/` and `jev-engineering/` into each seeded repo (seen in the template output). Exclude them and point to the single Jev home. Discovered from L-006. |
