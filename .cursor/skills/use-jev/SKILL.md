---
name: use-jev
description: Use when the user says "use jev", "use Jev for decision making", "use Jev to make decision on each item", "use jev to assess", "use jev mcp", or types /use-jev. Hands the open decisions, blocked steps and triage items of the current work to Jev in one batched call. Then it executes what Jev clears and hands back what Jev denies, never using Jev to bypass a hook or permission.
capability: "Resolve pending decisions and triage with Jev, act on confident low-risk picks, and hand denied or high-risk items back with exact commands."
side_effect_level: remote_write
approval_required: false
requires_tools: "MCP jev-engineering (jev_assess_risk, jev_decide, jev_route_task) and/or jev-rw-systemone (jev_system_one, jev_choice, jev_score, jev_noul)."
output_schema: "Verdict table (item | Jev answer | confidence | action), work done for cleared items, and paste-ready commands for items left to the user."
risk_class: medium
---

# Use Jev

"use jev" means: **stop asking me, let Jev settle the open decisions, then keep working.** It is not a
request for a report about Jev. It also does not grant authority. Jev advises, and the hooks, the
permission rules and the user still decide what may run.

## 1. Collect the decisions

From the current conversation, list every open item:

- questions you were about to ask the user, and pending `AskUserQuestion`-style choices;
- blocked steps from `/next-steps` or `/step-by-step`, such as "waiting on you" items;
- multi-item triage: merge or hold each PR, what to do with each group of uncommitted work, keep or cull.

For each item, write a short neutral statement of the item, the closed set of options, and the evidence:

- the options always include a "leave / defer / none fits" choice;
- evidence means diff stats, CI state, issue numbers, test results and who owns the item.

Sanitize the evidence. Never send secrets, credential files, `config.json`, `.env` or private keys.
Leave out private paths, raw transcript text and any terms a project prohibits. Describe them
instead, e.g. "body text uses prohibited terms".

Run cheap deterministic checks first (lint, tests, hashes, link targets, term scans, which processes
or sessions use a path) and send their results as flags. If a check settles the question, skip Jev.

## 2. Pick the tool

| Need | Tool |
|------|------|
| Whether a concrete action is acceptable (merge, push, edit a protected or permission file, delete) | `jev_assess_risk` (jev-engineering). It returns deny, ask or defer, never allow. |
| Classify a task: type, complexity, whether it needs clarification | `jev_decide` (jev-engineering) |
| Model or route choice at a subagent boundary | `jev_route_task`; keep its choice for the whole task |
| Choose between options, score, yes/no over evidence | `jev_system_one` batch, or `jev_choice` / `jev_score` / `jev_noul` (jev-rw-systemone) |

If `jev-engineering` is disconnected:

- Say so in one line.
- Use `jev-rw-systemone` for the semantic choices.
- Anything the harness hook gates stays denied. Do not route around it.

Batch independent questions into **one** call. Every call costs money.

## 3. Act on the answers

| Jev answer | What to do |
|------------|------------|
| Choice/Score confidence ≥ 0.5 and the action is reversible and low-risk | Do it now, following the normal workflow: issue, branch, tests, PR. Don't stop to ask. |
| Confidence < 0.5, or a Noul between 0.4 and 0.6 | Re-ask **once** with more evidence (issue numbers, CI, diffs). If it is still low, leave the item and report it. Act on a Noul ≥ 0.6; drop the item below 0.4. |
| Choice near-tie between options that are all reversible and low-risk, with "none" near 0 | Do them in sequence and say so. Jev ruled out doing nothing, not either option. |
| Near-tie where one option is "keep as is / leave local" (e.g. 0.51 vs 0.48) | Hold: leave the item unchanged and report it. |
| Split between a reversible option and a destructive one (move to an ignored folder vs delete) | Take the reversible one. |
| `jev_assess_risk` returns **deny** | Don't act. Hand the item to the user with the exact command, e.g. `! gh pr merge 205 --merge`. |
| `jev_assess_risk` returns **defer** or **ask** on a permission, settings or protected-branch change | Still the user's call. Ask once in the summary; don't edit. |
| `jev_decide` returns `needs_clarification: false` | Implement without further questions. Exclude the parts that need human authorization. |

An answer holds only for the state it was given. When that state changes materially (a PR merges, a
step finishes, new evidence arrives), ask the follow-up decision again rather than reusing the old pick.

Items that need the user's go-ahead (see the hard limits): put them all into **one** clickable
question right after the Jev results, each with a recommended option, the evidence and a "not
yet" choice. Don't ask again in prose.

Immediately before running an approved action, re-check the state the approval assumed: fresh
fetch, target unchanged, containers in the expected state, nobody using the path. If anything
differs, stop, restore what you touched and report. Before stopping shared resources (containers,
databases, folders), ask the other local sessions via `ListAgents` and `SendMessage` and wait for
each one's "safe".

**Hard limits.** These hold no matter what Jev says:

- Deterministic deny rules and hooks win. Never retry a blocked command in a reworded form to get past a hook.
- A hook block on harmless wording (such as "secrets" in a PR body) is not a bypass request. Rephrase the text or use a file.
  The jev-engineering pre-tool hook also blocks commands that contain secret-pattern regexes or the
  `check_secrets` script name. Run other scans in a separate command, and ask the user to run
  `! python scripts/ci/check_secrets.py` themselves.
- These always need the user's explicit go-ahead:
  - force-push;
  - merging another session's PR or merging to `main`/`master`;
  - edits to `.claude/settings*.json` or other permission policy;
  - deleting user data;
  - production deploys.
- Jev can't stand in for a documented gate: runbook prerequisites, qualification receipts, review
  sign-off. Report the gate as blocked; don't offer it as a Jev option.
- Don't disable or remove a working Jev integration as a workaround.
- Confidence is not proof. Verify with tests and checks before you claim an item is done.

## 4. Photo and content decisions

For keep/cull, near-duplicate audits, label conflicts and similar photo judgments:

1. Run independent LLM judges over the evidence first: Claude, Codex, Gemini, Cursor.
2. Resolve with one batched Jev call over their verdicts plus the measurements.
3. Record the results as judge/Jev verdicts, never as owner labels.

Irreversible steps such as a hard delete still need the user.

## 5. Report

Keep the report short, then continue the work:

```markdown
| Item | Jev answer | Confidence | Action |
|------|-----------|-----------|--------|
| Merge PR #730 | deny (high risk) | 0.85 | left for you: `! gh pr merge 730 --merge` |
| Implement #203 | feature, no clarification | 0.54 | implemented on fix/203-…, PR #206 |
| Allowlist `npm run typecheck` | defer (low risk) | 0.08 | left for you: permission change |
```

When Jev barely discriminates (all items scored within a few points), say so under the table, so
the numbers aren't read as a ranking.

After the table, list:

- what you actually ran and verified;
- each item left for the user, with a paste-ready command.

If the user states a new durable rule about Jev, save it as a feedback memory.

## Examples from past sessions

- "use Jev to make decision on each item" over PR merges and dirty-tree groups: one `jev_system_one` batch. Adding issue evidence raised several picks from about 0.3 to 0.6–0.9 confidence.
- "use jev" while blocked:
  - `jev_assess_risk` returned deny on merges and defer on a settings allowlist edit, so those were handed back.
  - `jev_decide` cleared a docs and typecheck fix, which was implemented and opened as a PR in the same turn.
- "use jev" over a production rollout (image-scoring, 2026-10-31):
  - first ask, PR still open: "merge first" (0.62, confidence 0.43), the plan's own next step;
  - re-asked after the merge: "continue into shadow" (0.79);
  - activation was never offered, because its qualification gate was unmet.
- "use jev" to triage saved work groups: noul per group. One group cleared at 0.60, three stayed
  put at 0.10–0.43, and a 0.31-confidence choice for the rest was not acted on.
- "use jev" with `jev-engineering` down:
  - `jev_system_one` chose "issue first, then a small PR" and the fix route.
  - The hook still blocked the force-push, so the user got the exact `!` command.
- "use jev" over hub cleanup leftovers (image-scoring, 2026-11-01):
  - moving drafts with prohibited terms into an ignored folder, rather than deleting them, won at
    0.97 and was done;
  - a commit-or-keep-local bundle tied 0.51/0.48 and was held;
  - pushes had an advisory 0.85, and `jev_assess_risk` said ask, so both went into one clickable
    question and were approved there;
  - a folder rename the user had approved was aborted: Docker had come back up and another
    session was working in the folder;
  - the later retry waited for three peer sessions' "safe", then rolled back cleanly because
    terminals had the folder as their working directory.
