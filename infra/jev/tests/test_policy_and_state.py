from jev_engineering.catalog import catalog, select_instructions
from jev_engineering.client import DecisionClient, FailingBackend
from jev_engineering.hook import pre_tool_decision, prompt_decision
from jev_engineering.redact import redact
from jev_engineering.routing import rebuild_prefers_stay
from jev_engineering.state_store import StateStore


def test_long_context_handoff_costs_more_than_staying():
    assert rebuild_prefers_stay("opus", "sonnet", 650_000, 120_000, 230_000)


def test_small_context_handoff_can_be_cheaper():
    assert not rebuild_prefers_stay("opus", "haiku", 1_000, 200, 200)


def test_sensitive_state_is_not_sent():
    client = DecisionClient(FailingBackend("should_not_call"))
    result = client.judge({"task": "api_key=abc123secret"}, {"q": {"type": "noul"}})
    assert result["jev_called"] is False
    assert result["fallback_reason"] == "sensitive_state"
    assert client.calls == 0


def test_redact_replaces_secret_text():
    assert "supersecret" not in redact("api_key=supersecret")
    assert "[redacted]" in redact("api_key=supersecret")


def test_catalog_hides_schema_until_requested():
    brief = catalog()
    assert "schema" not in brief[0]
    full = catalog(include_schema=True, names=["search"])
    assert full[0]["schema"]["query"] == "string"
    assert {item["id"] for item in select_instructions("run pytest on app.py")} >= {"python"}
    assert {item["id"] for item in select_instructions("read .env")} >= {"secrets"}


def test_lock_blocks_second_writer(tmp_path):
    store = StateStore(tmp_path / "state.db")
    assert store.acquire_lock("src/app.py", "agent-a")
    assert not store.acquire_lock("src/app.py", "agent-b")
    store.release_lock("src/app.py", "agent-a")
    assert store.acquire_lock("src/app.py", "agent-b")
    task_id = store.create_task("fix the parser")
    store.add_chunk(source="src/app.py", text="parser", provenance="file", task_id=task_id)
    assert store.list_chunks(task_id)[0]["provenance"] == "file"


def test_prompt_hook_does_not_echo_secrets():
    result = prompt_decision({"prompt": "use api_key=abc123secret"})
    text = result["hookSpecificOutput"]["additionalContext"]
    assert "abc123secret" not in text
    assert "credential" in text


def test_pre_tool_hook_denies_without_allow(monkeypatch, tmp_path):
    monkeypatch.setenv("JEV_ENGINEERING_ROOT", str(tmp_path))
    monkeypatch.delenv("JEV_HOOK_LIVE", raising=False)
    result = pre_tool_decision({"tool_name": "Bash", "tool_input": {"command": "rm -rf /tmp/app"}})
    decision = result["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny"
    assert decision != "allow"


def test_pre_tool_hook_defers_ordinary_test(monkeypatch, tmp_path):
    monkeypatch.setenv("JEV_ENGINEERING_ROOT", str(tmp_path))
    monkeypatch.delenv("JEV_HOOK_LIVE", raising=False)
    result = pre_tool_decision(
        {"tool_name": "Bash", "tool_input": {"command": "python -m pytest tests/test_app.py"}}
    )
    assert result["hookSpecificOutput"]["permissionDecision"] == "defer"
