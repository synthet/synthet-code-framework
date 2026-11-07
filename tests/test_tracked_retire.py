"""tracked-retire may list a tracked copy only when it can prove nothing would be lost."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import agent_setup as setup

SKILL = "---\nname: demo\ndescription: Demo\n---\n\nFor ${PROJECT_NAME}, follow this.\n"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-C", str(root), *args], check=True, capture_output=True)


def commit(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change")


def framework(tmp_path: Path, packs: dict | None = None) -> tuple[Path, dict]:
    root = tmp_path / "framework"
    root.mkdir()
    git(root, "init", "-q")
    write(root / ".claude/skills/demo/SKILL.md", SKILL)
    write(root / ".claude/commands/spec.md", "---\ndescription: Spec\n---\n\nDraft a spec.\n")
    write(root / ".agent/SAFETY.md", "Rules.\n")
    manifest = {"skills": [{"id": "demo", "source": ".claude/skills/demo", "pack": "global", "global": True, "projects": []}, *(packs or {}).get("skills", [])]}
    write(root / ".agent/setup/library.json", json.dumps(manifest))
    commit(root)
    return root, manifest


def repo(tmp_path: Path, body: str = "For the current project, follow this.\n") -> Path:
    root = tmp_path / "projects/app"
    root.mkdir(parents=True)
    git(root, "init", "-q")
    text = f"---\nname: demo\ndescription: Demo\n---\n\n{body}"
    write(root / ".claude/skills/demo/SKILL.md", text)
    write(root / ".agents/skills/demo/SKILL.md", text)
    write(root / "README.md", "App.\n")
    commit(root)
    return root


def run(fw: Path, manifest: dict, project: Path) -> dict:
    return setup.tracked_retirement(fw, project, manifest)


def test_an_unedited_tracked_copy_is_listed_from_every_tree(tmp_path):
    fw, manifest = framework(tmp_path)
    result = run(fw, manifest, repo(tmp_path))
    assert result["retire"]["demo"] == [".agents/skills/demo/SKILL.md", ".claude/skills/demo/SKILL.md"]
    assert result["kept"] == {}


def test_a_copy_of_an_old_library_version_is_listed(tmp_path):
    fw, manifest = framework(tmp_path)
    project = repo(tmp_path)
    write(fw / ".claude/skills/demo/SKILL.md", SKILL + "Newer text.\n")
    commit(fw)
    assert "demo" in run(fw, manifest, project)["retire"]


def test_a_committed_local_edit_keeps_the_skill_in_every_tree(tmp_path):
    fw, manifest = framework(tmp_path)
    project = repo(tmp_path)
    path = project / ".claude/skills/demo/SKILL.md"
    write(path, path.read_text(encoding="utf-8") + "A rule only this repository has.\n")
    commit(project)
    result = run(fw, manifest, project)
    assert result["retire"] == {}
    assert "differs from every library version" in result["kept"]["demo"]


def test_an_uncommitted_edit_is_kept(tmp_path):
    fw, manifest = framework(tmp_path)
    project = repo(tmp_path)
    path = project / ".agents/skills/demo/SKILL.md"
    write(path, path.read_text(encoding="utf-8") + "Work in progress.\n")
    result = run(fw, manifest, project)
    assert result["retire"] == {}
    assert "uncommitted edit" in result["kept"]["demo"]


def test_a_line_ending_difference_is_not_an_edit(tmp_path):
    fw, manifest = framework(tmp_path)
    project = repo(tmp_path)
    path = project / ".claude/skills/demo/SKILL.md"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert "demo" in run(fw, manifest, project)["retire"]


def test_an_untracked_file_in_the_skill_is_kept(tmp_path):
    fw, manifest = framework(tmp_path)
    project = repo(tmp_path)
    write(project / ".claude/skills/demo/notes.md", "My notes.\n")
    result = run(fw, manifest, project)
    assert result["retire"] == {}
    assert "untracked file" in result["kept"]["demo"]


def test_a_reference_from_repository_code_keeps_the_skill(tmp_path):
    fw, manifest = framework(tmp_path)
    project = repo(tmp_path)
    write(project / "scripts/run.py", 'PATH = ".claude/skills/demo/SKILL.md"\n')
    commit(project)
    result = run(fw, manifest, project)
    assert result["retire"] == {}
    assert "referenced by scripts/run.py" in result["kept"]["demo"]


def test_a_stack_pack_the_repository_opted_into_is_not_touched(tmp_path):
    pack = {"skills": [{"id": "stack", "source": ".claude/skills/stack", "pack": "stack", "global": False, "projects": ["app"]}]}
    fw, manifest = framework(tmp_path, pack)
    write(fw / ".claude/skills/stack/SKILL.md", "---\nname: stack\ndescription: Stack\n---\n\nStack.\n")
    commit(fw)
    project = repo(tmp_path)
    write(project / ".claude/skills/stack/SKILL.md", "---\nname: stack\ndescription: Stack\n---\n\nStack.\n")
    commit(project)
    assert "stack" not in run(fw, manifest, project)["retire"]


def test_a_project_owned_skill_is_never_considered(tmp_path):
    fw, manifest = framework(tmp_path)
    project = repo(tmp_path)
    write(project / ".claude/skills/app-only/SKILL.md", "---\nname: app-only\ndescription: Mine\n---\n\nMine.\n")
    commit(project)
    result = run(fw, manifest, project)
    assert "app-only" not in result["retire"] and "app-only" not in result["kept"]


def test_an_installer_bundled_copy_matches_its_source(tmp_path):
    fw, manifest = framework(tmp_path)
    project = repo(tmp_path)
    write(project / ".claude/skills/demo/references/shared/.agent/SAFETY.md", "Rules.\n")
    write(project / ".agents/skills/demo/references/shared/.agent/SAFETY.md", "Rules.\n")
    commit(project)
    assert len(run(fw, manifest, project)["retire"]["demo"]) == 4


def test_a_generated_alias_is_listed_when_it_matches_its_command(tmp_path):
    fw, manifest = framework(tmp_path)
    project = repo(tmp_path)
    write(project / ".claude/skills/framework-spec/SKILL.md", '---\nname: framework-spec\ndescription: "Explicit framework workflow: spec"\n---\n\nDraft a spec.\n')
    commit(project)
    assert "framework-spec" in run(fw, manifest, project)["retire"]


def test_an_edited_generated_alias_is_kept(tmp_path):
    fw, manifest = framework(tmp_path)
    project = repo(tmp_path)
    write(project / ".claude/skills/framework-spec/SKILL.md", '---\nname: framework-spec\ndescription: "Explicit framework workflow: spec"\n---\n\nMy own process.\n')
    commit(project)
    assert "framework-spec" in run(fw, manifest, project)["kept"]


def test_a_skill_with_no_tracked_files_is_left_to_plan(tmp_path):
    fw, manifest = framework(tmp_path)
    project = tmp_path / "projects/app"
    project.mkdir(parents=True)
    git(project, "init", "-q")
    write(project / "README.md", "App.\n")
    commit(project)
    write(project / ".claude/skills/demo/SKILL.md", "Untracked.\n")
    assert run(fw, manifest, project) == {"project": "app", "retire": {}, "kept": {}}


def test_the_command_writes_only_its_report(tmp_path):
    fw, manifest = framework(tmp_path)
    project = repo(tmp_path)
    before = subprocess.run(["git", "-C", str(project), "status", "--porcelain"], capture_output=True, text=True).stdout
    out = tmp_path / "report.json"
    code = setup.main(["tracked-retire", "--framework", str(fw), "--projects-root", str(project.parent), "--project", "app", "--out", str(out)])
    assert code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["retire"]["demo"]
    assert subprocess.run(["git", "-C", str(project), "status", "--porcelain"], capture_output=True, text=True).stdout == before
