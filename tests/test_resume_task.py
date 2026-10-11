"""Synthetic transcript coverage; these tests never read real session stores."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


PATH = Path(__file__).resolve().parents[1] / '.claude/skills/resume-task/scripts/harvest.py'
spec = importlib.util.spec_from_file_location('resume_task_harvest', PATH)
harvest = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = harvest
spec.loader.exec_module(harvest)


def prepare(monkeypatch, tmp_path):
    monkeypatch.setattr(harvest.Path, 'home', staticmethod(lambda: tmp_path / 'profile'))
    monkeypatch.setattr(harvest, 'probe', lambda: {})
    for key in ('CODEX_HOME', 'CLAUDE_CONFIG_DIR'):
        monkeypatch.delenv(key, raising=False)


def test_export_recovery_redacts_reports_and_preserves_input(tmp_path, monkeypatch):
    prepare(monkeypatch, tmp_path)
    transcript = tmp_path / 'export.md'
    secret = 'sk-' + 'a' * 25
    transcript.write_text('# unfinished work\n## User\nContinue the renderer fix.\n## Assistant\nNext steps:\n- Verify IPC.\n' + secret)
    original = transcript.read_bytes()
    out = tmp_path / 'scratch'
    monkeypatch.setattr(sys, 'argv', ['harvest', '--sources', 'md', '--md', str(transcript), '--out', str(out), '--no-git'])
    harvest.main()
    payload = json.loads((out / 'candidates.json').read_text())
    session = payload['projects'][0]['sessions'][0]
    assert session['first_ask'] == 'Continue the renderer fix.'
    assert any('Verify IPC' in candidate['text'] for candidate in session['candidates'])
    assert secret not in (out / 'candidates.json').read_text()
    assert secret not in (out / 'digest.md').read_text()
    assert transcript.read_bytes() == original


def test_profile_discovery_is_explicit(tmp_path, monkeypatch):
    prepare(monkeypatch, tmp_path)
    harvest.PROFILE_ROOTS[:] = []
    assert harvest.homes() == [tmp_path / 'profile']
    harvest.PROFILE_ROOTS[:] = [tmp_path / 'explicit-profile']
    assert harvest.homes() == [tmp_path / 'profile', tmp_path / 'explicit-profile']
    harvest.PROFILE_ROOTS[:] = []


def test_output_cannot_overwrite_session_stores(tmp_path, monkeypatch):
    prepare(monkeypatch, tmp_path)
    out = tmp_path / 'profile/.codex/sessions'
    monkeypatch.setattr(sys, 'argv', ['harvest', '--sources', 'md', '--out', str(out), '--no-git'])
    with pytest.raises(SystemExit) as error:
        harvest.main()
    assert error.value.code == 2
    assert not out.exists()


def test_redaction_covers_metadata_and_resume_arguments_are_quoted():
    token = 'sk-' + 'b' * 25
    assert token not in json.dumps(harvest.redact_report({'path': token, 'nested': [{'title': token}]}))
    session = harvest.Session(tool='codex', sid="session'; injected", path='synthetic')
    command = harvest.resume_cmd(session)
    assert command.startswith('codex resume ')
    if harvest.os.name == 'nt':
        assert command == "codex resume 'session''; injected'"
    else:
        assert harvest.shlex.split(command) == ['codex', 'resume', session.sid]
