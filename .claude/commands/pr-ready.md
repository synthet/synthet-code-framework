> **Claude Code:** Same intent as Cursor `/pr-ready`. When customizing, keep in sync with `.cursor/commands/pr-ready.md`.

# /pr-ready — Prepare for pull request

Use when implementation is complete and you want a merge-ready PR.

This is the **definition-of-done** check: merge readiness (checks green, hygiene, issue linkage).
Spec satisfaction is a separate question — run the `validate-implementation` skill first for
per-criterion verification; do not conflate "meets spec" with "mergeable".

## Inputs

- Diff or branch state; **AGENTS.md**; optional issue link.
- Validation report from `validate-implementation` if a spec with acceptance criteria exists.

## Output

1. **Summary** — User-facing description of the change (not the commit list).
2. **Risk / rollout** — Breaking changes, migrations, config.
3. **Testing** — Commands run and results.
4. **Suggested commit message** — Prefer [Conventional Commits](https://www.conventionalcommits.org/); use skill `commit-conventions` if present.
5. **PR description** — Paste-ready Markdown; align with `templates/pull_request_template.md` if the repo uses it.

## Self-review

- Scan diff for **debug code**, **TODOs** that should be issues, and **accidental files**.
- Confirm no secrets or large binaries.

## Definition of done

- Lint/test commands from **AGENTS.md** ran and are green (state actual results; never "probably green").
- Spec ACs are Verified per `validate-implementation`, or open Unknowns/Failures are listed explicitly.
- PR references its backlog item using the selected provider's convention (`Refs <ID>` or `Closes #<N>`); if the provider tracks status, the item is marked review-ready.
- Diff is clean: no debug code, secrets, large binaries, or unrelated refactors.

## Done when

- Maintainer can open a PR without rewriting the description.

## Optional

- For long-running PR hygiene (comments, CI loops), use a dedicated “babysit PR” skill in your personal skills directory if configured.
