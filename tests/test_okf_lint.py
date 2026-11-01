from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import okf_lint  # noqa: E402

NO_FRONTMATTER = "# Local note\n\nNo frontmatter, [dead link](missing.md).\n"


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def finding_paths(report) -> set[str]:
    return {f.path for f in report.findings}


def test_local_and_archive_are_skipped_by_default(tmp_path: Path) -> None:
    write(tmp_path, "_local/notes/session.md", NO_FRONTMATTER)
    write(tmp_path, "archive/old.md", NO_FRONTMATTER)

    report = okf_lint.lint_bundle(tmp_path)

    assert report.findings == []
    assert report.concepts_checked == 0


def test_tracked_docs_are_still_linted(tmp_path: Path) -> None:
    write(tmp_path, "_local/notes/session.md", NO_FRONTMATTER)
    write(tmp_path, "guides/broken.md", NO_FRONTMATTER)

    report = okf_lint.lint_bundle(tmp_path)

    assert finding_paths(report) == {"guides/broken.md"}


def test_cli_default_skips_local_and_extra_prefix_keeps_defaults(tmp_path: Path) -> None:
    write(tmp_path, "_local/notes/session.md", NO_FRONTMATTER)
    write(tmp_path, "drafts/wip.md", NO_FRONTMATTER)

    assert okf_lint.main([str(tmp_path), "--exclude-prefix", "drafts/"]) == 0
    assert okf_lint.main([str(tmp_path)]) == 1
