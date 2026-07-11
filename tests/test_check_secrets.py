from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.secret_detection import scan_text  # noqa: E402


def findings_for(tmp_path: Path, content: str) -> list[str]:
    path = tmp_path / "sample.txt"
    path.write_text(content, encoding="utf-8")
    return [finding.format() for finding in scan_text(content, "sample.txt")]


def test_real_token_with_example_comment_is_flagged(tmp_path: Path) -> None:
    token = "ghp_" + "A" * 36

    findings = findings_for(tmp_path, f'api_token = "{token}"  # example only\n')

    assert findings == ["sample.txt:1: possible GitHub token"]


def test_variable_and_angle_bracket_placeholders_are_ignored(tmp_path: Path) -> None:
    content = '\n'.join([
        'api_token = "${TOKEN}"',
        'api_token = "<token>"',
    ])

    assert findings_for(tmp_path, content) == []


def test_obvious_redacted_and_dummy_values_are_ignored(tmp_path: Path) -> None:
    content = '\n'.join([
        'api_key = "redacted"',
        'api_key = "dummy-token-value-0000"',
        'api_key = "xxxxxxxxxxxxxxxx"',
        'api_key = "example-token-value"',
        'api_key = "fake-token-value-0000"',
    ])

    assert findings_for(tmp_path, content) == []
