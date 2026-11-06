# Backlog providers

This directory defines the backlog-provider contract for projects seeded from this framework. The
provider is the system of record for selectable work, ownership, status, and PR linkage.

## Default provider order

0. **agent-flow** — use it whenever `.agent-flow/config.json` exists in the repo root. It is a
   dedicated agent tracker with a dependency-aware ready queue, atomic leased claims, evidence-backed
   acceptance criteria and a web board; see [`providers/agent-flow.md`](providers/agent-flow.md).
1. **Local Markdown** — simplest default for generic/offline projects; see
   [`providers/local-markdown.md`](providers/local-markdown.md).
2. **GitHub Issues** — default when the repo is hosted on GitHub and issue tracking is enabled; see
   [`providers/github-issues.md`](providers/github-issues.md).
3. **GitHub Projects** — optional board layer for teams that need project fields/stages; see
   [`providers/github-projects.md`](providers/github-projects.md).

Choose agent-flow when several agents share the backlog, because Local Markdown has no atomic
claims. Optional placeholders for other hosted trackers live in [`providers/linear.md`](providers/linear.md)
and [`providers/jira.md`](providers/jira.md).

## Generic five-step contract

Every provider should support the same lifecycle:

1. **Pick** the highest-priority ready item from the provider's ready queue.
2. **Claim** it by recording an owner/assignee before starting work.
3. **Start** it by moving it to the provider's in-progress state on the first commit.
4. **Block** it visibly with the reason and unblock condition if progress stops.
5. **Reference** it in the PR/merge request and mark it review/done according to provider rules.

Provider-specific commands, field IDs, labels, and status names belong in the provider files, not in
generic workflow docs.
