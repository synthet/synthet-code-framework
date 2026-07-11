"""Tests for assistant tree synchronization and Codex agent rendering."""

from __future__ import annotations

import importlib.util
import tomllib
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


def test_tree_diff_detects_missing_empty_directory(tmp_path: Path) -> None:
    src = tmp_path / ".claude" / "skills"
    dst = tmp_path / ".cursor" / "skills"
    (src / "demo" / "empty").mkdir(parents=True)
    (dst / "demo").mkdir(parents=True)

    assert sync_assistant_trees._diff(src, dst, "tree") == [
        "missing in .cursor: skills/demo/empty/"
    ]


def test_tree_diff_detects_stale_empty_directory(tmp_path: Path) -> None:
    src = tmp_path / ".claude" / "skills"
    dst = tmp_path / ".cursor" / "skills"
    (src / "demo").mkdir(parents=True)
    (dst / "demo" / "empty").mkdir(parents=True)

    assert sync_assistant_trees._diff(src, dst, "tree") == [
        "stale in .cursor: skills/demo/empty/"
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


def test_rules_diff_detects_stale_md_file(tmp_path: Path) -> None:
    src = tmp_path / ".claude" / "rules"
    dst = tmp_path / ".cursor" / "rules"
    src.mkdir(parents=True)
    dst.mkdir(parents=True)
    (src / "style.md").write_text("canonical\n", encoding="utf-8")
    (dst / "style.mdc").write_text("canonical\n", encoding="utf-8")
    (dst / "old.md").write_text("stale\n", encoding="utf-8")

    assert sync_assistant_trees._diff(src, dst, "rules") == [
        "stale in .cursor: rules/old.md"
    ]


def test_file_diff_detects_stale_unexpected_extension(tmp_path: Path) -> None:
    src = tmp_path / ".claude" / "commands"
    dst = tmp_path / ".cursor" / "commands"
    src.mkdir(parents=True)
    dst.mkdir(parents=True)
    (src / "spec.md").write_text("canonical\n", encoding="utf-8")
    (dst / "spec.md").write_text("canonical\n", encoding="utf-8")
    (dst / "unexpected.txt").write_text("stale\n", encoding="utf-8")

    assert sync_assistant_trees._diff(src, dst, "files") == [
        "stale in .cursor: commands/unexpected.txt"
    ]


def test_diff_tree_detects_nested_content_drift(tmp_path: Path) -> None:
    source = tmp_path / "source"
    mirror = tmp_path / "mirror"
    (source / "skill" / "references").mkdir(parents=True)
    (mirror / "skill" / "references").mkdir(parents=True)
    (source / "skill" / "references" / "guide.md").write_text("canonical", encoding="utf-8")
    (mirror / "skill" / "references" / "guide.md").write_text("stale", encoding="utf-8")

    assert sync_assistant_trees._diff_tree(source, mirror, "mirror") == [
        "differs: mirror/skill/references/guide.md"
    ]


def test_codex_agent_renderer_produces_valid_toml(tmp_path: Path) -> None:
    source = tmp_path / "reviewer.md"
    source.write_text(
        "---\nname: reviewer\ndescription: Review carefully.\n---\n\n"
        "Check correctness and cite evidence.\n",
        encoding="utf-8",
    )

    rendered = sync_assistant_trees._render_codex_agent(source)
    parsed = tomllib.loads(rendered)
    assert parsed == {
        "name": "reviewer",
        "description": "Review carefully.",
        "developer_instructions": "Check correctness and cite evidence.\n",
    }
