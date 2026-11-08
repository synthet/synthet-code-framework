"""The shared harness registry: contract, lookups, consumers and the read-only drift audit."""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import harness_registry as hr  # noqa: E402

REGISTRY = hr.load()


def test_registry_is_valid_and_lists_the_five_active_harnesses():
    assert hr.validate(REGISTRY) == []
    assert hr.active_ids(REGISTRY) == ("claude", "codex", "cursor", "antigravity", "grok")
    assert [h["id"] for h in hr.harnesses(REGISTRY, include_retired=True)][-1] == "gemini"


def test_schema_file_names_every_harness_key():
    schema = json.loads((ROOT / ".agent" / "harnesses" / "registry.schema.json").read_text(encoding="utf-8"))
    keys = set(schema["$defs"]["harness"]["properties"])
    assert keys == hr._HARNESS_KEYS
    assert set(schema["$defs"]["harness"]["required"]) == hr._REQUIRED


@pytest.mark.parametrize("token, expected", [
    ("claude", "claude"), ("claude-code", "claude"), ("AGY", "antigravity"),
    ("agent", "cursor"), ("cursor-agent", "cursor"), ("gemini", "gemini"), ("nope", None),
])
def test_resolve_maps_aliases_to_canonical_ids(token, expected):
    h = hr.resolve(REGISTRY, token)
    assert (h["id"] if h else None) == expected


def test_validate_reports_duplicate_alias_and_missing_retired_reason():
    data = copy.deepcopy(REGISTRY)
    data["harnesses"][0]["aliases"].append("agy")
    gemini = next(h for h in data["harnesses"] if h["id"] == "gemini")
    del gemini["retired_reason"]
    problems = hr.validate(data)
    assert any("'agy' already used" in p for p in problems)
    assert any("retired harness needs retired_reason" in p for p in problems)


def test_validate_rejects_relative_paths_and_bad_gate():
    data = copy.deepcopy(REGISTRY)
    data["harnesses"][1]["home"]["path"] = ".codex"
    data["harnesses"][4]["gate"] = {"supported": False, "can_approve": True}
    problems = hr.validate(data)
    assert any("codex" in p and "home.path" in p for p in problems)
    assert any("can_approve requires supported" in p for p in problems)


def test_home_dir_honours_override_variable_and_appdata(tmp_path):
    claude = hr.resolve(REGISTRY, "claude")
    assert hr.home_dir(claude, home=tmp_path, env={}) == tmp_path / ".claude"
    assert hr.home_dir(claude, home=tmp_path, env={"CLAUDE_CONFIG_DIR": str(tmp_path / "x")}) == tmp_path / "x"
    assert hr.expand("%APPDATA%/Cursor/User", home=tmp_path, env={"APPDATA": str(tmp_path / "roam")}) == (
        tmp_path / "roam" / "Cursor" / "User")


def test_harness_logs_reads_ids_and_homes_from_registry(tmp_path, monkeypatch):
    from scripts.harness_logs.common import HARNESSES, Homes

    for var in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "GROK_HOME", "APPDATA"):
        monkeypatch.delenv(var, raising=False)
    assert hr.active_ids(REGISTRY) == HARNESSES
    homes = Homes.detect(tmp_path)
    assert (homes.claude, homes.codex, homes.cursor, homes.gemini, homes.grok) == (
        tmp_path / ".claude", tmp_path / ".codex", tmp_path / ".cursor", tmp_path / ".gemini", tmp_path / ".grok")
    assert homes.cursor_user == tmp_path / "AppData" / "Roaming" / "Cursor" / "User"


def test_permission_gate_harnesses_match_the_registry():
    adapters = (ROOT / "infra" / "jev" / "src" / "jev_engineering" / "permission" / "adapters.py").read_text(
        encoding="utf-8")
    ids_block = re.search(r"^HARNESSES = \([^)]*\)", adapters, re.M)
    can_block = re.search(r"^CAN_APPROVE = \{[^}]*\}", adapters, re.M)
    assert ids_block and can_block
    ids = tuple(re.findall(r'"([a-z-]+)"', ids_block.group(0)))
    can = dict(re.findall(r'"([a-z-]+)": (True|False)', can_block.group(0)))
    gated = tuple(h["id"] for h in REGISTRY["harnesses"] if h["gate"]["supported"])
    assert ids == gated
    assert {h: v == "True" for h, v in can.items()} == {
        h["id"]: h["gate"]["can_approve"] for h in REGISTRY["harnesses"] if h["gate"]["supported"]}


def _fake_consumers(root: Path, swarm_ids: list[str], allowed: list[str]) -> None:
    reg = root / "synthet-agent-swarm" / "agent-orchestrator" / "src" / "harness" / "registry.ts"
    reg.parent.mkdir(parents=True)
    reg.write_text("export const HARNESS_SPECS = [\n" + "".join(f'  {{\n    id: "{i}",\n  }},\n' for i in swarm_ids)
                   + "];\n", encoding="utf-8")
    cfg = root / "synthet-agent-swarm" / "agent-orchestrator" / "config.default.json"
    cfg.write_text(json.dumps({"defaultTimeoutMs": 1, "allowedAgents": allowed, "codex": {}}), encoding="utf-8")


def test_audit_accepts_aliases_and_skips_missing_repos(tmp_path):
    _fake_consumers(tmp_path, ["codex", "claude", "agy", "cursor", "gemini", "grok"],
                    ["codex", "agy", "claude", "cursor", "grok"])
    findings = {f.probe.file: f for f in hr.audit(REGISTRY, tmp_path)}
    ts = findings["agent-orchestrator/src/harness/registry.ts"]
    assert ts.found and not ts.unknown and not ts.missing
    assert not findings["jev/src/jev_engineering/permission/adapters.py"].found


def test_audit_flags_unknown_and_missing_harnesses(tmp_path):
    _fake_consumers(tmp_path, ["codex", "claude", "copilot"], ["codex", "claude"])
    finding = next(f for f in hr.audit(REGISTRY, tmp_path) if f.probe.file.endswith("registry.ts"))
    assert finding.unknown == ["copilot"]
    assert finding.missing == ["antigravity", "cursor", "grok"]
    assert hr.main(["audit", "--root", str(tmp_path)]) == 1


def test_cli_validate_list_and_resolve(capsys):
    assert hr.main(["validate"]) == 0
    assert hr.main(["resolve", "agy"]) == 0
    assert capsys.readouterr().out.strip().endswith("antigravity")
    assert hr.main(["list", "--json"]) == 0
    assert [h["id"] for h in json.loads(capsys.readouterr().out)] == list(hr.active_ids(REGISTRY))
