---
type: Reference
title: Housekeeping Protocol
description: The contract every per-domain housekeeping tool implements — scan, describe, jev, decide, apply, verify, restore — with plan schema, approval classes and exit codes.
resource: housekeeping-protocol.md
tags: [agents, housekeeping, safety, jev, swarm]
timestamp: 2026-11-12T00:00:00Z
okf_version: 0.1
---

# Housekeeping protocol

Housekeeping is split by domain. Each tool lives in the repository that owns its domain and works without the others:

| Task id | Domain | Tool | Repository |
|---|---|---|---|
| `git` | Merged branches, stale worktrees, temp folders, dirty-worktree rescue | `projects-housekeeping` harness | vault |
| `transcripts` | Exported agent session transcripts → LLM Wiki | `llmwiki housekeep transcripts` | synthet-llm-wiki |
| `sanitize` | Secrets, personal and machine-local data in project folders | `llmwiki housekeep sanitize` | synthet-llm-wiki |
| `tickets` | Stale agent-flow tickets | `agent-flow triage` | synthet-agent-flow |
| `issues` | Stale GitHub issues | `agent-flow triage --source github` | synthet-agent-flow |

The `/housekeeping` skill in this repository chains the enabled tasks. It holds no domain logic: it calls each tool's
CLI and the Jev MCP tool. Tools share this contract, not a library.

Runs are on demand. No tool schedules itself or installs a hook.

## Steps

Every tool exposes the same subcommands. All of them print JSON on stdout (ASCII-safe), and nothing changes before
`apply --apply`.

| Step | Command | Contract |
|---|---|---|
| scan | `<tool> scan ... --out plan.json` | Read-only inventory. Deterministic items get a final `action`; judgment items get `action: "decide"` and `options`. |
| describe | `<tool> describe --plan plan.json [--max-items N] [--budget-usd N]` | For `decide` items only. Writes redacted excerpts to a staging directory and asks a read-only headless agent to describe each item. Stores `description` in the plan. |
| jev | `<tool> jev --plan plan.json` | Prints a `{state, questions}` payload for one `jev_system_one` batch. |
| decide | `<tool> decide --plan plan.json --answers answers.json [--min-confidence 0.5]` | Merges Jev's choices into the plan. |
| apply | `<tool> apply --plan plan.json [--apply] [--approve ID,...] [--approval-note "..."]` | Dry run unless `--apply`. Re-checks every item first. Writes a manifest. |
| verify | `<tool> verify --manifest manifest.json` | Confirms every manifest entry took effect and every backup is valid. |
| restore | `<tool> restore --manifest manifest.json` | Prints the undo commands. Never runs them. |

"The agent describes, Jev decides": the headless agent writes prose about an item; Jev chooses among fixed options;
deterministic code applies the choice. Neither the agent nor Jev can act, and Jev's answer never replaces a
deterministic check or a human approval.

## Plan schema

```json
{
  "tool": "llmwiki-housekeep-transcripts",
  "version": 1,
  "root": "<projects-root>",
  "scanned": "2026-11-12T21:00:00Z",
  "items": [
    {
      "id": "T0003",
      "kind": "transcript",
      "action": "decide",
      "options": ["ingest_summary", "ingest_redacted_full", "discard", "hold"],
      "why": "dated export older than 7 days in repo root",
      "evidence": {"bytes": 95367, "age_days": 9, "format": "claude-terminal-dialogue"},
      "staging": "T0003.md",
      "description": "Session that ...",
      "jev": {"choice": "ingest_summary", "confidence": 0.81},
      "needs_approval": false
    }
  ]
}
```

- `id` is a one-letter kind prefix plus four digits, stable within a plan.
- `evidence` holds facts code can check later (sizes, SHAs, timestamps, counts, statuses). A secret finding records
  its type, file and line, never the value.
- `staging` is a path relative to the describe staging directory.
- Plans, payloads and staging directories live in the session scratchpad, never in a repository: they list private
  paths.

## Describe

The tool, not the caller, builds the agent's input:

1. Redact the excerpt (credentials, home paths, emails, private IPs, injected `<system-reminder>`-style blocks).
   After redaction, re-scan it; any remaining credential hit sets the item to `hold` and skips the agent call.
2. Write the excerpts to a fresh staging directory, one file per item.
3. Run synthet-agent-swarm read-only with that directory as the workspace:

```bash
WORKSPACE_ROOT=<staging> node <swarm>/agent-orchestrator/dist/index.js run --request <staging>/request.json
```

```json
{
  "task": "For each file listed, write at most 600 characters describing what it contains, what is still useful (decisions, fixes, lessons, open work) and what is noise. Do not quote secrets or personal data. Answer as JSON {\"<file>\": \"<description>\"}.",
  "files": ["T0003.md", "T0007.md"],
  "harnesses": ["claude"],
  "modelChains": {"claude": ["<default>", "<fallback>"]},
  "mode": "explain",
  "timeoutMs": 300000,
  "budgetUsd": 1
}
```

`modelChains` and `budgetUsd` are optional. Batch at most 20 files per request (the swarm `files` limit). Stop at `--max-items` or `--budget-usd`; items left
undescribed stay `decide` and are reported. A swarm `outcome` other than `ok` leaves the batch undescribed.

The repository being judged may be the workspace instead of a staging directory only when the agent needs to read
code (issue and ticket triage). It is still read-only.

## Jev payload and decide

`jev` prints:

```json
{
  "state": {
    "context": "Housekeeping triage. Reversible options: ... Permanent options: ...",
    "items": {"T0003": {"description": "...", "age_days": 9, "format": "claude-terminal-dialogue"}}
  },
  "questions": {
    "T0003": {"type": "choice", "instructions": "Choose what to do with item T0003.", "criteria": {"ingest_summary": "...", "discard": "...", "hold": "..."}}
  }
}
```

The caller sends it as one `jev_system_one` batch and saves the response as `answers.json`. `decide` then:

- takes the highest-probability choice when its confidence is at least `--min-confidence` (default 0.5);
- turns a lower confidence, a missing answer or `keep` into `hold`;
- marks `needs_approval: true` on every choice in the approval classes below.

Re-ask `hold` items once with more evidence. If confidence is still low, leave them and report them.

## Approval classes

| Class | Examples | Gate |
|---|---|---|
| Reversible local | Quarantine move, git bundle, worktree patch archive, local rescue commit, wiki ingest into `wiki/notes/_local/`, agent-flow note or label | `--apply` |
| Permanent | Deleting files or branches without a backup, purging quarantine | `--approve <ids>` + `--approval-note` |
| Remote | `git push`, any GitHub label, comment or close | `--approve <ids>` + `--approval-note` |
| Tracker state | agent-flow `cancel` or `block` | `--approve <ids>` + `--approval-note` |

`--approval-note` records the owner's words in the manifest. Jev may recommend a gated action; only the owner approves
it. `apply` refuses an id that is in the approval classes but not in `--approve`.

Backups go to `<root>/_backup/housekeeping-<date>/` (bundles, patches, quarantine). Wiki notes stay `candidate`;
no tool approves claims.

## Apply rules

- Re-check each item's evidence (HEAD, branch SHA, dirty count, file digest, `updated_at`) before acting; skip and
  report anything that changed since `scan`.
- Act only inside the plan: paths under its root, repositories it inventoried, tickets and issues it listed.
- Never delete through a junction or symlink.
- Leave repositories with a live agent session or an unexpired agent-flow lease alone. The caller checks peers before
  `apply --apply`.
- Act under an agent identity (for example `--actor housekeeping:<run>`), never `human:` or `system:`.

## Manifest

`apply --apply` writes `manifest-<HHMMSS>.json` next to the backups:

```json
{"tool": "...", "version": 1, "plan": "<path>", "applied": "2026-11-12T21:30:00Z",
 "approval_note": "...",
 "<records>": [{"id": "T0003", "mode": "ingest_summary", "backup": "...", "...": "..."}],
 "skipped": [{"id": "T0004", "why": "changed since scan"}]}
```

`tool`, `version`, `plan`, `applied`, `approval_note` and `skipped` are common. Each tool keeps its done records
in its own lists (the git harness uses `worktrees`, `branches` and `folders`); every record carries the item `id`
and enough to verify and undo it.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (for `apply`, every attempted item succeeded or was skipped as unchanged-safe) |
| 1 | Some items failed, or `verify` found a problem |
| 2 | Invalid arguments, plan or answers file |
| 3 | A prerequisite is missing (swarm, Jev answers, `gh`, the wiki root) |

## Configuration

`/housekeeping` reads `~/.agents/housekeeping.json`. Every task is optional:

```json
{
  "roots": ["<projects-root>"],
  "tasks": {
    "git": {"enabled": true, "recent_days": 2},
    "transcripts": {"enabled": true, "min_age_days": 7},
    "sanitize": {"enabled": true},
    "tickets": {"enabled": true, "stale_days": 30},
    "issues": {"enabled": false, "stale_days": 60}
  },
  "tools": {
    "git": "python -I <projects-root>/vault/.claude/skills/projects-housekeeping/scripts/harness.py",
    "llmwiki": "llmwiki --root <projects-root>/synthet-llm-wiki",
    "agent_flow": "agent-flow",
    "swarm": "<projects-root>/synthet-agent-swarm/agent-orchestrator/dist/index.js"
  },
  "describe": {"max_items": 40, "budget_usd": 2},
  "decide": {"min_confidence": 0.5}
}
```
