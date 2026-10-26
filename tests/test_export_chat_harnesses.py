"""export-chat per-harness discovery/rendering and the export-chat -> resume-task (harvest --md) round trip.

Synthetic stores only; these tests never read real session stores.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPORT_CHAT = ROOT / ".claude" / "skills" / "export-chat" / "scripts" / "export_chat.py"
HARVEST = ROOT / ".claude" / "skills" / "resume-task" / "scripts" / "harvest.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


ec = _load("export_chat_multi", EXPORT_CHAT)
harvest = _load("harvest_multi", HARVEST)


def _jsonl(path: Path, rows: list[dict], mtime: float | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    if mtime:
        os.utime(path, (mtime, mtime))
    return path


@pytest.fixture()
def stores(tmp_path):
    ws = tmp_path / "Projects" / "my-app"
    ws.mkdir(parents=True)
    other = tmp_path / "Projects" / "other"
    other.mkdir()
    homes = {k: tmp_path / k for k in ("cursor", "claude", "codex", "gemini", "grok")}

    # Claude Code: projects/<encoded cwd>/<session>.jsonl
    _jsonl(homes["claude"] / "projects" / ec.claude_slug(ws) / "sess-claude.jsonl", [
        {"type": "user", "sessionId": "sess-claude", "cwd": str(ws),
         "message": {"content": "<system-reminder>x</system-reminder>Fix the parser"}},
        {"type": "assistant", "sessionId": "sess-claude",
         "message": {"content": [{"type": "text", "text": "Editing."},
                                 {"type": "tool_use", "name": "Edit", "input": {"file_path": str(ws / "p.py")}}]}},
        {"type": "user", "sessionId": "sess-claude", "isMeta": True, "message": {"content": "meta"}},
    ], 3_000)

    # Codex: sessions/Y/M/D/rollout-*.jsonl, cwd in session_meta
    _jsonl(homes["codex"] / "sessions" / "2026" / "10" / "24" / "rollout-2026-10-24T01-00-00-cdx1.jsonl", [
        {"type": "session_meta", "payload": {"id": "cdx1", "cwd": str(ws)}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
                                              "content": [{"type": "input_text", "text": "<environment_context>e</environment_context>"}]}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
                                              "content": [{"type": "input_text", "text": "Add a test"}]}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "shell",
                                              "arguments": json.dumps({"command": ["pytest", "-q"]})}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant",
                                              "content": [{"type": "output_text", "text": "Done."}]}},
    ], 2_000)
    _jsonl(homes["codex"] / "sessions" / "2026" / "10" / "24" / "rollout-2026-10-24T02-00-00-cdx2.jsonl", [
        {"type": "session_meta", "payload": {"id": "cdx2", "cwd": str(other)}},
    ], 9_000)

    # Antigravity CLI: brain/<id>/.system_generated/logs/transcript_full.jsonl, no cwd field
    def ag(conv, path_arg, mtime):
        return _jsonl(homes["gemini"] / "antigravity-cli" / "brain" / conv / ".system_generated" / "logs"
                      / "transcript_full.jsonl", [
            {"step_index": 0, "source": "USER_EXPLICIT", "type": "USER_INPUT", "created_at": "2026-10-24T03:00:00Z",
             "content": "<USER_REQUEST>\nRename the module\n</USER_REQUEST>\n<ADDITIONAL_METADATA>t</ADDITIONAL_METADATA>"},
            {"step_index": 1, "source": "MODEL", "type": "PLANNER_RESPONSE", "content": "Renaming.",
             "tool_calls": [{"name": "write_file", "args": {"Path": path_arg, "Content": "x"}}]},
            {"step_index": 2, "source": "MODEL", "type": "GENERIC", "content": "Command output: noise"},
        ], mtime)
    ag("ag-mine", str(ws / "mod.py"), 4_000)
    ag("ag-other", str(other / "x.py"), 8_000)

    # Grok: sessions/<url-encoded cwd>/<id>/updates.jsonl
    gdir = homes["grok"] / "sessions" / quote(str(ws), safe="") / "grk1"
    _jsonl(gdir / "updates.jsonl", [
        {"method": "session/update", "params": {"update": {"sessionUpdate": "user_message_chunk",
                                                           "content": {"type": "text", "text": "Ship "}}}},
        {"method": "session/update", "params": {"update": {"sessionUpdate": "user_message_chunk",
                                                           "content": {"type": "text", "text": "the docs"}}}},
        {"method": "session/update", "params": {"update": {"sessionUpdate": "agent_message_chunk",
                                                           "content": {"type": "text", "text": "Writing docs."}}}},
        {"method": "session/update", "params": {"update": {
            "sessionUpdate": "tool_call", "rawInput": {"target_file": str(ws / "README.md")},
            "_meta": {"x.ai/tool": {"name": "write", "kind": "edit", "read_only": False}}}}},
        {"method": "_x.ai/session/update", "params": {"update": {"sessionUpdate": "turn_completed", "stop_reason": "end_turn"}}},
    ], 5_000)
    (gdir / "summary.json").write_text(json.dumps({"generated_title": "Ship docs", "info": {"cwd": str(ws)}}))

    # Cursor: projects/<slug>/agent-transcripts/<id>/<id>.jsonl
    _jsonl(homes["cursor"] / "projects" / ec.workspace_slug(ws) / "agent-transcripts" / "cur1" / "cur1.jsonl", [
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>\nTidy imports\n</user_query>"}]}},
        {"role": "assistant", "message": {"content": [{"type": "tool_use", "name": "StrReplace", "input": {"path": "a.py"}}]}},
        {"type": "turn_ended", "status": "success"},
    ], 1_000)
    return ws, other, homes


@pytest.mark.parametrize("harness, sid, user_text, tool", [
    ("claude", "sess-claude", "Fix the parser", "**Tool: Edit**"),
    ("codex", "cdx1", "Add a test", "**Tool: shell**"),
    ("antigravity", "ag-mine", "Rename the module", "**Tool: write_file**"),
    ("grok", "grk1", "Ship the docs", "**Tool: write**"),
    ("cursor", "cur1", "Tidy imports", "**Tool: StrReplace**"),
])
def test_each_harness_exports_its_workspace_chat(stores, harness, sid, user_text, tool, monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    ws, _, homes = stores
    sources = ec.discover(harness, ws, homes, explicit=True)
    assert sources and sources[0].id == sid, [s.id for s in sources]
    src = sources[0]
    md, stats = ec.render_markdown(ec.load_events(src.path), transcript_id=src.id, workspace=str(ws),
                                   harness=src.harness, store=src.store)
    assert md.startswith("# Chat export\n")
    assert f"- Harness: {harness}" in md
    assert f"## User\n\n{user_text}" in md
    assert tool in md
    assert stats["user_messages"] == 1 and stats["tool_calls"] == 1
    for noise in ("<system-reminder>", "environment_context", "ADDITIONAL_METADATA", "Command output: noise", "meta"):
        assert noise not in md.split("## User", 1)[1]


def test_workspace_filter_excludes_other_projects(stores):
    ws, other, homes = stores
    assert [s.id for s in ec.discover("codex", ws, homes)] == ["cdx1"]
    assert [s.id for s in ec.discover("antigravity", ws, homes)] == ["ag-mine"]
    # Newer chats from another workspace are never picked for this workspace.
    assert ec.discover("antigravity", ws, homes)[0].workspace_verified


def test_auto_mode_refuses_to_guess_between_harnesses(stores, tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDECODE", raising=False)
    ws, _, homes = stores
    args = [str(tmp_path / "out.md"), "--workspace", str(ws), "--json"]
    for name, home in homes.items():
        args += [f"--{name}-home", str(home)]
    assert ec.main(args) == 1
    assert ec.main(args + ["--harness", "grok"]) == 0
    assert "- Resume: `grok --resume grk1`" in (tmp_path / "out.md").read_text(encoding="utf-8")


def test_refuses_to_write_into_a_harness_store(stores, monkeypatch):
    ws, _, homes = stores
    target = homes["claude"] / "export.md"
    args = [str(target), "--harness", "claude", "--workspace", str(ws)]
    for name, home in homes.items():
        args += [f"--{name}-home", str(home)]
    assert ec.main(args) == 1
    assert not target.exists()


@pytest.mark.parametrize("harness, tool, resume", [
    ("codex", "codex (export)", "codex resume"),
    ("claude", "claude (export)", "claude --resume"),
    ("antigravity", "antigravity (export)", "agy --conversation"),
    ("cursor", "cursor (export)", None),
])
def test_resume_task_understands_export_chat_output(stores, tmp_path, harness, tool, resume, monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    ws, _, homes = stores
    src = ec.discover(harness, ws, homes, explicit=True)[0]
    md, _ = ec.render_markdown(ec.load_events(src.path), transcript_id=src.id, workspace=str(ws),
                               harness=src.harness, store=src.store)
    export = tmp_path / "exports" / "2026-10-24-101500-chat.md"
    export.parent.mkdir()
    export.write_text(md, encoding="utf-8")

    s = harvest.parse_md(export, None)
    assert s.tool == tool
    assert s.sid == src.id
    assert s.project == str(ws)
    assert [t.role for t in s.turns][:1] == ["user"]
    assert all("**Tool" not in t.text and '"Content"' not in t.text for t in s.turns)
    cmd = harvest.resume_cmd(s)
    if resume:
        assert resume in cmd and src.id in cmd
    else:
        assert cmd is None


def test_resume_task_records_files_from_exported_edit_tools(stores, tmp_path):
    ws, _, homes = stores
    src = ec.discover("claude", ws, homes)[0]
    md, _ = ec.render_markdown(ec.load_events(src.path), transcript_id=src.id, workspace=str(ws), harness="claude")
    export = tmp_path / "e.md"
    export.write_text(md, encoding="utf-8")
    assert harvest.parse_md(export, None).files == [str(ws / "p.py")]


def test_legacy_export_without_harness_line_is_attributed(tmp_path):
    legacy = tmp_path / "old.md"
    legacy.write_text("# Chat export\n\n- Transcript: `abc`\n- Workspace: `D:\\Projects\\x`\n"
                      "- Exported: 2026-10-01T10:00:00+00:00\n\n## User\n\nhello\n\n## Assistant\n\nhi\n", encoding="utf-8")
    s = harvest.parse_md(legacy, None)
    assert s.tool == "cursor (export)" and s.sid == "abc" and s.project == "D:\\Projects\\x"


def test_fenced_role_markers_do_not_split_turns():
    md = "## User\n\nrun it\n\n## Assistant\n\n```\n## User\nnot a turn\n```\nok\n"
    assert [t.role for t in harvest.split_md_turns(md)] == ["user", "assistant"]


def test_harvest_reads_grok_and_structured_antigravity(stores, monkeypatch):
    ws, _, homes = stores
    since = harvest.datetime.fromtimestamp(0, harvest.UTC)
    monkeypatch.setattr(harvest.Path, "home", staticmethod(lambda: homes["grok"].parent / "no-profile"))
    monkeypatch.setenv("GROK_HOME", str(homes["grok"]))
    grok = harvest.parse_grok(since)
    assert len(grok) == 1 and grok[0].title == "Ship docs" and grok[0].project == str(ws)
    assert [t.text for t in grok[0].turns] == ["Ship the docs", "Writing docs."]
    assert grok[0].files == [str(ws / "README.md")]
    assert harvest.resume_cmd(grok[0]).endswith("grok --resume " + ("'grk1'" if os.name == "nt" else "grk1"))

    s = harvest.Session(tool="antigravity-cli", sid="ag", path="x")
    hints: list[str] = []
    for row in ec.load_events(homes["gemini"] / "antigravity-cli" / "brain" / "ag-mine" / ".system_generated"
                              / "logs" / "transcript_full.jsonl"):
        harvest.parse_antigravity_step(s, row, hints)
    assert [(t.role, t.text) for t in s.turns] == [("user", "Rename the module"), ("assistant", "Renaming.")]
    assert s.files == [str(ws / "mod.py")]


def test_export_chat_cli_subprocess_claude(stores, tmp_path):
    ws, _, homes = stores
    out = tmp_path / "c.md"
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID")}
    proc = subprocess.run([sys.executable, str(EXPORT_CHAT), str(out), "--harness", "claude", "--workspace", str(ws),
                           "--claude-home", str(homes["claude"]), "--json"],
                          capture_output=True, text=True, env=env, check=False)
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["harness"] == "claude" and result["tool_calls"] == 1
