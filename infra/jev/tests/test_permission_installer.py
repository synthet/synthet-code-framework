"""Tests for permission installer: plan, apply, rollback, and safety boundaries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jev_engineering.permission.grammar import Policy
from jev_engineering.permission.installer import apply_all, plan_all, rollback_permissions

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def mock_env(tmp_path: Path):
    home = tmp_path / "home"
    projects = tmp_path / "Projects"
    home.mkdir()
    projects.mkdir()

    # Claude home (with pre-existing notification hook on PermissionRequest to test ordering)
    claude_dir = home / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text(json.dumps({
        "permissions": {"defaultMode": "auto"},
        "hooks": {
            "PermissionRequest": [
                {"hooks": [{"type": "command", "command": "powershell.exe -Command notify"}]}
            ]
        },
    }, indent=2), encoding="utf-8")

    # Codex home
    codex_dir = home / ".codex"
    codex_dir.mkdir()
    (codex_dir / "rules").mkdir()
    (codex_dir / "config.toml").write_text('approval_policy = "on-request"\nsandbox_mode = "workspace-write"\n', encoding="utf-8")
    (codex_dir / "rules" / "default.rules").write_text('prefix_rule(pattern=["rm", "-rf"], decision="allow")\n', encoding="utf-8")

    # Cursor home
    cursor_dir = home / ".cursor"
    cursor_dir.mkdir()
    (cursor_dir / "cli-config.json").write_text(json.dumps({"approvalMode": "unrestricted", "permissions": {"allow": ["Shell(git push)"]}}, indent=2), encoding="utf-8")

    # Antigravity home
    gemini_cli = home / ".gemini" / "antigravity-cli"
    gemini_cli.mkdir(parents=True)
    (gemini_cli / "settings.json").write_text(json.dumps({"agentMode": "accept-edits", "permissions": {"allow": ["command(python:*)"]}}, indent=2), encoding="utf-8")

    gemini_cfg = home / ".gemini" / "config"
    gemini_cfg.mkdir(parents=True)
    (gemini_cfg / "config.json").write_text(json.dumps({"userSettings": {"globalPermissionGrants": {"allow": ["command(npm install)"]}}}, indent=2), encoding="utf-8")

    # Grok home
    grok_dir = home / ".grok"
    grok_dir.mkdir()
    (grok_dir / "config.toml").write_text('[ui]\npermission_mode = "always-approve"\n', encoding="utf-8")

    # Project repo
    repo = projects / "test-repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "settings.local.json").write_text(json.dumps({"permissions": {"allow": ["Bash(cat AppData/Temp/foo)", "Bash(git status)"]}}, indent=2), encoding="utf-8")
    (repo / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"allow": ["Bash(gh pr merge 5)", "Bash(git diff)"]}}, indent=2), encoding="utf-8")

    policy = Policy.load(ROOT / "config" / "permission-policy.json")
    return home, projects, policy, tmp_path / "agent_root"


def test_plan_does_not_modify_disk(mock_env):
    home, projects, policy, _ = mock_env
    claude_before = (home / ".claude" / "settings.json").read_text(encoding="utf-8")
    report = plan_all(home=home, projects_root=projects, policy=policy)
    claude_after = (home / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert claude_before == claude_after
    assert len(report.modified) > 0


def test_apply_and_rollback(mock_env):
    home, projects, policy, root = mock_env
    root.mkdir(parents=True)
    claude_file = home / ".claude" / "settings.json"
    claude_orig = claude_file.read_text(encoding="utf-8")

    receipt = apply_all(home=home, projects_root=projects, policy=policy, root=root)
    assert len(receipt["applied"]) > 0

    # Verify changes applied
    claude_updated = json.loads(claude_file.read_text(encoding="utf-8"))
    assert "Bash(git status:*)" in claude_updated["permissions"]["allow"]
    assert any("PermissionRequest" in k for k in claude_updated["hooks"])
    first_pr_hook = claude_updated["hooks"]["PermissionRequest"][0]
    assert first_pr_hook.get("matcher") == "Bash|PowerShell"
    assert first_pr_hook["hooks"][0]["timeout"] == 15

    codex_rules = (home / ".codex" / "rules" / "default.rules").read_text(encoding="utf-8")
    assert 'decision="forbidden"' in codex_rules
    assert 'decision="allow"' not in codex_rules

    cursor_cli = json.loads((home / ".cursor" / "cli-config.json").read_text(encoding="utf-8"))
    assert cursor_cli["approvalMode"] == "auto-review"

    grok_cfg = (home / ".grok" / "config.toml").read_text(encoding="utf-8")
    assert 'permission_mode = "auto"' in grok_cfg

    # Verify project cleanup
    repo_local = json.loads((projects / "test-repo" / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
    assert not any("AppData" in x for x in repo_local["permissions"]["allow"])

    repo_committed = json.loads((projects / "test-repo" / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert not any("gh pr merge" in x for x in repo_committed["permissions"]["allow"])

    # Rollback
    receipt_file = Path(receipt["backup_dir"]) / "receipt.json"
    restored = rollback_permissions(receipt_file)
    assert restored > 0
    assert claude_file.read_text(encoding="utf-8") == claude_orig
