# Explicit setup synchronization

Run these commands from a maintained checkout of synthet-code-framework with Python 3.11+; use the locally configured Python runner on Windows. The installer itself is stdlib-only.

```sh
python scripts/agent_setup.py inventory --projects-root <projects> --user-root <profile>
python scripts/agent_setup.py plan --projects-root <projects> --user-root <profile> --project <name> --out .agent/local/setup/pilot.json
python scripts/agent_setup.py apply --projects-root <projects> --user-root <profile> --input .agent/local/setup/pilot.json
python scripts/agent_setup.py check --input <receipt.json>
python scripts/agent_setup.py rollback --input <receipt.json> --projects-root <projects> --user-root <profile>
```

Omit --project to include eligible maintained roots. --scope global or projects limits the plan. Inventory includes upstream checkouts and archives; installation excludes them, linked aliases and duplicate worktrees. Remotes identify synthet-owned roots; local source/config evidence identifies projects without remotes. Review eligibility before apply.

Plans contain exact content and before/after hashes. Receipts, baselines and backups live under ignored .agent/local/setup and may contain existing private configuration. Never commit or export them. Changed-after-plan destinations and unmanaged conflicts are preserved. Rollback restores only unchanged installer writes and verifies backup hashes.

Claude uses .claude assets and CLAUDE.md; Codex uses .agents/skills, .codex/agents and AGENTS.md; Cursor discovers shared skills and uses .cursor rules/commands/agents; Antigravity uses .agents/skills/rules/agents and native mcp_config.json. User deployments additionally use .gemini/config for Antigravity. Existing legacy installations are retained.

The library manifest assigns skills to tiers: shared skills install at user level and stack packs only into repositories that opt in. Plans delete a retired repository copy only when its whole bundle is unmodified and unreferenced; otherwise they report `tier-collision` or `tier-review`. Refresh the user tier before pruning repositories. Project-native skills take precedence in packaging. MCP adapters add missing validated registrations, never replace a conflicting user entry or copy literal credentials. Missing executables, paths, disabled sources and unsupported auth are diagnostics, not successful activation.

Use the local receipt and subsequent plan as evidence; file installation alone does not prove a remote MCP is healthy or an IDE has reloaded it.

## Installing one skill

`plan` has no per-skill option. To take in one skill (for example after its PR merges), make the full plan, then keep only that skill's operations:

1. `plan --scope global --state <state> --out <state>/plan-full.json`. Use **the `--state` folder your earlier installs used**: the one holding `targets/*.json`, by default `.agent/local/setup` in the checkout that ran them. A scratch worktree has its own default and no ownership ledger, so its plan shows hundreds of unrelated creates and conflicts.
2. Write a copy of the plan that keeps only the operations whose `relative` path is under `<tree>/<skill>/` for the four user skill trees (`.claude/skills`, `.agents/skills`, `.gemini/config/skills`, `.gemini/antigravity-cli/skills`). Update `summary` to match.
3. Have the user review that list, then `apply --input <cut plan>` and `check --input <receipt>`.

This is safe because `apply` checks every operation it is given (library and installer hashes, the target root, the destination folder, the content hashes) without requiring the full list. Conflicts are skipped and recorded in the receipt. The ownership ledger merges, so other skills' entries stay.

## Tracked repository copies

`plan` needs an ownership ledger, so it can't remove tracked copies from a repository that has none. `tracked-retire --project <name> --out <report.json>` lists them instead and changes nothing. A skill is listed only if every copy, in every tree, is committed, unedited, unreferenced by the repository, and equal to some past library version. The report says why anything else stays.

Remove the listed files with `git rm` on a branch and open a PR, so history is the rollback. Check that the shared skills are installed at user level first.

## Private overlay

`plan --overlay <manifest.json>` adds skills that must not live in this library. They install at user level with the same ledger, receipts and rollback. The manifest is `{"skills": [{"id": "<name>", "source": "<path>"}]}`, each source sits beside the manifest, and a name that clashes with the library stops the plan. Keep the manifest and its skills in a private location. Plans and receipts then hold their content, so keep those under ignored state too.

## State folder

`--state` decides where the ownership ledger and receipts live, and its default is the running checkout's own `.agent/local/setup`. A plan made from a worktree or a temporary folder must pass `--state <main checkout>/.agent/local/setup` on `plan`, `apply` and `rollback`. Otherwise the ledger lands outside the main checkout, and the next plan treats the installed files as unmanaged conflicts. Check that the receipt path `apply` prints is under the main checkout.

## Comparing installed copies

- Use the ownership ledger in `.agent/local/setup/targets/`, not raw hashes. Installation rewrites skill content (placeholders, shared reference links, a footer), so an unedited copy hashes differently from its source.
- An empty plan doesn't prove a copy matches the framework. The 3-way merge keeps a local edit when the framework side hasn't changed, and plans it as `unchanged`.
- Before adding a skill to the library, compare it with any existing user copy, which may be newer than the framework's. Keep the newer text, or the install replaces it.

## Adopting a foreign skill tree

Copying another repository's `.agents` or `AGENTS.md` adds skills and operating rules. It does not replace the destination project's contract, toolchain, or a ban on sibling links.

Author the new skills under the destination's `.claude/skills/`. If that project has `scripts/sync_assistant_trees.py`, run it so `.agents/skills` and `.cursor/skills` match. If it does not, copy the same skill directories into `.claude/skills`, `.agents/skills`, and `.cursor/skills`. Leave existing skills in place.

From a foreign `AGENTS.md`, keep rules that apply in the destination, such as evidence handling, provider authority, and setup approval. Leave that repository's package manager, generated guidance blocks, and links to files that exist only there.
