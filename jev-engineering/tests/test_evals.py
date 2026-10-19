import json
from pathlib import Path

import pytest

from jev_engineering.client import FailingBackend, FixtureBackend
from jev_engineering.service import Engineering
from jev_engineering.state_store import StateStore

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
REQUIRED = {
    "benign",
    "routing",
    "ambiguity",
    "low_confidence",
    "secrets",
    "destructive",
    "prompt_injection",
    "missing_credentials",
    "network",
    "bias",
}


def test_case_inventory():
    assert len(CASES) >= 30
    assert REQUIRED <= {case["category"] for case in CASES}
    assert len({case["id"] for case in CASES}) == len(CASES)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_case(case, tmp_path):
    if case.get("failure"):
        backend = FailingBackend(case["failure"])
    elif "fixture" in case:
        backend = FixtureBackend(case["fixture"])
    else:
        backend = FailingBackend("should_not_call")
    engineering = Engineering(
        backend=backend,
        store=StateStore(tmp_path / "state.db"),
        metrics_path=tmp_path / "metrics.jsonl",
        root=tmp_path,
    )
    tool = case["tool"]
    payload = case["input"]
    if tool == "route_task":
        result = engineering.route_task(**payload)
    elif tool == "assess_risk":
        result = engineering.assess_risk(**payload)
    elif tool == "select_context":
        result = engineering.select_context(**payload)
    elif tool == "decide":
        result = engineering.decide(**payload)
    else:
        raise AssertionError(tool)
    for key, value in case["expect"].items():
        assert result[key] == value, (case["id"], key, result.get(key), value)
    assert result.get("decision") != "allow"
    blob = json.dumps(result)
    assert "api_key" not in blob
    assert "github_pat" not in blob
    assert "abc123secret" not in blob
    if result.get("allows_action") is not None:
        assert result["allows_action"] is False
    metrics = (tmp_path / "metrics.jsonl").read_text(encoding="utf-8")
    assert "api_key" not in metrics
    assert "github_pat" not in metrics
    assert "abc123secret" not in metrics
