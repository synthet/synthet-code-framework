# Local backlog

| ID | Status | Priority | Owner | Title | Notes |
|----|--------|----------|-------|-------|-------|
| L-001 | In Progress | p1 | agent | Compile skill wave 2: task-env, lint-format-security, eval | Harnesses + thin bootloaders; Refs L-001. GitHub Issues create blocked (403). |
| L-002 | Done | p1 | agent | Centralized permission auto-approval gate (hook → Jev → audit → approve/ask) | Plan: ~/.claude/plans/immutable-tinkering-pebble.md. Parsers in scripts/harness_logs; gate in _agent-infra/jev. Skill: centralized-permissions. Docs: docs/centralized-permissions.md. CLI: scripts/manage_permissions.py. Applied receipt: backups/20261024T173100294698Z/receipt.json. Zero drift verified. |
| L-003 | In Progress | p1 | claude:8b1e2653 | Shared harness registry (`.agent/harnesses/registry.json`) | Schema + stdlib loader `scripts/harness_registry.py` (validate/list/resolve/audit); `scripts/harness_logs` migrated; gate parity test. Uncommitted on `feat/harness-registry`. Refs L-003. |
| L-004 | Ready | p2 | — | Adopt the harness registry in consumers | infra/jev gate (`adapters.py`, `installer.py`), synthet-agent-swarm (uses `agy` as id), synthet-agent-mailbox wake clients, synthet-agent-flow actors, ai-quotas collectors. Vendor a copy + `audit` in each CI. Discovered from L-003. |
| L-005 | In Progress | p1 | claude:8b1e2653 | agent-flow as the default backlog provider when installed | `bootstrap.py --backlog auto` (default) picks agent-flow when its CLI is on PATH; `--backlog agent-flow` runs init + install --framework; backlog README + backlog-queue skill updated. Uncommitted. Wiki export side: synthet-agent-flow af-a1e16. Refs L-005. |
