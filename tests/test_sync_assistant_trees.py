"""Tests for assistant tree synchronization drift detection."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_PATH = REPO_ROOT / "scripts" / "sync_assistant_trees.py"

spec = importlib.util.spec_from_file_location("sync_assistant_trees", SYNC_PATH)
assert spec is not None and spec.loader is not None
sync_assistant_trees = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_assistant_trees)


def test_tree_diff_detects_nested_file_content_drift(tmp_path: Path) -> None:
    src = tmp_path / ".claude" / "skills"
    dst = tmp_path / ".cursor" / "skills"
    (src / "demo" / "references").mkdir(parents=True)
    (dst / "demo" / "references").mkdir(parents=True)
    (src / "demo" / "SKILL.md").write_text("canonical\n", encoding="utf-8")
    (dst / "demo" / "SKILL.md").write_text("stale\n", encoding="utf-8")
    (src / "demo" / "references" / "guide.md").write_text("same\n", encoding="utf-8")
    (dst / "demo" / "references" / "guide.md").write_text("same\n", encoding="utf-8")

    assert sync_assistant_trees._diff(src, dst, "tree") == ["differs: skills/demo/SKILL.md"]


def test_tree_diff_detects_nested_missing_and_stale_files(tmp_path: Path) -> None:
    src = tmp_path / ".claude" / "skills"
    dst = tmp_path / ".cursor" / "skills"
    (src / "demo" / "references").mkdir(parents=True)
    (dst / "demo" / "references").mkdir(parents=True)
    (src / "demo" / "references" / "expected.md").write_text("expected\n", encoding="utf-8")
    (dst / "demo" / "references" / "stale.md").write_text("stale\n", encoding="utf-8")

    assert sync_assistant_trees._diff(src, dst, "tree") == [
        "missing in .cursor: skills/demo/references/expected.md",
        "stale in .cursor: skills/demo/references/stale.md",
    ]


def test_file_diff_detects_stale_generated_files(tmp_path: Path) -> None:
    src = tmp_path / ".claude" / "commands"
    dst = tmp_path / ".cursor" / "commands"
    src.mkdir(parents=True)
    dst.mkdir(parents=True)
    (src / "spec.md").write_text("canonical\n", encoding="utf-8")
    (dst / "spec.md").write_text("canonical\n", encoding="utf-8")
    (dst / "old.md").write_text("stale\n", encoding="utf-8")

    assert sync_assistant_trees._diff(src, dst, "files") == [
        "stale in .cursor: commands/old.md"
    ]


def test_sync_check_reports_public_path_drift(tmp_path: Path, capsys) -> None:
    claude_root = tmp_path / ".claude"
    cursor_root = tmp_path / ".cursor"
    (claude_root / "commands").mkdir(parents=True)
    (cursor_root / "commands").mkdir(parents=True)
    (claude_root / "commands" / "spec.md").write_text("canonical\n", encoding="utf-8")
    (cursor_root / "commands" / "spec.md").write_text("stale\n", encoding="utf-8")

    result = sync_assistant_trees.sync(
        check=True, claude_root=claude_root, cursor_root=cursor_root
    )

    assert result == 1
    assert "OUT OF SYNC" in capsys.readouterr().out


def test_sync_check_reports_public_path_in_sync(tmp_path: Path, capsys) -> None:
    claude_root = tmp_path / ".claude"
    cursor_root = tmp_path / ".cursor"
    (claude_root / "commands").mkdir(parents=True)
    (cursor_root / "commands").mkdir(parents=True)
    (claude_root / "commands" / "spec.md").write_text("canonical\n", encoding="utf-8")
    (cursor_root / "commands" / "spec.md").write_text("canonical\n", encoding="utf-8")

    result = sync_assistant_trees.sync(
        check=True, claude_root=claude_root, cursor_root=cursor_root
    )

    assert result == 0
    assert "in sync" in capsys.readouterr().out
