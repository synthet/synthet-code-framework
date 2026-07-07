# /pr-ready — Prepare for pull request

Use when implementation is complete and you want a merge-ready PR.

This is the **definition-of-done** gate (merge readiness). Spec satisfaction is verified
separately by the `validate-implementation` skill — do not conflate the two.

## Inputs

- Diff or branch state; [AGENTS.md](../../AGENTS.md).
- Validation report from `validate-implementation` when the work has a spec with `AC-n` criteria.

## Output (PR Ready Report)

1. **Summary** — User-facing description of the change (not the commit list).
2. **Risk / rollout** — Breaking changes, migrations, config.
3. **Testing** — Commands run and results.
4. **Suggested commit message** — Prefer Conventional Commits.
5. **PR description** — Paste-ready Markdown.

## Definition of done

- Lint/test commands ran and are green (actual results, not "probably green").
- Spec ACs Verified per `validate-implementation`, or open Unknowns/Failures listed explicitly.
- PR references its backlog item (`Refs <ID>` or `Closes #<N>`); provider status is review-ready when applicable.
- Diff clean: no debug code, secrets, large binaries, or unrelated refactors.

## Done when

- Maintainer can open a PR without rewriting the description.
