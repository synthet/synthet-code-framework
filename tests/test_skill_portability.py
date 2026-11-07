"""The portability check must catch real problems and stay quiet on clean assets."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.ci import check_skill_portability as check  # noqa: E402

DRIVE = "D:" + "/Projects"
HOME = "C:" + "\\Users\\someone"


def skill(root: Path, folder: str, name: str | None = None, description: str = "Use when testing.", body: str = "Body.") -> Path:
    path = root / ".claude/skills" / folder / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name or folder}\ndescription: {description}\n---\n\n{body}\n", encoding="utf-8")
    return path


def test_clean_skill_passes(tmp_path):
    skill(tmp_path, "good-skill")
    assert check.check(tmp_path, []) == []


def test_name_must_match_its_folder(tmp_path):
    skill(tmp_path, "folder-name", name="other-name")
    assert "must match folder" in check.check(tmp_path, [])[0]


def test_bad_names_and_missing_descriptions_fail(tmp_path):
    skill(tmp_path, "Bad_Name")
    (tmp_path / ".claude/skills/none").mkdir(parents=True)
    (tmp_path / ".claude/skills/none/SKILL.md").write_text("---\nname: none\n---\n\nBody.\n", encoding="utf-8")
    errors = "\n".join(check.check(tmp_path, []))
    assert "lowercase" in errors and "missing description" in errors


def test_long_descriptions_fail(tmp_path):
    skill(tmp_path, "long", description="x" * 1025)
    assert "limit 1024" in check.check(tmp_path, [])[0]


def test_machine_paths_fail_with_a_line_number(tmp_path):
    skill(tmp_path, "paths", body=f"Open {DRIVE}/app.\nThen {HOME}\\notes.")
    errors = check.check(tmp_path, [])
    assert len(errors) == 2 and all("machine path" in e for e in errors)
    assert ":6:" in errors[0]


def test_scripts_and_commands_are_scanned(tmp_path):
    skill(tmp_path, "tool")
    (tmp_path / ".claude/skills/tool/run.py").write_text(f'ROOT = "{DRIVE}"\n', encoding="utf-8")
    command = tmp_path / ".claude/commands/go.md"
    command.parent.mkdir(parents=True)
    command.write_text(f"See {DRIVE}/x\n", encoding="utf-8")
    assert len(check.check(tmp_path, [])) == 2


def test_placeholders_and_uri_forms_are_not_machine_paths(tmp_path):
    skill(tmp_path, "safe", body="Use C:/Users/<user>/x, %USERPROFILE%, and handle /c:/Users/name forms.")
    assert check.check(tmp_path, []) == []


def test_deny_list_catches_names_case_insensitively(tmp_path):
    skill(tmp_path, "named", body="Talks about Secret-Project here.")
    errors = check.check(tmp_path, ["secret-project"])
    assert errors and "denied name" in errors[0]


def test_this_repository_passes():
    assert check.check(ROOT, []) == []
