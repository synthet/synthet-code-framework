# Agent harness registry

[`registry.json`](registry.json) is the one list of coding-agent harnesses this framework and its
sibling tools support: Claude Code, Codex, Cursor agent, Antigravity, Grok, and the retired Gemini CLI.
Each entry gives the canonical id and aliases, CLI command and argv, home directory and its override
variable, instruction files, MCP config files, permission files, hook file and events, transcript
folders, and whether the Jev permission gate supports and can approve for it.

The contract is [`registry.schema.json`](registry.schema.json). `scripts/harness_registry.py`
validates the same rules with the standard library, so no extra dependency is needed.

```bash
python scripts/harness_registry.py validate
python scripts/harness_registry.py list --all
python scripts/harness_registry.py resolve agy          # -> antigravity
python scripts/harness_registry.py audit --root D:/Projects   # read-only drift report, exit 1 on drift
```

## Rules

- **Canonical ids** are `claude`, `codex`, `cursor`, `antigravity`, `grok` (active) and `gemini`
  (retired). Other spellings (`claude-code`, `agent`, `cursor-agent`, `agy`) are aliases; consumers
  normalise through `resolve` before comparing.
- **Paths** start with `~/` or `%APPDATA%/` and are expanded per machine; a `home.env` variable such as
  `CLAUDE_CONFIG_DIR` overrides the home.
- **Change the registry first.** Adding a harness, renaming a config file or a hook event starts here,
  in the same PR as the framework code that reads it. Consumers then update their copy or loader.

## Consumers

| Consumer | Reads the registry | Today |
|---|---|---|
| `scripts/harness_logs` (this repo) | yes, ids and homes | migrated |
| `infra/jev` permission gate (`adapters.py`, `installer.py`) | not yet | `tests/test_harness_registry.py` fails if its harness tuple or approval map drifts |
| `synthet-agent-swarm` (`src/harness/registry.ts`, `config.default.json`) | not yet | covered by `audit`; uses `agy` as its id for Antigravity |
| `synthet-agent-mailbox` (wake clients, MCP snippets) | not yet | not probed |
| `synthet-agent-flow` (actor prefixes) | not yet | not probed |
| `ai-quotas` (CLI collectors) | not yet | not probed |

Repos outside this one should vendor a copy of `registry.json` into their package and check it with
`audit` (or a digest comparison in their CI) rather than reading this checkout at runtime.
