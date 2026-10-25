"""scripts.harness_logs on synthetic stores; never reads real harness data."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.harness_logs import catalog, events, report, settings  # noqa: E402
from scripts.harness_logs.common import Homes, redact  # noqa: E402

EPOCH = datetime.fromtimestamp(0, timezone.utc)


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


@pytest.fixture()
def homes(tmp_path) -> Homes:
    h = Homes(claude=tmp_path / "claude", codex=tmp_path / "codex", cursor=tmp_path / "cursor",
              cursor_user=tmp_path / "cursor-user", gemini=tmp_path / "gemini", grok=tmp_path / "grok")
    ws = "D:\\Projects\\app"

    def tu(i, cmd, name="Bash"):
        return {"type": "assistant", "sessionId": "s1", "cwd": ws, "timestamp": "2026-10-24T01:00:00Z",
                "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": name, "input": {"command": cmd}}]}}

    def tr(i, text, err=True):
        return {"type": "user", "sessionId": "s1", "permissionMode": "auto",
                "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "is_error": err, "content": text}]}}

    _jsonl(h.claude / "projects" / "D--Projects-app" / "s1.jsonl", [
        {"type": "user", "sessionId": "s1", "permissionMode": "auto", "message": {"content": "go"}},
        tu(1, "git status"), tr(1, "On branch main", err=False),
        tu(2, "gh pr merge 5"), tr(2, "Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Merge Without Review]. If"),
        tu(3, "cat .env"), tr(3, "PreToolUse:Bash hook error: jev-engineering: sensitive_path_or_secret"),
        tu(4, "rm -rf build"), tr(4, "The user doesn't want to proceed with this tool use. The tool use was rejected"),
        tu(5, "curl x"), tr(5, "Permission to use Bash with command curl x has been denied."),
    ])
    # a resumed session re-logs t1: it must not be counted twice
    resumed = h.claude / "projects" / "D--Projects-app" / "s1-resumed.jsonl"
    _jsonl(resumed, [tu(1, "git status"), tr(1, "ok", err=False)])
    later = (h.claude / "projects" / "D--Projects-app" / "s1.jsonl").stat().st_mtime + 60
    import os
    os.utime(resumed, (later, later))

    _jsonl(h.codex / "sessions" / "2026" / "10" / "24" / "rollout-x-c1.jsonl", [
        {"type": "session_meta", "payload": {"id": "c1", "cwd": ws}},
        {"type": "turn_context", "payload": {"cwd": ws, "approval_policy": "on-request", "approvals_reviewer": "auto_review"}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "exec_command", "call_id": "a",
                                              "arguments": json.dumps({"cmd": "docker exec db psql", "sandbox_permissions": "require_escalated",
                                                                       "justification": "read the DB"})}},
        {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "a", "output": "ok"}},
        {"type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec", "call_id": "b",
                                              "input": 'text(await tools.exec_command({cmd:"git push origin main", sandbox_permissions:"require_escalated"}))'}},
        {"type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": "b",
                                              "output": 'failed: Rejected("Automatic approval review failed: risky")'}},
        {"type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec", "call_id": "c", "input": "const x = 1; text(x)"}},
    ])
    (h.codex / "rules").mkdir(parents=True)
    (h.codex / "rules" / "default.rules").write_text(
        'prefix_rule(pattern=["git", "push"], decision="allow")\nprefix_rule(pattern=["rg", "-n"], decision="allow")\n')
    (h.codex / "config.toml").write_text(
        'approval_policy = "on-request"\nsandbox_mode = "workspace-write"\n'
        '[projects.\'d:\\projects\\app\']\ntrust_level = "trusted"\n'
        '[apps.conn.tools."github.merge_pull_request"]\napproval_mode = "approve"\n')

    _jsonl(h.cursor / "projects" / "D-Projects-app" / "agent-transcripts" / "u1" / "u1.jsonl", [
        {"role": "assistant", "message": {"content": [{"type": "tool_use", "name": "Shell", "input": {"command": "npm test"}}]}},
    ])
    (h.cursor / "cli-config.json").write_text(json.dumps({"approvalMode": "unrestricted", "sandbox": {"mode": "disabled"},
                                                          "permissions": {"allow": ["Shell(python)", "Shell(git status)"], "deny": []}}))

    _jsonl(h.gemini / "antigravity-cli" / "brain" / "g1" / ".system_generated" / "logs" / "transcript_full.jsonl", [
        {"step_index": 1, "source": "MODEL", "type": "PLANNER_RESPONSE", "created_at": "2026-10-24T02:00:00Z",
         "tool_calls": [{"name": "run_command", "args": {"CommandLine": "git push", "BypassSandbox": True}},
                        {"name": "run_command", "args": {"CommandLine": "git status"}}]},
        {"step_index": 2, "source": "MODEL", "type": "GENERIC", "status": "DONE", "content": "pushed"},
        {"step_index": 3, "source": "MODEL", "type": "GENERIC", "status": "ERROR", "content": "permission denied by rule"},
    ])
    (h.gemini / "antigravity-cli" / "settings.json").write_text(json.dumps({
        "agentMode": "accept-edits", "allowNonWorkspaceAccess": True, "trustedWorkspaces": ["C:\\Users\\me"],
        "permissions": {"allow": ["command(python:*)", "command(git status)"], "ask": ["command(git push)"], "deny": ["command(sudo)"]}}))

    gdir = h.grok / "sessions" / quote(ws, safe="") / "k1"
    _jsonl(gdir / "events.jsonl", [{"type": "turn_started", "yolo_mode": True}])
    _jsonl(gdir / "updates.jsonl", [
        {"timestamp": 1792357068, "method": "session/update", "params": {"update": {
            "sessionUpdate": "tool_call", "rawInput": {"command": "cargo test"},
            "_meta": {"x.ai/tool": {"name": "run_terminal_command", "read_only": False}}}}},
    ])
    (h.grok / "config.toml").write_text('[ui]\npermission_mode = "always-approve"\n[permission]\ndeny = ["Bash(rm -rf *)"]\n')
    return h


def test_events_outcomes_per_harness(homes):
    evs = list(events.iter_events(homes, EPOCH))
    by = {(e.harness, e.command.split("\n")[0]): e for e in evs}
    assert by[("claude", "git status")].outcome == "allowed"
    assert sum(1 for e in evs if e.harness == "claude" and e.command == "git status") == 1
    assert by[("claude", "gh pr merge 5")].outcome == "auto_denied"
    assert by[("claude", "gh pr merge 5")].detail == "Merge Without Review"
    assert by[("claude", "cat .env")].outcome == "hook_blocked"
    assert by[("claude", "rm -rf build")].outcome == "user_rejected"
    assert by[("claude", "curl x")].outcome == "rule_denied"
    assert by[("claude", "git status")].mode == "auto"
    assert by[("codex", "docker exec db psql")].outcome == "escalation_requested"
    assert by[("codex", "docker exec db psql")].mode == "on-request/auto_review"
    assert by[("codex", "git push origin main")].outcome == "auto_denied"
    assert any(e.tool == "exec(js)" for e in evs if e.harness == "codex")
    assert by[("cursor", "npm test")].outcome == "unknown"
    assert by[("antigravity", "git push")].outcome == "escalation_requested"
    assert by[("antigravity", "git status")].outcome == "rule_denied"
    assert by[("grok", "cargo test")].outcome == "auto_allowed"


def test_settings_inventory(homes, tmp_path):
    proj = tmp_path / "projects" / "app"
    (proj / ".claude").mkdir(parents=True)
    (proj / ".claude" / "settings.local.json").write_text(json.dumps({"permissions": {"allow": ["Bash(python *)", "Bash(git push:*)"]}}))
    rules = settings.all_rules(homes, tmp_path / "projects")
    got = {(r.harness, r.scope, r.action, r.rule) for r in rules}
    assert ("codex", "global", "allow", "prefix:git push") in got
    assert ("codex", "global", "allow", "app:github.merge_pull_request approval_mode=approve") in got
    assert ("codex", "global", "trust", "d:\\projects\\app: trusted") in got
    assert ("cursor", "global", "mode", "approvalMode=unrestricted") in got
    assert ("antigravity", "global", "ask", "command(git push)") in got
    assert ("antigravity", "global", "trust", "trustedWorkspace=C:\\Users\\me") in got
    assert ("grok", "global", "mode", "permission_mode=always-approve") in got
    assert ("claude", "project", "allow", "Bash(python *)") in got
    flags = {r.rule: report.risk_flag(r) for r in rules}
    assert flags["Bash(python *)"] == "interpreter wildcard"
    assert flags["command(python:*)"] == "interpreter wildcard"
    assert flags["approvalMode=unrestricted"] == "unrestricted mode"
    assert flags["permission_mode=always-approve"] == "unrestricted mode"
    assert flags["app:github.merge_pull_request approval_mode=approve"] == "remote write"
    assert flags["Shell(git status)"] is None


@pytest.mark.parametrize("command, expected", [
    ("cd D:/x && git -C y status -s | head -5", ["git status", "head"]),
    ("MSYS_NO_PATHCONV=1 timeout 60 python -m pytest -q", ["python -m pytest"]),
    ("python - <<'EOF'\nimport os\nprint(1 && 2)\nEOF\necho done", ["python - (inline)", "echo"]),
    ("$env:PYTHONIOENCODING='utf-8'; uv run python scripts/x.py", ["uv run python"]),
    ("& 'C:\\Py\\python.exe' -X utf8 tool.py --flag", ["python <script>"]),
    ("gh pr view 12 --json state; docker exec gpu sh -c 'ls'", ["gh pr view", "docker exec gpu"]),
    ("Get-ChildItem -Recurse | Select-Object -First 3", ["Get-ChildItem", "Select-Object"]),
    ("for f in a b; do cat \"$f\"; done", ["for", "cat"]),
])
def test_catalog_heads(command, expected):
    assert catalog.heads(command) == expected


def test_catalog_and_report_render(homes, tmp_path):
    evs = list(events.iter_events(homes, EPOCH))
    cat = catalog.build_catalog(evs)
    heads = {(r["harness"], r["head"]) for r in cat}
    assert ("claude", "git status") in heads and ("codex", "tool:exec(js)") in heads
    md = report.build_report(evs, settings.all_rules(homes, None), cat, since=EPOCH,
                             generated=datetime(2026, 10, 24, tzinfo=timezone.utc), projects_root=None)
    for section in ("## 1. Tool calls by outcome", "## 2. Asked and refused", "## 4. Persisted grants",
                    "## 5. Settings review", "## 7. Most frequent command heads"):
        assert section in md
    assert "Merge Without Review" in md


def test_redaction_keeps_labels():
    text = redact("token=abcdef123456 Bearer abcdefghijklmnop sk-" + "a" * 24)
    assert "abcdef123456" not in text and "token=[REDACTED]" in text and "Bearer [REDACTED]" in text
    assert "sk-aaaa" not in text
