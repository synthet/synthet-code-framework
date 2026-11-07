"""Installed skills must not carry false credential hits, dead links or nested skill copies."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import agent_setup as setup


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def skill(root: Path, name: str, body: str = "Body.") -> Path:
    return write(root / ".claude/skills" / name / "SKILL.md", f"---\nname: {name}\ndescription: Demo\n---\n\n{body}\n").parent


@pytest.mark.parametrize("text", ["ask-before-touching-shared-state", "mask-automation-feasibility", "task-runner-configuration-file", "disk-usage-and-cleanup-report"])
def test_credential_patterns_ignore_words_that_contain_the_prefix(text):
    assert setup.CREDENTIAL_DATA.search(text) is None
    assert setup.SECRET.search(text) is None


@pytest.mark.parametrize("prefix", ["", "key=", '"', " ", "("])
def test_credential_patterns_still_match_real_shapes(prefix):
    value = prefix + "sk-" + "a1b2c3d4" * 4
    assert setup.CREDENTIAL_DATA.search(value)
    assert setup.SECRET.search(value)


def test_bundle_rejects_a_real_credential_but_not_a_word(tmp_path):
    fine = skill(tmp_path, "fine", "Always ask-before-touching-shared-state.")
    assert "SKILL.md" in setup.skill_bundle(tmp_path, "fine", fine)
    bad = skill(tmp_path, "bad", "Use sk-" + "a1b2c3d4" * 4)
    with pytest.raises(ValueError, match="credential pattern"):
        setup.skill_bundle(tmp_path, "bad", bad)


def test_sibling_skill_links_stay_links_and_are_not_copied(tmp_path):
    skill(tmp_path, "other")
    source = skill(tmp_path, "main", "See [other](../other/SKILL.md).")
    files = setup.skill_bundle(tmp_path, "main", source)
    assert "](../other/SKILL.md)" in files["SKILL.md"].decode()
    assert not [name for name in files if name.endswith("/SKILL.md")]


def test_repository_files_are_still_bundled_for_installed_skills(tmp_path):
    write(tmp_path / ".agent/SAFETY.md", "Rules.\n")
    source = skill(tmp_path, "main", "See [safety](../../../.agent/SAFETY.md).")
    files = setup.skill_bundle(tmp_path, "main", source)
    assert "references/shared/.agent/SAFETY.md" in files
    assert "](references/shared/.agent/SAFETY.md)" in files["SKILL.md"].decode()


def test_links_that_resolve_nowhere_keep_only_their_label(tmp_path):
    source = skill(tmp_path, "main", "Read [the guide](../../AGENTS.md#setup) and [web](https://example.com).")
    text = setup.skill_bundle(tmp_path, "main", source)["SKILL.md"].decode()
    assert "Read the guide and [web](https://example.com)." in text


def test_bundled_repository_docs_lose_their_own_dead_links(tmp_path):
    write(tmp_path / ".agent/GUIDE.md", "See [peer](./PEER.md), [code](../scripts/x.py) and [site](https://example.com).\n")
    source = skill(tmp_path, "main", "Read [guide](../../../.agent/GUIDE.md).")
    text = setup.skill_bundle(tmp_path, "main", source)["references/shared/.agent/GUIDE.md"].decode()
    assert "See peer, code and [site](https://example.com)." in text


def test_bare_links_to_files_outside_the_bundle_are_dropped(tmp_path):
    source = skill(tmp_path, "main", "Edit [config](.mcp.json), keep [local](references/a.md#top).")
    write(source / "references/a.md", "Text.\n")
    text = setup.skill_bundle(tmp_path, "main", source)["SKILL.md"].decode()
    assert "Edit config, keep [local](references/a.md#top)." in text


def test_links_inside_code_fences_are_left_alone(tmp_path):
    source = skill(tmp_path, "main", "```md\n[example](missing.md)\n```\n")
    assert "[example](missing.md)" in setup.skill_bundle(tmp_path, "main", source)["SKILL.md"].decode()


def test_a_skill_outside_the_framework_keeps_its_links_untouched(tmp_path):
    outside = tmp_path / "private"
    source = skill(outside, "local", "See [note](../../notes.md).")
    text = setup.skill_bundle(tmp_path / "framework", "local", source)["SKILL.md"].decode()
    assert "[note](../../notes.md)" in text


def alias_text(tmp_path: Path, name: str, commands: dict[str, str]) -> str:
    sources = {stem: write(tmp_path / ".claude/commands" / f"{stem}.md", f"---\ndescription: D\n---\n\n{body}\n") for stem, body in commands.items()}
    result = setup.native_assets(tmp_path, {}, sources, {}, {}, global_scope=True)
    return result[f".claude/skills/framework-{name}/SKILL.md"].decode()


def test_aliases_point_at_installed_siblings_instead_of_command_paths(tmp_path):
    text = alias_text(tmp_path, "mine", {"mine": "Use [eval](../skills/eval/SKILL.md) then [spec](spec.md#top).", "spec": "Spec."})
    assert "[eval](../eval/SKILL.md)" in text
    assert "[spec](../framework-spec/SKILL.md#top)" in text


def test_aliases_drop_links_that_only_exist_in_the_source_repository(tmp_path):
    text = alias_text(tmp_path, "mine", {"mine": "See [rules](../rules/karpathy-coding.md), [list](../skills/) and [inv](../../.agent/SKILL_INVENTORY.md)."})
    assert "See rules, list and inv." in text


def test_the_command_file_itself_keeps_its_original_links(tmp_path):
    source = write(tmp_path / ".claude/commands/mine.md", "---\ndescription: D\n---\n\nUse [eval](../skills/eval/SKILL.md).\n")
    result = setup.native_assets(tmp_path, {}, {"mine": source}, {}, {}, global_scope=True)
    assert "](../skills/eval/SKILL.md)" in result[".claude/commands/mine.md"].decode()


def framework(tmp_path: Path) -> Path:
    root = tmp_path / "framework"
    skill(root, "demo")
    write(root / ".agent/setup/library.json", json.dumps({"skills": [{"id": "demo", "source": ".claude/skills/demo", "pack": "global", "global": True, "projects": []}]}))
    write(root / ".agent/setup/global-instructions.md", "Use project instructions.\n")
    return root


def overlay_manifest(tmp_path: Path, name: str = "extra") -> Path:
    skill(tmp_path / "private", name)
    return write(tmp_path / "private/overlay.json", json.dumps({"skills": [{"id": name, "source": f".claude/skills/{name}"}]}))


def plan_targets(plan: dict) -> set[str]:
    return {Path(op["path"]).as_posix() for op in plan["operations"]}


def test_overlay_installs_extra_skills_at_user_level_only(tmp_path):
    root, manifest = framework(tmp_path), overlay_manifest(tmp_path)
    projects, user, state = tmp_path / "projects", tmp_path / "user", tmp_path / "state"
    write(projects / "repo/pyproject.toml", '[project]\nname="repo"\n')
    user.mkdir()
    plan = setup.build_plan(root, projects, user, state, overlay=manifest)
    hits = [p for p in plan_targets(plan) if "/extra/" in p]
    assert any(p.endswith(".claude/skills/extra/SKILL.md") for p in hits)
    assert hits and all("/user/" in p for p in hits)


def test_plans_without_an_overlay_do_not_mention_it(tmp_path):
    root = framework(tmp_path)
    overlay_manifest(tmp_path)
    (tmp_path / "user").mkdir()
    (tmp_path / "projects").mkdir()
    plan = setup.build_plan(root, tmp_path / "projects", tmp_path / "user", tmp_path / "state")
    assert not [p for p in plan_targets(plan) if "/extra/" in p]


def test_overlay_cannot_replace_a_library_skill(tmp_path):
    root, manifest = framework(tmp_path), overlay_manifest(tmp_path, "demo")
    (tmp_path / "user").mkdir()
    with pytest.raises(ValueError, match="overlay skill collides"):
        setup.build_plan(root, tmp_path / "projects", tmp_path / "user", tmp_path / "state", overlay=manifest)


def test_overlay_source_must_stay_beside_its_manifest(tmp_path):
    root = framework(tmp_path)
    manifest = write(tmp_path / "private/overlay.json", json.dumps({"skills": [{"id": "escape", "source": "../outside"}]}))
    skill(tmp_path / "outside", "escape")
    (tmp_path / "user").mkdir()
    with pytest.raises(ValueError, match="overlay source"):
        setup.build_plan(root, tmp_path / "projects", tmp_path / "user", tmp_path / "state", overlay=manifest)


def installed(tmp_path: Path, extra: str = "references/old.md"):
    root = framework(tmp_path)
    write(root / ".claude/skills/demo" / extra, "Old.")
    projects, user, state = tmp_path / "projects", tmp_path / "user", tmp_path / "state"
    projects.mkdir()
    user.mkdir()
    plan = setup.build_plan(root, projects, user, state)
    run = setup.apply_operations(plan["operations"], state, [projects, user])
    setup.save_ownership(state, run, user)
    (root / ".claude/skills/demo" / extra).unlink()
    return root, projects, user, state


def deletes(plan: dict) -> set[str]:
    return {op["relative"] for op in plan["operations"] if op["action"] == "delete"}


def test_files_a_skill_no_longer_ships_are_removed_from_every_tree(tmp_path):
    root, projects, user, state = installed(tmp_path)
    found = deletes(setup.build_plan(root, projects, user, state))
    assert ".claude/skills/demo/references/old.md" in found
    assert ".agents/skills/demo/references/old.md" in found
    assert not [name for name in found if name.endswith("SKILL.md")]


def test_an_edited_leftover_is_kept(tmp_path):
    root, projects, user, state = installed(tmp_path)
    (user / ".claude/skills/demo/references/old.md").write_text("My notes.", encoding="utf-8")
    found = deletes(setup.build_plan(root, projects, user, state))
    assert ".claude/skills/demo/references/old.md" not in found
    assert ".agents/skills/demo/references/old.md" in found


def test_a_file_the_installer_never_wrote_is_kept(tmp_path):
    root, projects, user, state = installed(tmp_path)
    write(user / ".claude/skills/demo/references/mine.md", "Mine.")
    assert ".claude/skills/demo/references/mine.md" not in deletes(setup.build_plan(root, projects, user, state))


def test_a_stale_file_delete_applies_and_rolls_back(tmp_path):
    root, projects, user, state = installed(tmp_path)
    target = user / ".claude/skills/demo/references/old.md"
    plan = setup.build_plan(root, projects, user, state)
    run = setup.apply_operations(plan["operations"], state, [projects, user])
    assert not target.exists()
    setup.rollback(run, [user, projects])
    assert target.exists()
