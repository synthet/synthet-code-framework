from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "agent_policy" / "validate_export.py"
spec = importlib.util.spec_from_file_location("validate_export", VALIDATOR_PATH)
assert spec is not None and spec.loader is not None
validate_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_export)


def write_policy(tmp_path: Path, *, max_files: int = 20, max_total_bytes: int = 10000) -> Path:
    policy = tmp_path / "agent-policy.yaml"
    policy.write_text(
        f"""
version: 1
default_mode: review_only
tool_classes: {{}}
approval_requirements:
  external_export:
    required: true
    marker: APPROVED_EXTERNAL_EXPORT
external_review_constraints:
  review_only: true
  allow_writes: false
denied_globs:
  - .env
  - '**/*.pem'
  - '**/*.key'
  - '**/*secret*'
  - '**/*credential*'
allowed_globs:
  - '**/*.md'
  - '**/*.py'
  - '**/*.txt'
  - '**/*.yaml'
  - '**/*.yml'
  - '**/*.json'
  - 'VERSION'
max_files: {max_files}
max_total_bytes: {max_total_bytes}
""".lstrip(),
        encoding="utf-8",
    )
    return policy


def test_allowed_files_pass_within_limits(tmp_path: Path) -> None:
    policy = write_policy(tmp_path)

    assert validate_export.validate(["README.md"], policy_path=policy) == ["README.md"]


@pytest.mark.parametrize("candidate", [".env", "private.pem", "keys/deploy.key", "docs/secret-plan.md", "docs/credentials.json"])
def test_denied_and_credential_like_files_fail(tmp_path: Path, candidate: str) -> None:
    policy = write_policy(tmp_path)

    with pytest.raises(validate_export.ValidationError):
        validate_export.validate([candidate], policy_path=policy)


def test_max_file_count_is_enforced(tmp_path: Path) -> None:
    policy = write_policy(tmp_path, max_files=1)

    with pytest.raises(validate_export.ValidationError, match="too many files"):
        validate_export.validate(["README.md", "VERSION"], policy_path=policy)


def test_max_total_bytes_is_enforced(tmp_path: Path) -> None:
    policy = write_policy(tmp_path, max_total_bytes=1)

    with pytest.raises(validate_export.ValidationError, match="total bytes exceed limit"):
        validate_export.validate(["README.md"], policy_path=policy)


@pytest.mark.parametrize("candidate", ["/etc/passwd", "../README.md", "docs/../README.md", "~/README.md", "docs/*.md"])
def test_path_traversal_absolute_and_ambiguous_paths_fail(tmp_path: Path, candidate: str) -> None:
    policy = write_policy(tmp_path)

    with pytest.raises(validate_export.ValidationError):
        validate_export.validate([candidate], policy_path=policy)


def test_external_export_requires_explicit_approval_marker(tmp_path: Path) -> None:
    policy = write_policy(tmp_path)

    with pytest.raises(validate_export.ValidationError, match="requires approval marker"):
        validate_export.validate(["README.md"], policy_path=policy, external_export=True)

    assert validate_export.validate(
        ["README.md"],
        policy_path=policy,
        external_export=True,
        approval_marker="APPROVED_EXTERNAL_EXPORT",
    ) == ["README.md"]
