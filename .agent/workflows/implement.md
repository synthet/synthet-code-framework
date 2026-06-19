# /implement — Execute an approved plan

Use when the user has approved a plan or given a small, explicit task.

## Inputs

- Approved plan or task list.
- [AGENTS.md](../../AGENTS.md) for lint/test/build commands.

## Steps

1. Write the failing test stubs from the plan **before** implementation; confirm they fail.
2. Implement in **minimal diffs** until the stubs pass; match existing style.
3. Run **lint** and **tests** from [AGENTS.md](../../AGENTS.md); fix failures.
4. Summarize what changed and where.

## Done when

- All agreed items are implemented.
- Tests written-and-failing before code, now passing (or failures explained with next steps).

## Checklist

- [ ] Test stubs written and **failing** before implementation began
- [ ] Tests pass after implementation
- [ ] No unrelated refactors
- [ ] No secrets committed
- [ ] [AGENTS.md](../../AGENTS.md) commands run (or documented why not)
