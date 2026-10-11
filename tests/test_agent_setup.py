"""Behavior tests for inventory and reversible multi-harness installation."""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import agent_setup as setup


def test_frontmatter_does_not_read_embedded_examples():
    text = '---\nname: real\ndescription: |\n  First line\n  Second line\n---\nname: fake\n'
    assert setup.frontmatter(text) == {"name": "real", "description": "First line Second line"}


def test_inventory_redacts_secrets_and_reports_read_failures(tmp_path):
    repo = tmp_path / "projects" / "demo"
    repo.mkdir(parents=True)
    (repo / "package.json").write_text('{}')
    (repo / ".mcp.json").write_text(json.dumps({"mcpServers": {"test": {"env": {"API_KEY": "private-value"}}}}))
    (repo / ".env").write_text('SECRET=do-not-collect')
    (repo / '.cursor/scripts').mkdir(parents=True)
    (repo / '.cursor/scripts/server.cmd').write_text('@node server.js')
    report = setup.inventory(tmp_path / "projects", tmp_path / "user")
    serialized = json.dumps(report)
    assert "private-value" not in serialized
    assert "do-not-collect" not in serialized
    assert report["projects"][0]["eligible"]
    assert report["assets"][0]["config"]["servers"] == ["test"]
    assert any(asset['relative'] == '.cursor/scripts/server.cmd' for asset in report['assets'])


def test_ownership_not_inferred_from_existing_agent_files(tmp_path):
    root = tmp_path / "projects"
    for name, owner in [("fork", "synthet"), ("vendor", "someone")]:
        repo = root / name
        (repo / ".git").mkdir(parents=True)
        (repo / ".git" / "config").write_text(f'[remote "origin"]\n url = https://github.com/{owner}/tool.git\n')
        (repo / "AGENTS.md").write_text("Existing instructions")
    (root / "_backup" / "copy").mkdir(parents=True)
    (root / "_backup" / "copy" / "AGENTS.md").write_text("Backup")
    report = setup.inventory(root, tmp_path / "user")
    projects = {p["name"]: p for p in report["projects"]}
    assert projects["fork"]["eligible"]
    assert not projects["vendor"]["eligible"]
    assert not projects["_backup"]["eligible"]
    assert any(Path(a["path"]).as_posix().endswith("copy/AGENTS.md") for a in report["assets"])


def test_native_adapters_translate_rules_and_do_not_invent_model_names():
    rule = '---\ndescription: Python rules\nglobs: "*.py"\nalwaysApply: false\n---\nValidate input.\n'
    converted = setup.antigravity_rule(rule)
    assert "trigger: glob" in converted
    assert 'globs: "*.py"' in converted
    agent = '---\nname: reviewer\ndescription: Review code\nmodel: opus\n---\nCheck correctness.\n'
    assert "opus" not in setup.antigravity_agent(agent)
    assert "inherit" in setup.antigravity_agent(agent)


def test_rule_adapters_preserve_conditional_scope(tmp_path):
    rule = tmp_path / '.cursor/rules/python.mdc'
    rule.parent.mkdir(parents=True)
    rule.write_text('---\ndescription: Python\nglobs:\n  - "**/*.py"\n  - "**/*.pyi"\nalwaysApply: false\n---\nCheck types.\n')
    files = setup.native_assets(tmp_path, {}, {}, {}, {'python': rule})
    assert b'paths: ["**/*.py", "**/*.pyi"]' in files['.claude/rules/python.md']
    assert b'globs: "**/*.py,**/*.pyi"' in files['.agents/rules/python.md']
    rule.write_text('---\ndescription: Optional review\nalwaysApply: false\n---\nReview on request.\n')
    files = setup.native_assets(tmp_path, {}, {}, {}, {'python': rule})
    assert '.claude/rules/python.md' not in files
    assert b'disable-model-invocation: true' in files['.claude/skills/project-rule-python/SKILL.md']


def test_mcp_conversion_does_not_copy_literal_credentials():
    source = {"command": "node", "args": ["server.js"], "env": {"API_KEY": "secret-value", "MODE": "read"}}
    converted, issues = setup.convert_server(source, "codex")
    assert "secret-value" not in json.dumps(converted)
    assert "API_KEY" in converted["env_vars"]
    assert issues


def test_toml_merge_preserves_unrelated_tables_and_adds_only_missing_servers():
    existing = 'model = "my-model"\n[mcp_servers.existing]\ncommand = "tool"\n'
    converted = setup.add_toml_servers(existing, {"existing": {"command": "other"}, "new": {"command": "new-tool"}})
    import tomllib
    parsed = tomllib.loads(converted)
    assert parsed["model"] == "my-model"
    assert parsed["mcp_servers"]["existing"]["command"] == "tool"
    assert parsed["mcp_servers"]["new"]["command"] == "new-tool"


def test_merge_preserves_independent_user_edit_and_rejects_overlap():
    base = "one\ntwo\nthree\n"
    assert setup.merge_text(base, "ONE\ntwo\nthree\n", "one\ntwo\nTHREE\n") == "ONE\ntwo\nTHREE\n"
    assert setup.merge_text(base, "one\nTWO\nthree\n", "one\nSECOND\nthree\n") is None


def test_owned_local_edit_does_not_create_repeated_noop_updates(tmp_path):
    (tmp_path / 'notes.md').write_bytes(b'User customization\n')
    owned = {'notes.md': {'content': base64.b64encode(b'Original\n').decode()}}
    op = setup.plan_files(tmp_path, {'notes.md': b'Original\n'}, owned)[0]
    assert op['action'] == 'unchanged'
    assert base64.b64decode(op['content']) == b'User customization\n'


def test_plan_preserves_unmanaged_conflicting_files(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    (root / "notes.md").write_text("User content\n")
    ops = setup.plan_files(root, {"notes.md": b"Generated\n", "new.md": b"New\n"}, {})
    assert {x["action"] for x in ops} == {"conflict", "create"}
    assert (root / "notes.md").read_text() == "User content\n"


def test_apply_check_and_rollback_are_reversible(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    ops = setup.plan_files(root, {"new.md": b"New\n"}, {})
    run = setup.apply_operations(ops, tmp_path / "state", [root])
    assert (root / "new.md").read_text() == "New\n"
    assert setup.check_run(run)["ok"]
    assert setup.rollback(run, [root])["ok"]
    assert not (root / "new.md").exists()


def test_apply_rechecks_content_before_overwriting(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    f = root / "new.md"
    ops = setup.plan_files(root, {"new.md": b"New\n"}, {})
    f.write_text("Changed after planning\n")
    run = setup.apply_operations(ops, tmp_path / "state", [root])
    assert f.read_text() == "Changed after planning\n"
    assert json.loads(run.read_text())["conflicts"]


def test_live_claude_state_merges_only_reviewed_new_servers(tmp_path):
    source = tmp_path / '.claude.json'
    source.write_text(json.dumps({'cached_state': 1, 'mcpServers': {}}))
    planned = setup.plan_files(tmp_path, {'.claude.json': json.dumps({'cached_state': 1, 'mcpServers': {'jev': {'command': 'verified'}}}).encode()}, {}, {'.claude.json'})
    source.write_text(json.dumps({'cached_state': 2, 'auth': 'existing', 'mcpServers': {'user': {'command': 'user'}}}))
    run = setup.apply_operations(planned, tmp_path / 'state', [tmp_path])
    actual = json.loads(source.read_text())
    assert actual['cached_state'] == 2 and actual['auth'] == 'existing'
    assert set(actual['mcpServers']) == {'user', 'jev'}
    assert setup.check_run(run)['ok']
    assert setup.rollback(run, [tmp_path])['ok']
    assert json.loads(source.read_text())['cached_state'] == 2


def test_concurrent_config_merge_refuses_permission_changes(tmp_path):
    source = tmp_path / '.claude.json'
    source.write_text(json.dumps({'permissions': ['Read']}))
    plan = setup.plan_files(tmp_path, {'.claude.json': json.dumps({'permissions': ['Write']}).encode()}, {}, {'.claude.json'})
    assert setup.concurrent_config_merge(plan[0], b'{"permissions": ["Read"], "state": 2}') is None


def test_receipt_checks_registration_while_live_caches_change(tmp_path):
    source = tmp_path / '.claude.json'
    wanted = json.dumps({'mcpServers': {'jev': {'command': 'verified'}}, 'cache': 1}).encode()
    receipt = setup.apply_operations(setup.plan_files(tmp_path, {'.claude.json': wanted}, {}), tmp_path / 'state', [tmp_path])
    source.write_text(json.dumps({'mcpServers': {'jev': {'command': 'verified'}}, 'cache': 2}))
    check = setup.check_run(receipt)
    assert check['ok'] and check['live_state_changes'] == [str(source)]
    source.write_text(json.dumps({'mcpServers': {'jev': {'command': 'changed'}}, 'cache': 2}))
    assert not setup.check_run(receipt)['ok']


def test_rollback_refuses_later_edits_and_outside_targets(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    run = setup.apply_operations(setup.plan_files(root, {"new.md": b"New\n"}, {}), tmp_path / "state", [root])
    (root / "new.md").write_text("Later work\n")
    assert not setup.rollback(run, [root])["ok"]
    assert (root / "new.md").read_text() == "Later work\n"
    with pytest.raises(ValueError):
        setup.apply_operations(setup.plan_files(tmp_path, {"outside.md": b"No"}, {}), tmp_path / "state", [root])


def test_json_merge_keeps_existing_permissions_and_auth():
    current = {"permissions": {"allow": ["Read"]}, "auth": "private", "mcpServers": {"user": {"command": "user-tool"}}}
    result = setup.merge_json(current, {"mcpServers": {"new": {"command": "new-tool"}}})
    assert result["permissions"] == current["permissions"]
    assert result["auth"] == "private"
    assert result["mcpServers"]["user"] == current["mcpServers"]["user"]


def test_mcp_noop_preserves_live_native_json_format(tmp_path):
    original = b'{"cache":2,"mcpServers":{}}\n'
    (tmp_path / '.claude.json').write_bytes(original)
    files, diagnostics, _ = setup.mcp_files(tmp_path, global_scope=True)
    assert files['.claude.json'] == original
    assert not diagnostics


def test_equivalent_line_endings_are_preserved(tmp_path):
    (tmp_path / 'notes.md').write_bytes(b'Text\r\n')
    plan = setup.plan_files(tmp_path, {'notes.md': b'Text\n'}, {})
    assert plan[0]['action'] == 'unchanged'
    assert base64.b64decode(plan[0]['content']) == b'Text\r\n'


def test_project_instructions_preserve_existing_contract(tmp_path):
    repo = tmp_path / "demo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# My project\n\nNever change the database directly.\n")
    files = setup.project_instructions(repo, {"name": "demo", "commands": {"TEST_CMD": "npm test"}}, [])
    assert b"Never change the database directly." in files["AGENTS.md"]
    assert b"npm test" in files["AGENTS.md"]
    assert files["CLAUDE.md"] == b"@AGENTS.md\n"
    assert b"AGENTS.md" in files["GEMINI.md"]


def test_portable_core_harness_runs_outside_framework(tmp_path):
    framework = Path(__file__).resolve().parents[1]
    files = setup.skill_bundle(framework, "search-tool-selection")
    installed = tmp_path / "user" / "skills" / "search-tool-selection"
    for rel, data in files.items():
        f = installed / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
    proc = subprocess.run([sys.executable, str(installed / "scripts/harness.py"), "--task-type", "config", "--json"], cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["task_type"] == "config"


def test_packaging_a_previously_installed_runtime_is_stable(tmp_path):
    framework = Path(__file__).resolve().parents[1]
    files = setup.skill_bundle(framework, 'search-tool-selection')
    installed = tmp_path / '.claude/skills/search-tool-selection'
    for rel, data in files.items():
        path = installed / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    repeated = setup.skill_bundle(framework, 'search-tool-selection', installed)
    assert set(repeated) == set(files)
    assert not any(path.count('_runtime') > 1 for path in repeated)


def test_native_skill_name_normalization_preserves_workflow(tmp_path):
    source = tmp_path / 'legacy'
    source.mkdir()
    (source / 'SKILL.md').write_text('---\nname: old-name\ndescription: Project MCP workflow\n---\n# Existing project title\nCall the documented tools.\n')
    bundle = setup.skill_bundle(tmp_path, 'legacy', source)
    assert setup.frontmatter(bundle['SKILL.md'].decode())['name'] == 'legacy'
    assert '# Existing project title\nCall the documented tools.' in setup.body(bundle['SKILL.md'].decode())


def test_memory_helpers_are_portable_and_use_target_workspace(tmp_path):
    framework = Path(__file__).resolve().parents[1]
    installed = tmp_path / "installed"
    for rel, data in setup.skill_bundle(framework, "agent-memory").items():
        f = installed / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
    target = tmp_path / "target"
    (target / ".agent-memory").mkdir(parents=True)
    (target / ".agent-memory/memory.md").write_text("# Memory\nTarget context\n")
    proc = subprocess.run([sys.executable, str(installed / "scripts/agent-memory/context.py"), "--repo-root", str(target)], cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "Target context" in proc.stdout


def test_mcp_inherited_environment_transfers_without_values():
    output, issues = setup.convert_server({"command": "tool", "env_vars": ["ACCESS_TOKEN"]}, "claude")
    assert output["env"] == {"ACCESS_TOKEN": "${ACCESS_TOKEN}"}
    assert not issues
    output, issues = setup.convert_server({"url": "https://user:password@example.com/mcp?token=private"}, "codex")
    assert "url" not in output
    assert issues
    remote, issues = setup.convert_server({'url': 'https://example.com/mcp', 'bearer_token_env_var': 'ACCESS_TOKEN'}, 'claude')
    assert remote['type'] == 'http'
    assert remote['headers']['Authorization'] == 'Bearer ${ACCESS_TOKEN}'
    assert 'bearer_token_env_var' not in remote
    cursor, issues = setup.convert_server({'command': 'tool', 'env': {'ACCESS_TOKEN': '${ACCESS_TOKEN}'}}, 'cursor')
    assert cursor['type'] == 'stdio'
    assert cursor['env']['ACCESS_TOKEN'] == '${env:ACCESS_TOKEN}'


def test_interrupted_journal_supports_rollback(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    run = setup.apply_operations(setup.plan_files(root, {"new.md": b"New"}, {}), tmp_path / "state", [root])
    receipt = json.loads(run.read_text())
    receipt["complete"] = False
    receipt["writes"] = []
    run.write_text(json.dumps(receipt))
    assert setup.rollback(run, [root])["ok"]
    assert not (root / "new.md").exists()


def test_audit_excludes_vendor_and_counts_ast_functions(tmp_path):
    path = Path(__file__).resolve().parents[1] / ".claude/skills/codebase-size-audit/scripts/audit.py"
    (tmp_path / "large.py").write_text("def big():\n" + "    pass\n" * 10)
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules/large.py").write_text("pass\n" * 100)
    proc = subprocess.run([sys.executable, str(path), "--root", str(tmp_path), "--file-lines", "5", "--function-lines", "5"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert [x["path"] for x in data["files"]] == ["large.py"]
    assert data["functions"][0]["name"] == "big"


def test_plan_apply_is_idempotent_and_updates_owned_library(tmp_path):
    framework = tmp_path / "framework"
    source = framework / ".claude/skills/demo/SKILL.md"
    source.parent.mkdir(parents=True)
    source.write_text('---\nname: demo\ndescription: Demo\n---\n\nOriginal workflow\n')
    commands = framework / ".claude/commands"
    commands.mkdir()
    (commands / "spec.md").write_text('---\ndescription: Spec\n---\n\nDraft a specification.\n')
    catalog = framework / ".agent/setup/library.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(json.dumps({'skills': [{'id': 'demo', 'source': '.claude/skills/demo', 'pack': 'core'}]}))
    (catalog.parent / "global-instructions.md").write_text('Use project instructions.\n')
    projects = tmp_path / "projects"
    target = projects / "maintained"
    target.mkdir(parents=True)
    (target / "pyproject.toml").write_text('[project]\nname="maintained"\n')
    user = tmp_path / "user"
    user.mkdir()
    state = tmp_path / "state"
    plan = setup.build_plan(framework, projects, user, state)
    run = setup.apply_operations(plan['operations'], state, [projects, user])
    assert setup.check_run(run)['ok']
    for root in plan['targets']:
        setup.save_ownership(state, run, Path(root))
    repeat = setup.build_plan(framework, projects, user, state)
    assert repeat['summary']['create'] == repeat['summary']['update'] == repeat['summary']['conflict'] == 0
    source.write_text('---\nname: demo\ndescription: Demo\n---\n\nImproved workflow\n')
    update = setup.build_plan(framework, projects, user, state)
    changed = [op for op in update['operations'] if op['action'] == 'update']
    assert any(op['relative'] == '.claude/skills/demo/SKILL.md' for op in changed)
    assert any(op['relative'] == '.agents/skills/demo/SKILL.md' for op in changed)


def test_equal_skill_text_with_specialized_resources_is_not_disabled(tmp_path):
    framework, projects, user, state = [tmp_path / name for name in ['framework', 'projects', 'user', 'state']]
    source = framework / '.claude/skills/demo'
    (source / 'references/rules').mkdir(parents=True)
    (source / 'SKILL.md').write_text('---\nname: demo\ndescription: Demo\n---\nUse bundled guidance.\n')
    (source / 'references/rules/guide.md').write_text('Generic guidance\n')
    catalog = framework / '.agent/setup'
    catalog.mkdir(parents=True)
    (catalog / 'library.json').write_text(json.dumps({'skills': [{'id': 'demo', 'source': '.claude/skills/demo', 'pack': 'core'}]}))
    (catalog / 'global-instructions.md').write_text('Respect project contracts.\n')
    repo = projects / 'demo'
    repo.mkdir(parents=True)
    (repo / 'pyproject.toml').write_text('[project]\nname="demo"\n')
    user.mkdir()
    for rel, data in setup.skill_bundle(framework, 'demo').items():
        destination = repo / '.claude/skills/demo' / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (repo / '.claude/skills/demo/references/rules/guide.md').write_text('Specialized project guidance\n')
    plan = setup.build_plan(framework, projects, user, state)
    config = next(op for op in plan['operations'] if op['path'] == str(user / '.codex/config.toml'))
    assert str(repo / '.agents/skills/demo/SKILL.md') not in base64.b64decode(config['content']).decode()
    assert any(op['path'] == str(user / '.agents/skills/demo/references/rules/guide.md') for op in plan['operations'])


def test_delete_is_receipted_and_rollback_preserves_later_work(tmp_path):
    target = tmp_path / 'target'
    target.mkdir()
    path = target / 'stale.md'
    path.write_bytes(b'Original')
    operation = {'path': str(path), 'relative': 'stale.md', 'action': 'delete',
                 'before_sha256': setup.digest(b'Original'), 'after_sha256': None,
                 'content': '', 'before_content': None}
    receipt = setup.apply_operations([operation], tmp_path / 'state', [target])
    assert not path.exists() and setup.check_run(receipt)['ok']
    setup.save_ownership(tmp_path / 'state', receipt, target)
    assert 'stale.md' not in setup.owned_files(tmp_path / 'state', target)
    assert setup.rollback(receipt, [target])['ok']
    assert path.read_bytes() == b'Original'
    path.write_bytes(b'Later work')
    assert not setup.rollback(receipt, [target])['ok']
    assert path.read_bytes() == b'Later work'


@pytest.mark.parametrize('canonical', ['.claude', '.cursor'])
def test_reviewed_project_generator_runs_only_in_staging(tmp_path, canonical):
    project = tmp_path / 'project'
    script = project / 'scripts/sync_assistant_trees.py'
    script.parent.mkdir(parents=True)
    code = '''from pathlib import Path
import shutil
ROOT = Path(__file__).resolve().parents[1]
def sync(check=False):
    dest = ROOT / '.cursor/skills'
    if dest.exists(): shutil.rmtree(dest)
    shutil.copytree(ROOT / '.claude/skills', dest)
    return 0
def sync_cursor_to_claude(check=False):
    dest = ROOT / '.claude/skills'
    if dest.exists(): shutil.rmtree(dest)
    shutil.copytree(ROOT / '.cursor/skills', dest)
    return 0
'''
    script.write_bytes(code.replace('\n', '\r\n').encode())
    original = script.read_bytes()
    skill = project / canonical / 'skills/demo/SKILL.md'
    skill.parent.mkdir(parents=True)
    skill.write_bytes(b'Local workflow')
    files = {'.claude/skills/demo/SKILL.md': b'Portable local workflow'}
    contract = {'sha256': setup.digest(original), 'canonical': canonical}
    adopt, deleted, _ = setup.project_sync_contract(project, files, contract, {}, tmp_path / 'state')
    assert files['.cursor/skills/demo/SKILL.md'] == files['.claude/skills/demo/SKILL.md'] == b'Portable local workflow'
    assert '.cursor/skills/demo/SKILL.md' in adopt and not deleted
    assert skill.read_bytes() == b'Local workflow' and script.read_bytes() == original
    script.write_bytes(files['scripts/sync_assistant_trees.py'])
    baseline = {'scripts/sync_assistant_trees.py': {'sha256': setup.digest(script.read_bytes())}}
    repeated = dict(files)
    setup.project_sync_contract(project, repeated, contract, baseline, tmp_path / 'state')
    assert repeated == files
    script.write_bytes(b'unreviewed changes')
    with pytest.raises(ValueError, match='unreviewed'):
        setup.project_sync_contract(project, files, contract, {}, tmp_path / 'state')
