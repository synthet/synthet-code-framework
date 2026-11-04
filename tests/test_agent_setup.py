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
    files = setup.project_instructions(repo, {"name": "demo", "commands": {"TEST_CMD": "npm test"}})
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


def _tier_workspace(tmp_path, repo_name='maintained', git=True):
    """Install one library skill everywhere, leaving a ledger to prune from."""
    framework, projects, user, state = [tmp_path / name for name in ['framework', 'projects', 'user', 'state']]
    source = framework / '.claude/skills/demo'
    (source / 'references').mkdir(parents=True)
    (source / 'SKILL.md').write_text('---\nname: demo\ndescription: Demo\n---\n\nShared workflow\n')
    (source / 'references/guide.md').write_text('Shared guidance\n')
    commands = framework / '.claude/commands'
    commands.mkdir()
    (commands / 'spec.md').write_text('---\ndescription: Spec\n---\n\nDraft a specification.\n')
    catalog = framework / '.agent/setup'
    catalog.mkdir(parents=True)
    (catalog / 'global-instructions.md').write_text('Use project instructions.\n')
    repo = projects / repo_name
    repo.mkdir(parents=True)
    (repo / 'pyproject.toml').write_text('[project]\nname="maintained"\n')
    if git:
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    user.mkdir()
    _catalog(framework, 'core', True, [])
    plan = setup.build_plan(framework, projects, user, state)
    _apply(plan, state, projects, user)
    return framework, projects, user, state, repo


def _catalog(framework, pack, is_global, projects):
    (framework / '.agent/setup/library.json').write_text(json.dumps({'skills': [
        {'id': 'demo', 'source': '.claude/skills/demo', 'pack': pack, 'global': is_global, 'projects': projects}]}))


def _apply(plan, state, projects, user):
    run = setup.apply_operations(plan['operations'], state, [projects, user])
    assert setup.check_run(run)['ok']
    for root in plan['targets']:
        setup.save_ownership(state, run, Path(root))
    return run


def _deleted(plan, root=None):
    return {op['relative'] for op in plan['operations']
            if op['action'] == 'delete' and (root is None or Path(op['path']).is_relative_to(root))}


def _tier_diagnostics(plan, kind):
    return {item['skill']: item['reason'] for item in plan['diagnostics'] if item.get('kind') == kind}


def test_lean_tier_prunes_unmodified_bundle_and_keeps_global_copy(tmp_path):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    _catalog(framework, 'global', True, [])
    cache = repo / '.claude/skills/demo/__pycache__/x.pyc'
    cache.parent.mkdir()
    cache.write_bytes(b'cache')
    plan = setup.build_plan(framework, projects, user, state)
    assert {'.claude/skills/demo/SKILL.md', '.claude/skills/demo/references/guide.md',
            '.claude/skills/demo/__pycache__/x.pyc', '.agents/skills/demo/SKILL.md'} <= _deleted(plan, repo)
    assert not _tier_diagnostics(plan, 'tier-collision')
    assert plan['summary']['delete'] == len(_deleted(plan))
    run = _apply(plan, state, projects, user)
    assert not (repo / '.claude/skills/demo').exists() and not (repo / '.agents/skills/demo').exists()
    assert (repo / '.claude/skills').is_dir()
    assert (user / '.claude/skills/demo/SKILL.md').is_file()
    # The copy is gone, so the next plan drops its Codex disable entry and settles.
    cleanup = setup.build_plan(framework, projects, user, state)
    assert [op['relative'] for op in cleanup['operations'] if op['action'] != 'unchanged'] == ['.codex/config.toml']
    _apply(cleanup, state, projects, user)
    repeat = setup.build_plan(framework, projects, user, state)
    assert not any(repeat['summary'][action] for action in ['create', 'update', 'delete', 'conflict'])
    assert setup.rollback(run, [projects, user])['ok']
    assert (repo / '.claude/skills/demo/references/guide.md').read_text() == 'Shared guidance\n'


@pytest.mark.parametrize('case, reason', [('edited', 'edited'), ('unowned', 'unowned'), ('referenced', 'referenced'), ('protected', 'protected')])
def test_prune_keeps_the_whole_bundle_when_a_guard_fails(tmp_path, case, reason):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    _catalog(framework, 'global', True, [])
    skill = repo / '.claude/skills/demo'
    if case == 'edited':
        (skill / 'references/guide.md').write_text('Project guidance\n')
    elif case == 'unowned':
        (skill / 'notes.md').write_text('Project notes\n')
    elif case == 'protected':
        (skill / 'config.json').write_text('{}\n')
    else:
        (repo / 'README.md').write_text('Run .claude/skills/demo/scripts/run.py\n')
        subprocess.run(['git', '-C', str(repo), 'add', 'README.md'], check=True)
    plan = setup.build_plan(framework, projects, user, state)
    assert not any(rel.startswith('.claude/skills/demo/') for rel in _deleted(plan, repo))
    assert reason in _tier_diagnostics(plan, 'tier-collision')['demo']
    assert plan['summary']['tier_collisions'] == 1
    assert (skill / 'SKILL.md').is_file()


def test_blocked_copy_in_one_tree_keeps_the_skill_in_every_tree(tmp_path):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    _catalog(framework, 'global', True, [])
    (repo / '.agents/skills/demo/references/guide.md').write_text('Project guidance\n')
    plan = setup.build_plan(framework, projects, user, state)
    assert not any('skills/demo/' in rel for rel in _deleted(plan, repo))
    assert 'edited' in _tier_diagnostics(plan, 'tier-collision')['demo']


def test_references_from_other_retiring_copies_do_not_block_pruning(tmp_path):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    _catalog(framework, 'global', True, [])
    mirror = repo / '.agents/skills/demo/references/guide.md'
    original = (repo / '.claude/skills/demo/SKILL.md').read_bytes()
    subprocess.run(['git', '-C', str(repo), 'add', '.claude/skills', '.agents/skills'], check=True)
    assert mirror.is_file() and original
    plan = setup.build_plan(framework, projects, user, state)
    assert '.claude/skills/demo/SKILL.md' in _deleted(plan, repo)


def test_prune_requires_a_ledger_and_git(tmp_path):
    framework, projects, user, state, repo = _tier_workspace(tmp_path / 'nogit', git=False)
    _catalog(framework, 'global', True, [])
    plan = setup.build_plan(framework, projects, user, state)
    assert not _deleted(plan, repo)
    assert 'Git' in _tier_diagnostics(plan, 'tier-collision')['demo']

    framework, projects, user, state, repo = _tier_workspace(tmp_path / 'noledger')
    _catalog(framework, 'global', True, [])
    for manifest in (state / 'targets').glob('*.json'):
        if Path(json.loads(manifest.read_text())['root']) == repo:
            manifest.unlink()
    plan = setup.build_plan(framework, projects, user, state)
    assert not _deleted(plan, repo)
    assert 'ledger' in _tier_diagnostics(plan, 'tier-collision')['demo']


def test_stack_pack_installs_only_where_opted_in_and_leaves_global(tmp_path):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    other = projects / 'other'
    other.mkdir()
    (other / 'pyproject.toml').write_text('[project]\nname="other"\n')
    _catalog(framework, 'rust', False, ['maintained'])
    plan = setup.build_plan(framework, projects, user, state)
    assert '.claude/skills/demo/SKILL.md' in _deleted(plan, user)
    assert '.agents/skills/demo/SKILL.md' in _deleted(plan, user)
    assert not _deleted(plan, repo) and (repo / '.claude/skills/demo/SKILL.md').is_file()
    assert not any(Path(op['path']).is_relative_to(other / '.claude/skills/demo') for op in plan['operations'])


def test_kept_project_skill_with_global_name_is_a_collision(tmp_path):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    native = repo / '.claude/skills/framework-spec/SKILL.md'
    native.parent.mkdir(parents=True, exist_ok=True)
    native.write_text('---\nname: framework-spec\ndescription: Our own spec flow\n---\n\nLocal\n')
    plan = setup.build_plan(framework, projects, user, state)
    assert 'global name' in _tier_diagnostics(plan, 'tier-collision')['framework-spec']


def test_aliases_are_global_for_framework_commands_and_project_for_custom_ones(tmp_path):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    assert not (repo / '.claude/skills/framework-spec').exists()
    assert (user / '.claude/skills/framework-spec/SKILL.md').is_file()
    (repo / '.claude/commands/ship.md').write_text('---\ndescription: Ship\n---\n\nShip it our way.\n')
    plan = setup.build_plan(framework, projects, user, state)
    created = {op['relative'] for op in plan['operations'] if op['action'] == 'create'}
    assert {'.claude/skills/project-ship/SKILL.md', '.agents/skills/project-ship/SKILL.md'} <= created
    assert not any('framework-ship' in rel for rel in created)
    shared = framework / '.claude/commands/spec.md'
    repo_copy = repo / '.claude/commands/spec.md'
    assert not setup.project_command(framework, 'spec', repo_copy, shared.read_text().replace('\n', '\r\n'))
    assert setup.project_command(framework, 'spec', repo_copy, 'Our spec flow.\n')
    assert not setup.project_command(framework, 'spec', shared, 'Anything\n')
    _apply(plan, state, projects, user)
    repeat = setup.build_plan(framework, projects, user, state)
    assert not any(repeat['summary'][action] for action in ['create', 'update', 'delete', 'conflict'])


def test_generated_framework_alias_left_in_a_repo_is_pruned(tmp_path):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    alias = repo / '.claude/skills/framework-old/SKILL.md'
    alias.parent.mkdir(parents=True)
    alias.write_text('---\nname: framework-old\ndescription: "Explicit framework workflow: old"\ndisable-model-invocation: true\n---\n\nOld\n')
    ledger = next(path for path in (state / 'targets').glob('*.json') if Path(json.loads(path.read_text())['root']) == repo)
    data = json.loads(ledger.read_text())
    data['files']['.claude/skills/framework-old/SKILL.md'] = {'sha256': setup.digest(alias.read_bytes()), 'content': base64.b64encode(alias.read_bytes()).decode()}
    ledger.write_text(json.dumps(data))
    assert '.claude/skills/framework-old/SKILL.md' in _deleted(setup.build_plan(framework, projects, user, state), repo)


def test_contract_repo_does_not_resurrect_pruned_skills(tmp_path):
    project = tmp_path / 'project'
    script = project / 'scripts/sync_assistant_trees.py'
    script.parent.mkdir(parents=True)
    script.write_text('''from pathlib import Path
import shutil
ROOT = Path(__file__).resolve().parents[1]
def sync(check=False):
    dest = ROOT / '.cursor/skills'
    if dest.exists(): shutil.rmtree(dest)
    shutil.copytree(ROOT / '.claude/skills', dest)
    return 0
''')
    for name in ['demo', 'kept']:
        for tree in ['.claude', '.cursor']:
            path = project / tree / 'skills' / name / 'SKILL.md'
            path.parent.mkdir(parents=True)
            path.write_bytes(name.encode())
    contract = {'sha256': setup.digest(script.read_bytes()), 'canonical': '.claude'}
    prune = {'.claude/skills/demo/SKILL.md', '.cursor/skills/demo/SKILL.md'}
    files = {}
    _, deleted, _ = setup.project_sync_contract(project, files, contract, {}, tmp_path / 'state', prune)
    assert {op['relative'] for op in deleted} == prune
    assert '.cursor/skills/kept/SKILL.md' in files and not prune & set(files)


def test_codex_disables_drop_only_missing_project_paths(tmp_path):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    gone = str(repo / '.agents/skills/gone/SKILL.md')
    alive = repo / '.agents/skills/alive/SKILL.md'
    alive.parent.mkdir(parents=True)
    alive.write_text('---\nname: alive\ndescription: Alive\n---\n\nLocal\n')
    elsewhere = str(tmp_path / 'elsewhere/SKILL.md')
    config = user / '.codex/config.toml'
    config.parent.mkdir(exist_ok=True)
    entries = ''.join('\n[[skills.config]]\npath = ' + json.dumps(value) + '\nenabled = false\n' for value in [gone, str(alive), elsewhere])
    config.write_text('model = "keep"\n' + entries)
    plan = setup.build_plan(framework, projects, user, state)
    written = next(op for op in plan['operations'] if op['path'] == str(config))
    text = base64.b64decode(written['content']).decode()
    assert 'model = "keep"' in text and json.dumps(str(alive)) in text and json.dumps(elsewhere) in text
    assert json.dumps(gone) not in text


def test_project_instructions_describe_the_tiers(tmp_path):
    repo = tmp_path / 'demo'
    repo.mkdir()
    text = setup.project_instructions(repo, {'name': 'demo', 'commands': {}})['AGENTS.md'].decode()
    assert 'user level' in text and 'Installed library' not in text


@pytest.mark.skipif(sys.platform != 'win32', reason='NTFS junctions')
def test_junction_is_a_link_and_not_a_second_project(tmp_path):
    projects = tmp_path / 'projects'
    real = projects / 'real'
    real.mkdir(parents=True)
    (real / 'AGENTS.md').write_text('# real\n')
    subprocess.run(['cmd', '/c', 'mklink', '/J', str(projects / 'alias'), str(real)], check=True, capture_output=True)
    assert setup.linked(projects / 'alias') and not setup.linked(real)
    report = setup.inventory(projects, tmp_path / 'absent')
    assert [item['name'] for item in report['projects']] == ['real']
    assert report['aliases'][0]['path'].endswith('alias')


def _own(state, repo, path):
    ledger = next(item for item in (state / 'targets').glob('*.json') if Path(json.loads(item.read_text())['root']) == repo)
    data = json.loads(ledger.read_text())
    data['files'][path.relative_to(repo).as_posix()] = {'sha256': setup.digest(path.read_bytes()), 'content': base64.b64encode(path.read_bytes()).decode()}
    ledger.write_text(json.dumps(data))


@pytest.mark.parametrize('edited', [False, True])
def test_only_unmodified_installer_files_stop_counting_as_references(tmp_path, edited):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    _catalog(framework, 'global', True, [])
    doc = repo / '.agent/SKILL_COMPILATION.md'
    doc.parent.mkdir(exist_ok=True)
    doc.write_text('See .claude/skills/demo/scripts/harness.py\n')
    _own(state, repo, doc)
    if edited:
        doc.write_text('Project note: run .claude/skills/demo/scripts/harness.py\n')
    plan = setup.build_plan(framework, projects, user, state)
    assert ('.claude/skills/demo/SKILL.md' in _deleted(plan, repo)) is not edited
    assert ('referenced' in _tier_diagnostics(plan, 'tier-collision').get('demo', '')) is edited


def test_bundled_shared_reference_copies_do_not_block_pruning(tmp_path):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    _catalog(framework, 'global', True, [])
    shared = repo / '.claude/skills/kept/references/shared/.agent/SAFETY.md'
    shared.parent.mkdir(parents=True)
    shared.write_text('See .claude/skills/demo/SKILL.md\n')
    assert '.claude/skills/demo/SKILL.md' in _deleted(setup.build_plan(framework, projects, user, state), repo)


def test_rollback_restores_the_ownership_ledger(tmp_path):
    framework, projects, user, state, repo = _tier_workspace(tmp_path)
    _catalog(framework, 'global', True, [])
    rel = '.claude/skills/demo/SKILL.md'
    before = dict(setup.owned_files(state, repo))
    assert rel in before
    plan = setup.build_plan(framework, projects, user, state)
    run = _apply(plan, state, projects, user)
    assert rel not in setup.owned_files(state, repo)
    result = setup.rollback(run, [projects, user])
    assert setup.restore_ownership(state, run, result['restored']) >= 1
    assert setup.owned_files(state, repo)[rel] == before[rel]
    # With the ledger back, the same retirement can be planned again.
    assert rel in _deleted(setup.build_plan(framework, projects, user, state), repo)


def test_rollback_drops_ledger_entries_for_files_it_removes(tmp_path):
    target = tmp_path / 'target'
    target.mkdir()
    state = tmp_path / 'state'
    data = b'New'
    path = target / 'new.md'
    operation = {'path': str(path), 'relative': 'new.md', 'action': 'create', 'before_sha256': None, 'after_sha256': setup.digest(data),
                 'content': base64.b64encode(data).decode(), 'before_content': None}
    run = setup.apply_operations([operation], state, [target])
    setup.save_ownership(state, run, target)
    assert 'new.md' in setup.owned_files(state, target)
    result = setup.rollback(run, [target])
    setup.restore_ownership(state, run, result['restored'])
    assert 'new.md' not in setup.owned_files(state, target)


def test_old_receipts_without_a_snapshot_leave_the_ledger_alone(tmp_path):
    target = tmp_path / 'target'
    target.mkdir()
    path = target / 'kept.md'
    path.write_bytes(b'Original')
    state = tmp_path / 'state'
    operation = {'path': str(path), 'relative': 'kept.md', 'action': 'delete', 'before_sha256': setup.digest(b'Original'), 'after_sha256': None,
                 'content': '', 'before_content': None}
    run = setup.apply_operations([operation], state, [target])
    result = setup.rollback(run, [target])
    assert setup.restore_ownership(state, run, result['restored']) == 0
