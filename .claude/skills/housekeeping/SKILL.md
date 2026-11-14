---
name: housekeeping
description: Use when the user asks for housekeeping across their projects or types /housekeeping — stale worktrees and merged branches, exported session transcripts, secrets or machine-local data lying in project folders, stale agent-flow tickets, stale GitHub issues. Chains the per-domain housekeeping tools on demand (scan, agent describes, Jev decides, gated apply), each task optional. Not for C: drive caches (windows-disk-cleanup) or a single branch in the current repo.
capability: "Run the enabled per-domain housekeeping tools under one approval flow: peers check, scan, read-only agent describe, one Jev batch per task, dry run, reversible apply, one consolidated owner approval for gated items, verify, report."
side_effect_level: local_write
approval_required: true
requires_tools: "Per task: projects-housekeeping harness (vault), llmwiki housekeep (synthet-llm-wiki), agent-flow triage (synthet-agent-flow), git, gh; synthet-agent-swarm build for describe; Jev System One (jev_system_one) for decide."
output_schema: "One table per run: task → item → agent description → Jev choice and confidence → action; then held, skipped and approval-pending items with restore commands. Plans and manifests stay in the session scratchpad."
risk_class: high
---

# Housekeeping

On-demand housekeeping across a projects root. Each domain has its own tool in the repository that owns it; this
skill only chains them. The contract they share — steps, plan schema, approval classes, exit codes — is
[`docs/housekeeping-protocol.md`](../../../docs/housekeeping-protocol.md). Nothing here schedules itself.

| Task | Tool (run from anywhere) | What it handles |
|---|---|---|
| `git` | `python -I <vault>/.claude/skills/projects-housekeeping/scripts/harness.py` | merged branches, stale or dirty worktrees (rescue to `rescue/` branches), temp folders |
| `transcripts` | `llmwiki --root <wiki> housekeep transcripts` | exported session transcripts → redacted notes in the private wiki area |
| `sanitize` | `llmwiki --root <wiki> housekeep sanitize` | secrets and machine-local data in project folders |
| `tickets` | `agent-flow triage` | stale agent-flow tickets |
| `issues` | `agent-flow triage --source github` | stale GitHub issues in the user's own repos |

Usage: `/housekeeping [git|transcripts|sanitize|tickets|issues ...] [--plan]`. With no task names, run every task
enabled in the config. `--plan` stops after the dry run.

## Config

Read `~/.agents/housekeeping.json` (schema in the protocol doc): `roots`, `tasks.<name>.enabled` plus thresholds,
`tools` paths, `describe.{max_items,budget_usd}`, `decide.min_confidence`. If the file is missing, show the example
from the protocol doc, ask the user for their projects root and tool paths once, and offer to write the file; do not
guess paths. A task whose tool is not installed (its `--help` fails, or prints no `housekeep`/`triage` command) is
skipped and reported, never emulated by hand.

## Workflow

Keep every plan, staging folder, Jev payload and manifest under the session scratchpad: they name private paths.

1. **Peers first.** List live agent sessions (`ListAgents` in Claude Code). Tell any that work in a repo you will
   touch, and wait for "safe" before applying there; skip repos you cannot clear. Without a way to reach peers, ask
   the user.
2. **Scan** each enabled task (read-only). Read each summary; a scan that reports errors or truncation is a limit
   to report, not a pass.
3. **Describe.** Run each tool's `describe` with the swarm path from the config. Exit 3 means the swarm is missing:
   report it and continue with deterministic items only. Items the tool held as unredactable stay held.
4. **Jev decides.** Send each task's `jev` payload as one `jev_system_one` batch, save the answers next to the
   plan, then run `decide --answers`. Without Jev, put the same questions to the user once. Re-ask `hold` items once
   with more evidence; still low → leave and report. The agent's description informs Jev; neither one acts.
5. **Dry run** every task's `apply` and read every line. Stop here for `--plan`.
6. **Apply reversible actions** (`apply --apply`, or the tool's equivalent) — quarantine, bundles, local
   `rescue/` branches, private wiki notes, agent-flow notes and labels — acting as an agent identity
   (`--actor housekeeping:<run>` for agent-flow), never `human:` or `system:`.
7. **One owner approval.** Collect every gated id across tasks — permanent deletes and purges, pushes, every
   GitHub write, ticket cancels, any write in a repo that mirrors to mailbox or GitHub — and ask once with ids,
   what each does, sizes or titles, and "not yet". Apply only the approved ids with `--approve` and the owner's
   words in `--approval-note`.
8. **Verify** each manifest (`verify`), then spot-check: every touched repo still has a valid HEAD and no
   unexpected `git status` changes.
9. **Report** the table from `output_schema`, then held items, skipped items with reasons, items still awaiting
   approval, and each manifest's `restore` commands.

## Rules

- Never schedule, hook or loop this skill on your own; the user runs it.
- Never apply a plan you did not just dry-run, and never apply to try things out: agent-flow notes and GitHub
  comments cannot be taken back.
- Never pass raw file content, secrets or private paths to Jev or the describe agent yourself; each tool redacts its
  own payloads, and its residual checks hold what it cannot clean.
- Jev confidence is not authorisation. Deterministic checks in each tool and the owner's approval decide.
- A task that fails stops only itself; finish the other tasks and report the failure with its exit code.
