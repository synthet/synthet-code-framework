from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.agent_memory.consolidate import (
    find_stale_items,
    merge_sections,
    parse_memory_markdown,
    promote_dream,
    render_memory_markdown,
    run_dream,
)
from scripts.agent_memory import schema


def _empty_sections():
    return {section: [] for section in schema.SECTION_ORDER}


def _write_session(repo: Path, name: str, candidates: list[dict]) -> None:
    raw = repo / ".agent-memory" / "raw-sessions"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / name).write_text(
        json.dumps(
            {
                "timestamp": "2026-07-07T00:00:00Z",
                "task_summary": "test",
                "memory_candidates": candidates,
            },
        ),
        encoding="utf-8",
    )


def test_secret_like_memory_rejected_during_dream(tmp_path: Path) -> None:
    (tmp_path / ".agent-memory").mkdir()
    (tmp_path / ".agent-memory" / "memory.md").write_text(
        "# Project Memory\n", encoding="utf-8"
    )
    _write_session(
        tmp_path,
        "2026-07-07T000000Z.yaml",
        [
            {
                "text": "Do not save Bearer abcdefghijklmnopqrstuvwxyz123456 tokens",
                "category": "working_rule",
                "confidence": "high",
                "source_hint": "test fixture",
            }
        ],
    )

    with pytest.raises(ValueError, match="possible secret detected"):
        run_dream(tmp_path)


def test_required_provenance_retained_during_promotion(tmp_path: Path) -> None:
    dream_dir = tmp_path / ".agent-memory" / "dreams"
    dream_dir.mkdir(parents=True)
    dream = dream_dir / "2026-07-07-0000.md"
    changelog = dream_dir / "2026-07-07-0000-changelog.md"
    sections = _empty_sections()
    merged, _ = merge_sections(
        sections,
        [
            (
                "2026-07-07T000000Z.yaml",
                {
                    "memory_candidates": [
                        {
                            "id": "mem-docs-sync",
                            "text": "Sync generated Cursor assets after Claude asset edits.",
                            "category": "working_rule",
                            "confidence": "high",
                            "source_hint": ".agent/SKILL_CHANGE_AST10_REVIEW.md",
                            "verified_at": "2026-07-07",
                            "verification_status": "verified",
                            "stale_after": "2027-01-07",
                            "related_paths": [".claude/", ".cursor/"],
                            "related_tasks": ["PR #123"],
                        }
                    ]
                },
            )
        ],
        max_per_section=40,
    )
    dream.write_text(render_memory_markdown(merged), encoding="utf-8")
    changelog.write_text("# Dream changelog\n", encoding="utf-8")

    memory_path = promote_dream(tmp_path, dream)
    promoted = parse_memory_markdown(memory_path.read_text(encoding="utf-8"))
    item = promoted["Working Rules"][0]

    assert item.id == "mem-docs-sync"
    assert item.source_hint == ".agent/SKILL_CHANGE_AST10_REVIEW.md"
    assert item.verified_at == "2026-07-07"
    assert item.verification_status == "verified"
    assert item.stale_after == "2027-01-07"
    assert item.related_paths == [".claude/", ".cursor/"]
    assert item.related_tasks == ["PR #123"]


def test_stale_memory_detection_uses_stale_after() -> None:
    sections = parse_memory_markdown(
        """# Project Memory

## Working Rules

- Re-verify this rule. (updated: 2026-07-01)
  id: mem-stale
  source_hint: issue #1
  confidence: medium
  verified_at: 2026-07-01
  verification_status: verified
  stale_after: 2026-07-02
  related_paths: []
  related_tasks: []
"""
    )

    stale = find_stale_items(sections, staleness_days=9999)

    assert stale == [
        "Re-verify this rule. (stale after: 2026-07-02) [section: Working Rules]"
    ]


def test_safe_duplicate_consolidation_merges_metadata_without_duplicate_items() -> None:
    merged, _ = merge_sections(
        _empty_sections(),
        [
            (
                "one.yaml",
                {
                    "memory_candidates": [
                        {
                            "id": "mem-one",
                            "text": "Run sync after skill edits.",
                            "category": "working_rule",
                            "confidence": "medium",
                            "source_hint": "docs/one.md",
                            "related_paths": [".claude/skills"],
                            "related_tasks": ["issue #1"],
                        }
                    ]
                },
            ),
            (
                "two.yaml",
                {
                    "memory_candidates": [
                        {
                            "text": "Run sync after skill edits!",
                            "category": "working_rule",
                            "confidence": "high",
                            "source_hint": "docs/two.md",
                            "related_paths": [".cursor/skills"],
                            "related_tasks": ["PR #2"],
                        }
                    ]
                },
            ),
        ],
        max_per_section=40,
    )

    items = merged["Working Rules"]
    assert len(items) == 1
    assert items[0].id == "mem-one"
    assert items[0].confidence == "high"
    assert items[0].source_hint == "docs/one.md; docs/two.md"
    assert items[0].related_paths == [".claude/skills", ".cursor/skills"]
    assert items[0].related_tasks == ["issue #1", "PR #2"]
