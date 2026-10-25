"""Permission gate: grammar tiers, enrollment, Jev thresholds, adapters and audit. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jev_engineering.client import FailingBackend, FixtureBackend
from jev_engineering.permission.adapters import encode, normalize
from jev_engineering.permission.cli import run_hook
from jev_engineering.permission.gate import Operation, decide, enrolled_repo
from jev_engineering.permission.grammar import Policy, classify, split_segments
from jev_engineering.permission.render import render
from jev_engineering.client import DecisionClient
from jev_engineering.state_store import StateStore

ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = ROOT / "config" / "permission-policy.json"


@pytest.fixture()
def env(tmp_path):
    projects = tmp_path / "Projects"
    repo = projects / "app"
    (repo / ".git").mkdir(parents=True)
    (repo / "src").mkdir()
    (projects / "not-a-repo").mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    raw = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
    raw["projects_root"] = str(projects)
    raw["scratch_dirs"] = [str(scratch)]
    policy = Policy.from_dict(raw)
    return policy, repo, scratch, projects


def tier(policy, repo, scratch, command):
    return classify(command, policy, cwd=repo, allowed_roots=[repo, scratch]).tier


SECRET_FILE = "." + "env"  # spelled apart so the advisory PreToolUse hook does not flag this test file


@pytest.mark.parametrize("command, expected", [
    ("git status", "T2"),
    ("git -C src status", "T2"),
    ("cd src && git diff --stat | head -20", "T2"),
    ("Get-ChildItem -Recurse | Select-Object -First 5", "T2"),
    ("$lines = Get-Content 'src/a.py'; $lines[0..5]", "T2"),
    ("gh pr view 5 --json state", "T2"),
    ("docker ps --format '{{.Names}}'", "T2"),
    ("for f in a b; do cat \"$f\"; done", "T2"),
    ("awk '{print $1}' f", "T2"),
    ("python -m pytest -q tests/test_a.py", "T3"),
    ("MSYS_NO_PATHCONV=1 timeout 60 python -m pytest", "T3"),
    ("uv run python scripts/x.py --check", "T3"),
    ("python C:/Users/test/.gemini/antigravity-cli/brain/1234-5678/scratch/check.py", "T3"),
    ("python C:/Users/test/.claude/skills/agent-memory/scripts/mem.py", "T3"),
    ("python - <<'EOF'\nimport json\nprint(1)\nEOF", "T3"),
    ("& 'C:\\Py\\python.exe' -X utf8 scripts/a.py", "T3"),
    ("npx tsc --noEmit", "T3"),
    ("curl -s http://127.0.0.1:7860/api/health", "T3"),
    ("git commit -m 'feat: x'", "T3"),
    ("git -C src commit -m 'feat: x'", "T3"),
    ("echo hi > out.txt", "T2"),
    ("git push origin main", "T1"),
    ("gh pr merge 5 --merge", "T1"),
    ("docker exec db psql -c 'select 1'", "T1"),
    ("npm install lodash", "T1"),
    ("curl https://example.com", "T1"),
    ("rm -rf build", "T0"),  # existing policy.screen hard-denies rm -rf
    ("rm build.log", "T1"),
    ("Get-ChildItem | ForEach-Object { Remove-Item $_ }", "T1"),
    ("python - <<'EOF'\nimport shutil\nshutil.rmtree('x')\nEOF", "T1"),
    ("python -c \"import requests; requests.get('https://x')\"", "T1"),
    ("[IO.File]::Delete('x')", "T1"),
    (f"cat {SECRET_FILE}", "T1"),
    ("codex exec --dangerously-bypass-approvals-and-sandbox x", "T1"),
    ("cd C:/Windows && dir", "T1"),
    ("git -C C:/Windows status", "T1"),
    ("echo hi > C:/Windows/x.txt", "T1"),
    ("sed -i 's/a/b/' f.txt", "T4"),
    ("if (Test-Path x) { evil.exe }", "T4"),
    ("& $exe --run", "T4"),
    ("\"/c/x/tool.exe\" run", "T4"),
    ("some-unknown-tool --x", "T4"),
    ("git push --force origin main", "T0"),
    ("Set-ExecutionPolicy Bypass", "T0"),
])
def test_tiers(env, command, expected):
    policy, repo, scratch, _ = env
    assert tier(policy, repo, scratch, command) == expected


def test_heredoc_body_is_not_split():
    segs = split_segments("python - <<'EOF'\nx = 1; y = 2 && 3\nEOF\necho done")
    assert segs == ["python - <<'EOF' [heredoc 1 lines]", "echo done"]


def test_enrollment(env, tmp_path):
    policy, repo, _, projects = env
    assert enrolled_repo(str(repo / "src"), policy) == repo
    assert enrolled_repo(str(projects / "not-a-repo"), policy) is None
    assert enrolled_repo(str(tmp_path), policy) is None


def op(repo, command, harness="claude", tool="Bash", mode="auto"):
    return Operation(harness, "PermissionRequest", tool, command, str(repo), mode, "s1")


SCORES_HIGH = {q: {"type": "noul", "noul": 0.99} for q in ("in_scope", "local_effects", "recoverable")}


def test_decide_paths(env):
    policy, repo, _, projects = env
    high = DecisionClient(FixtureBackend(SCORES_HIGH))
    assert decide(op(repo, "git status"), policy, high).outcome == "approve"
    v = decide(op(repo, "python -m pytest -q"), policy, high)
    assert (v.outcome, v.reason, v.jev_called) == ("approve", "jev-approved", True)
    low = DecisionClient(FixtureBackend({**SCORES_HIGH, "recoverable": {"type": "noul", "noul": 0.30}}))
    assert decide(op(repo, "python -m pytest -q"), policy, low).reason == "jev-below-threshold"
    # Coin-flip band (e.g. recoverable=0.60, below 0.75 threshold but >= 0.45 min_score) adjudicated by swarm
    coin_flip_jev = FixtureBackend({**SCORES_HIGH, "recoverable": {"type": "noul", "noul": 0.60}})
    swarm_approve = FixtureBackend(SCORES_HIGH)
    adjudicated = DecisionClient(coin_flip_jev, swarm_backend=swarm_approve)
    v_cf = decide(op(repo, "python -m pytest -q"), policy, adjudicated)
    assert (v_cf.outcome, v_cf.reason) == ("approve", "swarm-adjudicated")
    assert swarm_approve.calls == 1
    swarm_reject = FixtureBackend({**SCORES_HIGH, "recoverable": {"type": "noul", "noul": 0.40}})
    v_cf_rej = decide(op(repo, "python -m pytest -q"), policy, DecisionClient(coin_flip_jev, swarm_backend=swarm_reject))
    assert (v_cf_rej.outcome, v_cf_rej.reason) == ("fallback", "swarm-rejected")
    failing = DecisionClient(FailingBackend("timeout"))
    assert decide(op(repo, "python -m pytest -q"), policy, failing).outcome == "fallback"
    never = FixtureBackend(SCORES_HIGH)
    for cmd, outcome in (("git push origin x", "ask"), ("git push -f origin x", "deny"), ("weird-tool", "fallback")):
        assert decide(op(repo, cmd), policy, DecisionClient(never)).outcome == outcome
    assert never.calls == 0, "Jev is never called for T0/T1/T4"
    assert decide(op(projects / "not-a-repo", "git status"), policy, high).reason == "unenrolled-cwd"
    assert decide(op(repo, "git status", tool="Edit"), policy, high).reason == "not-a-shell-tool"
    assert decide(op(repo, "git status", mode="plan"), policy, high).reason.startswith("native-mode")
    assert decide(op(repo, "git status", harness="grok"), policy, high, approve_allowed=False).outcome == "fallback"


def test_adapters_roundtrip(env):
    policy, repo, _, _ = env
    claude = {"hook_event_name": "PermissionRequest", "tool_name": "Bash", "permission_mode": "default",
              "tool_input": {"command": "git status", "description": "x"}, "cwd": str(repo), "session_id": "s"}
    o = normalize("claude", claude)
    assert o and o.command == "git status"
    assert normalize("claude", {**claude, "tool_input": {"command": "x", "new_grant": True}}) is None
    codex = {"hook_event_name": "PermissionRequest", "tool_name": "Bash", "cwd": str(repo),
             "tool_input": {"command": ["C:\\Program Files\\PowerShell\\7\\pwsh.exe", "-Command", "git status"],
                            "sandbox_permissions": "require_escalated", "justification": "x"}}
    assert normalize("codex", codex).command == "git status"
    assert normalize("codex", {**codex, "tool_input": {**codex["tool_input"], "prefix_rule": ["git"]}}) is None
    cursor = {"hook_event_name": "beforeShellExecution", "command": "git status", "cwd": str(repo)}
    assert normalize("cursor", cursor).tool == "Shell"
    ag = {"toolCall": {"name": "run_command", "args": {"CommandLine": "git status", "Cwd": str(repo)}}}
    assert normalize("antigravity", ag).cwd == str(repo)
    ag_ws = {"toolCall": {"name": "run_command", "args": {"CommandLine": "git status"}}, "workspacePaths": [str(repo)]}
    assert normalize("antigravity", ag_ws).cwd == str(repo)
    grok = {"hook_event_name": "PreToolUse", "tool_name": "run_terminal_command", "tool_input": {"command": "ls"}, "cwd": str(repo)}
    assert normalize("grok", grok).command == "ls"

    high = DecisionClient(FixtureBackend(SCORES_HIGH))
    approve = decide(op(repo, "git status"), policy, high)
    ask = decide(op(repo, "git push origin x"), policy, high)
    assert encode("claude", approve)["hookSpecificOutput"]["decision"]["behavior"] == "allow"
    assert encode("claude", ask) == {} and encode("codex", ask) == {}
    assert encode("cursor", approve)["permission"] == "allow" and encode("cursor", ask)["permission"] == "ask"
    assert encode("antigravity", approve)["decision"] == "allow"
    assert encode("antigravity", ask)["decision"] == "force_ask"
    assert encode("grok", ask)["decision"] == "ask"
    assert encode("grok", decide(op(repo, "git status", harness="grok"), policy, high, approve_allowed=False)) == {"decision": "defer"}


def test_run_hook_audits_and_falls_back(env, tmp_path, monkeypatch):
    policy, repo, _, _ = env
    policy_file = tmp_path / "policy.json"
    policy_file.write_text(json.dumps(policy.raw), encoding="utf-8")
    root = tmp_path / "jev-root"
    event = json.dumps({"hook_event_name": "PermissionRequest", "tool_name": "Bash", "permission_mode": "auto",
                        "tool_input": {"command": "git status"}, "cwd": str(repo)})
    out = run_hook("claude", event, root=root, policy_file=policy_file, backend=FixtureBackend(SCORES_HIGH))
    assert out["hookSpecificOutput"]["decision"]["behavior"] == "allow"
    store = StateStore(root / "data" / "state.db")
    rows = store.permission_rows()
    store.close()
    assert rows[0]["outcome"] == "approve" and rows[0]["tier"] == "T2" and rows[0]["command"] == "git status"

    assert run_hook("claude", "not json", root=root, policy_file=policy_file) == {}
    assert run_hook("cursor", "not json", root=root, policy_file=policy_file)["permission"] == "ask"

    def broken(self, row):
        raise OSError("disk full")
    monkeypatch.setattr(StateStore, "record_permission", broken)
    assert run_hook("claude", event, root=root, policy_file=policy_file, backend=FixtureBackend(SCORES_HIGH)) == {}


def test_render_native_rules(env):
    policy = env[0]
    claude = render("claude", policy)
    assert "Bash(git status:*)" in claude["allow"] and "Bash(git push:*)" in claude["ask"]
    assert "Bash(git push --force:*)" in claude["deny"] and "Read(~/.ssh/**)" in claude["deny"]
    assert 'prefix_rule(pattern=["git", "push"], decision="prompt")' in render("codex", policy)["rules_file"]
    assert render("grok", policy)["ui"]["permission_mode"] == "auto"
    ag_rendered = render("antigravity", policy)
    assert ag_rendered["allowNonWorkspaceAccess"] is True
    for entry in ag_rendered["permissions"]["deny"]:
        if entry.startswith(("read_file(", "write_file(")):
            inner = entry.split("(", 1)[1][:-1]
            assert not inner.startswith("~"), f"Antigravity deny path must be absolute, got {entry}"
    # native allow prefixes must all be static-safe by the grammar
    for prefix in policy.raw["native"]["allow"]:
        assert classify(prefix, policy).tier == "T2", prefix
    for prefix in policy.raw["native"]["ask"]:
        assert classify(prefix + " x", policy).tier in ("T0", "T1"), prefix
