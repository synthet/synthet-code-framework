"""Plugin manifests point at the existing Claude and Cursor trees."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "build_plugin_manifests.py"
spec = importlib.util.spec_from_file_location("build_plugin_manifests", SCRIPT)
assert spec is not None and spec.loader is not None
build_plugin_manifests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_plugin_manifests)


def test_manifests_match_the_generator_and_existing_trees() -> None:
    expected = build_plugin_manifests.documents(REPO_ROOT)
    assert expected[".claude/.claude-plugin/plugin.json"]["version"] == (
        REPO_ROOT / "VERSION"
    ).read_text(encoding="utf-8").strip()

    for relative, document in expected.items():
        path = REPO_ROOT / relative
        assert json.loads(path.read_text(encoding="utf-8")) == document

    claude_root = REPO_ROOT / ".claude"
    cursor_root = REPO_ROOT / ".cursor"
    assert not (claude_root / ".mcp.json").exists()
    assert (claude_root / "skills").is_dir()
    assert (claude_root / "commands").is_dir()
    assert list((claude_root / "agents").glob("*.md"))
    assert (cursor_root / "skills").is_dir()
    assert (cursor_root / "rules").is_dir()
    assert (cursor_root / "commands").is_dir()
    assert list((cursor_root / "agents").glob("*.md"))
    assert expected[".cursor/.cursor-plugin/plugin.json"]["mcpServers"] == {}
    assert (REPO_ROOT / ".claude-plugin" / "marketplace.json").is_file()
    assert (claude_root / ".claude-plugin" / "plugin.json").is_file()
    assert (cursor_root / ".cursor-plugin" / "plugin.json").is_file()
