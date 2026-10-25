import json
from pathlib import Path

from jev_engineering.install_config import apply, rollback
from jev_engineering.mcp_server import create_server
from jev_engineering.service import Engineering
from jev_engineering.state_store import StateStore

ROOT = Path(__file__).resolve().parents[1]


def _home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    (home / ".cursor").mkdir(parents=True)
    (home / ".claude").mkdir()
    (home / ".codex").mkdir()
    (home / ".gemini" / "antigravity").mkdir(parents=True)
    (home / ".gemini" / "config").mkdir()
    secret = "github_pat_testvalue_do_not_copy"
    cursor = {
        "mcpServers": {
            "llmwiki-ro-core": {"command": "llmwiki", "args": ["mcp"]},
            "github": {"type": "http", "headers": {"Authorization": f"Bearer {secret}"}},
        }
    }
    (home / ".cursor" / "mcp.json").write_text(json.dumps(cursor, indent=2), encoding="utf-8")
    (home / ".claude.json").write_text(
        json.dumps({"permissions": {"defaultMode": "auto"}, "mcpServers": {"llmwiki-ro-core": {"command": "llmwiki"}}}),
        encoding="utf-8",
    )
    (home / ".gemini" / "settings.json").write_text(
        json.dumps({"mcpServers": {"llmwiki-ro-core": {"command": "llmwiki"}}, "security": {"auth": {"selectedType": "gemini-api-key"}}}),
        encoding="utf-8",
    )
    (home / ".gemini" / "antigravity" / "mcp_config.json").write_text(
        json.dumps({"mcpServers": {"llmwiki-ro-core": {"command": "llmwiki"}}}),
        encoding="utf-8",
    )
    (home / ".gemini" / "config" / "mcp_config.json").write_text(
        json.dumps({"mcpServers": {"jev-rw-systemone": {"command": "uv"}}}),
        encoding="utf-8",
    )
    (home / ".codex" / "config.toml").write_text(
        'approval_policy = "on-request"\nsandbox_mode = "workspace-write"\nmodel = "gpt-6.1-sol"\n\n'
        '[mcp_servers.llmwiki-ro-core]\ncommand = "llmwiki"\n',
        encoding="utf-8",
    )
    (home / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "permissions": {"defaultMode": "auto"},
                "model": "opus",
                "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "warp"}]}]},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (home / ".claude" / "CLAUDE.md").write_text("keep me\n", encoding="utf-8")
    (home / ".codex" / "AGENTS.md").write_text("keep me\n", encoding="utf-8")
    (home / ".gemini" / "GEMINI.md").write_text("keep me\n", encoding="utf-8")
    return home


def test_apply_preserves_existing_config_and_rolls_back(tmp_path, monkeypatch):
    monkeypatch.delenv("JEV_ENV_FILE", raising=False)
    root = tmp_path / "proj"
    (root / "instructions").mkdir(parents=True)
    (root / "scripts").mkdir()
    for name in ("JEV_ENGINEERING.md", "cursor-rule.mdc"):
        (root / "instructions" / name).write_text((ROOT / "instructions" / name).read_text(encoding="utf-8"), encoding="utf-8")
    home = _home(tmp_path)
    secret = "github_pat_testvalue_do_not_copy"
    receipt = apply(home=home, root=root)
    cursor = json.loads((home / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
    assert "jev-engineering" in cursor["mcpServers"]
    assert cursor["mcpServers"]["llmwiki-ro-core"]["command"] == "llmwiki"
    assert secret in cursor["mcpServers"]["github"]["headers"]["Authorization"]
    assert "jev-rw-systemone" in json.loads((home / ".gemini" / "config" / "mcp_config.json").read_text(encoding="utf-8"))["mcpServers"]
    settings = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings["permissions"]["defaultMode"] == "auto"
    assert settings["model"] == "opus"
    assert settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"] == "warp"
    assert any("hook-pre-tool.ps1" in hook["command"] for group in settings["hooks"]["PreToolUse"] for hook in group["hooks"])
    codex = (home / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert 'approval_policy = "on-request"' in codex
    assert "jev-engineering" in codex
    assert "<!-- BEGIN JEV ENGINEERING -->" in (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
    assert secret not in json.dumps(receipt)
    again = apply(home=home, root=root)
    assert again["files"] == []
    rollback(root / "backups" / receipt["stamp"] / "receipt.json")
    restored = json.loads((home / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
    assert "jev-engineering" not in restored["mcpServers"]
    assert secret in restored["mcpServers"]["github"]["headers"]["Authorization"]
    assert not (home / ".cursor" / "rules" / "jev-engineering.mdc").exists()


def test_mcp_tools_are_registered(tmp_path):
    engineering = Engineering(
        backend=FailingBackend(),
        store=StateStore(tmp_path / "state.db"),
        metrics_path=tmp_path / "metrics.jsonl",
        root=tmp_path,
    )
    server = create_server(engineering)
    names = _tool_names(server)
    assert names == {"jev_decide", "jev_route_task", "jev_select_context", "jev_assess_risk"}


class FailingBackend:
    def system_one(self, **kwargs):
        raise RuntimeError("offline")


def _tool_names(server) -> set[str]:
    for attr in ("_tools", "tools", "_tool_manager"):
        value = getattr(server, attr, None)
        if isinstance(value, dict):
            return set(value)
        tools = getattr(value, "tools", None)
        if isinstance(tools, dict):
            return set(tools)
        listed = getattr(value, "_tools", None)
        if isinstance(listed, dict):
            return set(listed)
    request = getattr(server, "list_tools", None)
    if request is not None:
        import asyncio

        result = asyncio.run(request())
        return {tool.name for tool in result}
    raise AssertionError(f"cannot see tools on {type(server)}")
