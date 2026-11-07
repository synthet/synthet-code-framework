"""bg-status must find repositories without a hard-coded machine path."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude/skills/bg-status/scripts"))
import bg_status  # noqa: E402


def test_environment_variable_sets_the_repos_root(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECTS_ROOT", str(tmp_path))
    assert bg_status.default_repos_root() == str(tmp_path)


def test_default_is_the_parent_of_the_current_repository(monkeypatch, tmp_path):
    monkeypatch.delenv("PROJECTS_ROOT", raising=False)
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    monkeypatch.chdir(repo / "sub")
    assert Path(bg_status.default_repos_root()).resolve() == tmp_path.resolve()


def test_outside_a_repository_the_default_is_the_parent_folder(monkeypatch, tmp_path):
    monkeypatch.delenv("PROJECTS_ROOT", raising=False)
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(plain)
    assert Path(bg_status.default_repos_root()).resolve() == tmp_path.resolve()


def test_status_roots_follow_the_repos_root():
    assert bg_status.default_status_roots("X:/work") == ["X:/work/_wt-*/runs", "X:/work/*/runs", "X:/work/*/work"]


def test_shipped_skill_names_no_machine_path():
    for rel in ("SKILL.md", "scripts/bg_status.py"):
        assert "D:/Projects" not in (ROOT / ".claude/skills/bg-status" / rel).read_text(encoding="utf-8")
