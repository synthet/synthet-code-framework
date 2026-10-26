---
name: export-chat
description: Use when the user types /export or /export-chat, or asks to export, save, dump, copy, or share the current chat, conversation, or agent transcript as a file or to the clipboard. Renders Claude Code, Codex, Cursor, Google Antigravity and Grok transcripts (user/assistant text plus full tool-call inputs) to Markdown that /resume-task can read back. Also use to export an earlier chat by id.
capability: "Export a Claude Code, Codex, Cursor, Antigravity or Grok chat transcript for the current workspace to a Markdown file or the clipboard."
side_effect_level: local_write
approval_required: false
requires_tools: "python (stdlib only); clip / pbcopy / wl-copy / xclip / xsel for --clipboard"
output_schema: "Path of the written Markdown file (or clipboard tool used) plus harness, message/tool-call counts and workspace_verified; --json for a summary object"
risk_class: low
---

# Export chat (`/export` for every harness)

Renders the newest transcript **for the current workspace** in the harness you name. Pass
`--harness` with the harness running this chat; the script never guesses between harnesses.
Only Claude Code is detected automatically (`CLAUDECODE=1`).

| `--harness` | Store read (read-only) | Native alternative |
|---|---|---|
| `claude` | `$CLAUDE_CONFIG_DIR` or `~/.claude/projects/<encoded-cwd>/<session>.jsonl`; prefers `CLAUDE_CODE_SESSION_ID` | built-in `/export` (text, `⏺` markers) |
| `codex` | `$CODEX_HOME` or `~/.codex/sessions/**/rollout-*.jsonl`, matched on `session_meta.cwd` | none |
| `cursor` | `~/.cursor/projects/<workspace-slug>/agent-transcripts/[<id>/]<id>.jsonl` | none |
| `antigravity` | `~/.gemini/antigravity-cli`, `antigravity`, `antigravity-ide` `/brain/<id>/.system_generated/logs/transcript_full.jsonl`; matched on workspace paths in tool-call arguments | Antigravity's Markdown export |
| `grok` | `$GROK_HOME` or `~/.grok/sessions/<url-encoded-cwd>/<id>/updates.jsonl` | built-in `/export` |

The script lives next to this file. Resolve it from this skill directory, for example
`.cursor/skills/export-chat/scripts/export_chat.py` in a repo or
`~/.cursor/skills/export-chat/scripts/export_chat.py` for the user-level install. Run it from the workspace root.

## Invoke

```bash
# /export            -> timestamped .md in cwd (YYYY-MM-DD-HHMMSS-<first-prompt>.md)
python <skill-dir>/scripts/export_chat.py --harness cursor --json

# /export <file>     -> write to that path
python <skill-dir>/scripts/export_chat.py notes/chat.md --harness codex --json

# Copy to clipboard instead of writing a file
python <skill-dir>/scripts/export_chat.py --harness antigravity --clipboard --json

# Export an earlier chat: list, then pass the id (prefix ok) or a .jsonl path
python <skill-dir>/scripts/export_chat.py --harness grok --list
python <skill-dir>/scripts/export_chat.py --harness grok --transcript 01a16b78 --json
```

Other flags:
- `--workspace <path>` (default cwd). Junctions and symlinks match both the launched and the resolved path.
- `--any-workspace` drops the workspace filter.
- `--raw` keeps injected wrapper tags (`<system_reminder>`, `<user_info>`, `<ADDITIONAL_METADATA>`, …). By default only the user's own text (`<user_query>`, `<USER_REQUEST>`) is kept.
- `--<harness>-home` overrides a store root.

## Output format (read by /resume-task)

```
# Chat export

- Harness: <claude|codex|cursor|antigravity|grok>[ (<store>)]
- Transcript: `<session id>`
- Workspace: `<path>`
- Exported: <ISO time>
- Resume: `<native resume command>`        (when the harness has one)

## User / ## Assistant sections, **Tool: <name>** + fenced input, --- between turns
```

`/resume-task` reads these files with `--md`. It attributes them to the harness, takes the project from
`Workspace`, rebuilds the resume command and records files from edit-tool inputs.

## LLM judgment slots

- Always pass `--harness` naming the harness you are running in.
- Use the filename or destination the user gave after `/export`. If they gave none, use the default.
  If they said "clipboard", pass `--clipboard`.
- If the result says `"workspace_verified": false` (Antigravity chat that has not touched a workspace
  path yet), say so in the reply.
- Report the output path and counts from the JSON result in one sentence.

## Limits

- Tool *results* are not exported, only tool inputs. Antigravity `GENERIC` steps (tool output) and
  Codex/Grok reasoning are omitted.
- The reply that runs the export is not in the transcript yet, so it is not exported.
- Store formats are internal and change between releases. Unknown lines are skipped, not fatal.

## Safety

- The export contains everything pasted into the chat, including any secrets. Do not write it
  into a tracked path without telling the user. Do not commit it, and do not send it to an
  external service without explicit approval.
- The script refuses to write inside a harness store directory.

Resolve helper paths from this skill directory. Run project commands from the target workspace.
