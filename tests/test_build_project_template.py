"""synthet-project-template: built from bootstrap, and template + init_project.py == a direct seed."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bootstrap  # noqa: E402
from scripts import build_project_template as bpt  # noqa: E402

PROJECT = ["--name", "Demo App", "--desc", "A demo project", "--stack", "python",
           "--repo-url", "https://github.com/example/demo-app"]


@pytest.fixture(scope="module")
def template(tmp_path_factory) -> Path:
    target = tmp_path_factory.mktemp("tpl") / "synthet-project-template"
    bpt.build(target)
    return target


def _seed(target: Path) -> None:
    argv = sys.argv
    sys.argv = ["bootstrap.py", "--target", str(target), "--backlog", "local-markdown", *PROJECT]
    try:
        assert bootstrap.main() == 0
    finally:
        sys.argv = argv


def test_template_keeps_placeholders_and_adds_init(template: Path) -> None:
    assert (template / "init_project.py").is_file()
    assert (template / "TEMPLATE.md").is_file()
    readme = (template / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# ${PROJECT_NAME}\n\n${PROJECT_DESC}")
    assert "${PROJECT_NAME}" in (template / "CLAUDE.md").read_text(encoding="utf-8")
    assert "${TEST_CMD}" in (template / "AGENTS.md").read_text(encoding="utf-8")


def test_template_plus_init_equals_direct_bootstrap(template: Path, tmp_path: Path) -> None:
    project = tmp_path / "from-template"
    shutil.copytree(template, project)
    res = subprocess.run([sys.executable, str(project / "init_project.py"), *PROJECT],
                         capture_output=True, text=True, check=False)
    assert res.returncode == 0, res.stderr
    assert not (project / "init_project.py").exists()
    assert not (project / "TEMPLATE.md").exists()
    direct = tmp_path / "direct"
    _seed(direct)
    assert bpt.diff_trees(direct, project) == []


def test_check_reports_sync_and_drift(template: Path, tmp_path: Path, capsys) -> None:
    copy = tmp_path / "copy"
    shutil.copytree(template, copy)
    (copy / ".git").mkdir()  # .git is ignored
    assert bpt.main(["--target", str(copy), "--check"]) == 0
    (copy / "AGENTS.md").write_text("edited\n", encoding="utf-8")
    (copy / "stray.txt").write_text("x\n", encoding="utf-8")
    assert bpt.main(["--target", str(copy), "--check"]) == 1
    out = capsys.readouterr().out
    assert "changed: AGENTS.md" in out
    assert "extra: stray.txt" in out


def test_build_keeps_git_dir_and_replaces_old_files(tmp_path: Path) -> None:
    target = tmp_path / "t"
    (target / ".git").mkdir(parents=True)
    (target / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (target / "old.txt").write_text("stale\n", encoding="utf-8")
    bpt.build(target)
    assert (target / ".git" / "HEAD").is_file()
    assert not (target / "old.txt").exists()
