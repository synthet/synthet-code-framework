"""Tests for compiled skill harnesses and shared skill_harness helpers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.skill_harness.acceptance import parse_acceptance_criteria, render_validation_report
from scripts.skill_harness.changelog import promote_unreleased, unreleased_bullets
from scripts.skill_harness.eval_signals import build_log_command, schema_skeleton
from scripts.skill_harness.lint_router import recommend as lint_recommend
from scripts.skill_harness.search_router import recommend
from scripts.skill_harness.verify_catalog import is_secret_path, list_profiles, resolve_gates
from scripts.skill_harness.version import bump_semver, detect_version_source, write_version


def _run_harness(skill: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    script = ROOT / ".claude" / "skills" / skill / "scripts" / "harness.py"
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_bump_semver_levels() -> None:
    assert bump_semver("1.2.3", "patch") == "1.2.4"
    assert bump_semver("1.2.3", "minor") == "1.3.0"
    assert bump_semver("1.2.3", "major") == "2.0.0"


def test_promote_unreleased_and_bullets() -> None:
    text = """# Changelog

## [Unreleased]

### Added

- New harness support

### Fixed

## [0.1.0] — 2026-01-01

- Old
"""
    bullets = unreleased_bullets(text)
    assert bullets == ["New harness support"]
    from datetime import date

    out = promote_unreleased(text, "0.2.0", date(2026, 7, 19))
    assert "## [Unreleased]\n" in out
    assert "## [0.2.0] — 2026-07-19" in out
    assert "New harness support" in out
    # empty ### Fixed dropped
    assert "### Fixed" not in out.split("## [0.1.0]")[0]


def test_detect_and_write_version_file(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    source = detect_version_source(tmp_path)
    assert source is not None
    assert source.version == "0.1.0"
    write_version(source, "0.1.1")
    assert (tmp_path / "VERSION").read_text(encoding="utf-8").strip() == "0.1.1"


def test_parse_acceptance_criteria_lines_and_table() -> None:
    spec = """
# Spec

- AC-1: Users can log in
- AC-2: Sessions expire

| AC | Criterion |
|----|-----------|
| AC-3 | Reports export as CSV |
"""
    acs = parse_acceptance_criteria(spec)
    ids = [a.id for a in acs]
    assert ids == ["AC-1", "AC-2", "AC-3"]
    assert "log in" in acs[0].text


def test_render_rejects_verified_without_evidence() -> None:
    with pytest.raises(ValueError, match="evidence"):
        render_validation_report(
            "demo",
            [{"id": "AC-1", "criterion": "x", "verdict": "Verified", "evidence": ""}],
        )


def test_search_router() -> None:
    rec = recommend("content")
    assert rec.use == "rg"
    rec2 = recommend("ast-grep")
    assert "ast-grep" in rec2.use


def test_secret_path_gate() -> None:
    assert is_secret_path(".env")
    assert is_secret_path("config/secrets.json")
    assert not is_secret_path("README.md")


def test_release_bump_harness_dry_run() -> None:
    expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    proc = _run_harness("release-bump", "--json")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["current_version"] == expected
    assert data["applied"] is False


def test_release_bump_harness_apply(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# test\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Thing\n\n## [1.0.0] — 2026-01-01\n\n- Start\n",
        encoding="utf-8",
    )
    proc = _run_harness(
        "release-bump",
        "--repo",
        str(tmp_path),
        "--level",
        "minor",
        "--apply",
        "--date",
        "2026-07-19",
        "--json",
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["proposed_version"] == "1.1.0"
    assert data["applied"] is True
    assert (tmp_path / "VERSION").read_text(encoding="utf-8").strip() == "1.1.0"
    cl = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [1.1.0] — 2026-07-19" in cl


def test_validate_implementation_harness(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("- AC-1: Foo works\n- AC-2: Bar works\n", encoding="utf-8")
    bad = _run_harness(
        "validate-implementation",
        "--spec",
        str(spec),
        "--verdict",
        "AC-1=Verified|",
        "--json",
    )
    assert bad.returncode != 0

    good = _run_harness(
        "validate-implementation",
        "--spec",
        str(spec),
        "--verdict",
        "AC-1=Verified|pytest passed",
        "--verdict",
        "AC-2=Failed|assertion error",
        "--json",
    )
    assert good.returncode == 0, good.stderr
    data = json.loads(good.stdout)
    assert data["all_verified"] is False
    assert data["rows"][0]["verdict"] == "Verified"


def test_search_tool_selection_harness() -> None:
    proc = _run_harness("search-tool-selection", "--task-type", "filename", "--json")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["use"] == "fd"


def test_verification_harness_catalog() -> None:
    proc = _run_harness("verification-before-completion", "--json")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert "tests_pass" in data["catalog"]


def test_commit_and_push_dry_run() -> None:
    proc = _run_harness("commit-and-push", "--json")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["committed"] is False
    assert data["pushed"] is False


def test_commit_refuses_without_execute() -> None:
    proc = _run_harness("commit-and-push", "--commit", "-m", "test", "--json")
    assert proc.returncode != 0
    data = json.loads(proc.stdout)
    assert any("execute" in n.lower() for n in data["notes"])


def test_verify_profiles_and_resolve_gates() -> None:
    profiles = list_profiles()
    assert "agent-assets" in profiles
    assert profiles["agent-assets"] == ["sync_check", "frontmatter", "cli_skills"]
    rows = resolve_gates(profile="tests")
    assert len(rows) == 1
    assert rows[0]["id"] == "pytest"
    mixed = resolve_gates(profile="tests", gate_ids=["okf_lint"])
    assert [r["id"] for r in mixed] == ["pytest", "okf_lint"]


def test_lint_router() -> None:
    rec = lint_recommend("python", paths="scripts")
    assert rec.stack == "python"
    assert any("ruff check scripts" in c for c in rec.check_commands)
    assert "ruff check --fix" in rec.confirmation_gates


def test_eval_signals_build_log_command() -> None:
    payload = build_log_command(
        summary="Implemented harness wave 2",
        test_pass_rate="yes",
        first_try_success="yes",
        iteration_count=1,
        candidates=["Scoped lint router|successful_pattern|high"],
    )
    assert payload["outcome"] == "first_try_success"
    assert payload["test_results"] == "pass"
    assert "log_session.py" in payload["command"]
    assert schema_skeleton()["signals"]["test_pass_rate"] == ["no", "partial", "yes"]


def test_task_env_harness_list() -> None:
    proc = _run_harness("task-env-package-tools", "--list", "--json")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert "agent-assets" in data["profiles"]
    assert any(g["id"] == "sync_check" for g in data["catalog"])


def test_task_env_harness_profile_dry_run() -> None:
    proc = _run_harness(
        "task-env-package-tools",
        "--profile",
        "agent-assets",
        "--json",
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["ran"] is False
    assert [g["id"] for g in data["selected"]] == [
        "sync_check",
        "frontmatter",
        "cli_skills",
    ]


def test_lint_format_harness() -> None:
    proc = _run_harness(
        "lint-format-security",
        "--stack",
        "shell",
        "--paths",
        "scripts/*.sh",
        "--json",
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["stack"] == "shell"
    assert any("shellcheck" in c for c in data["check_commands"])


def test_eval_harness_schema_and_emit() -> None:
    schema = _run_harness("eval", "--json")
    assert schema.returncode == 0, schema.stderr
    data = json.loads(schema.stdout)
    assert "successful_pattern" in data["categories"]

    bad = _run_harness(
        "eval",
        "--emit-log-cmd",
        "--summary",
        "x",
        "--test-pass-rate",
        "yes",
        "--first-try-success",
        "yes",
        "--iteration-count",
        "2",
        "--candidate",
        "ok|successful_pattern|high",
        "--json",
    )
    assert bad.returncode != 0

    good = _run_harness(
        "eval",
        "--emit-log-cmd",
        "--summary",
        "Wave 2 compile",
        "--test-pass-rate",
        "partial",
        "--first-try-success",
        "no",
        "--iteration-count",
        "2",
        "--candidate",
        "Need fixture tests for harnesses|working_rule|high",
        "--json",
    )
    assert good.returncode == 0, good.stderr
    out = json.loads(good.stdout)
    assert out["outcome"] == "partial"
    assert out["test_results"] == "partial"
