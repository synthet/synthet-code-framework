"""Focused tests for recursive mirror checks and Codex agent rendering."""

from __future__ import annotations

import tomllib

from scripts import sync_assistant_trees as syncer


def test_diff_tree_detects_nested_content_drift(tmp_path) -> None:
    source = tmp_path / "source"
    mirror = tmp_path / "mirror"
    (source / "skill" / "references").mkdir(parents=True)
    (mirror / "skill" / "references").mkdir(parents=True)
    (source / "skill" / "references" / "guide.md").write_text("canonical", encoding="utf-8")
    (mirror / "skill" / "references" / "guide.md").write_text("stale", encoding="utf-8")

    assert syncer._diff_tree(source, mirror, "mirror") == [
        "differs: mirror/skill/references/guide.md"
    ]


def test_codex_agent_renderer_produces_valid_toml(tmp_path) -> None:
    source = tmp_path / "reviewer.md"
    source.write_text(
        "---\nname: reviewer\ndescription: Review carefully.\n---\n\n"
        "Check correctness and cite evidence.\n",
        encoding="utf-8",
    )

    rendered = syncer._render_codex_agent(source)
    parsed = tomllib.loads(rendered)
    assert parsed == {
        "name": "reviewer",
        "description": "Review carefully.",
        "developer_instructions": "Check correctness and cite evidence.\n",
    }
