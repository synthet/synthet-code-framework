import http.server
import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import bg_status as B  # noqa: E402
import project_probes as P  # noqa: E402


def write_config(root: Path, data) -> Path:
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    path = root / ".claude" / "bg-status.json"
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def loopback_server():
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200 if self.path.split("?")[0] == "/ok" else 503)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_absent_probe_file_changes_nothing(tmp_path):
    assert P.collect(str(tmp_path), [], [], redact=B.redact) is None
    assert P.markdown(None) == [] and P.flags(None) == []
    snap = {"taken": "t", "flags": [], "tasks": [], "processes": [], "status_files": [], "status_files_partial": False,
            "memory": None, "gpu": None, "docker": None, "worktrees": []}
    assert "## Project" not in B.markdown(snap)


def test_config_is_found_from_a_subfolder_and_bad_files_become_notes(tmp_path):
    write_config(tmp_path, "{not json")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    section = P.collect(str(sub), [], [])
    assert "unreadable" in section["error"]
    assert P.flags(section) and "## Project" in "\n".join(P.markdown(section))
    write_config(tmp_path, [1, 2])
    assert "not a JSON object" in P.collect(str(sub), [], [])["error"]
    write_config(tmp_path, {"http": "nope", "paths": {"x": 1}})  # wrong shapes are ignored, not fatal
    section = P.collect(str(sub), [], [])
    assert section["http"] == [] and section["paths"] == []


def test_http_probe_kinds_and_redaction(tmp_path, loopback_server):
    write_config(tmp_path, {"http": [
        {"name": "ok", "url": f"{loopback_server}/ok"},
        {"name": "sick", "url": f"{loopback_server}/sick"},
        {"name": "closed", "url": "http://127.0.0.1:9/"},
        {"name": "remote", "url": "https://example.com/health"},
        {"name": "secret", "url": f"{loopback_server}/ok?api_key=abc123&page=2"},
        {"name": "userinfo", "url": loopback_server.replace("://", "://admin:hunter2@") + "/ok"},
        {"name": "malformed", "url": f"{loopback_server}/ok --token=abc123"},
    ]})
    start = time.monotonic()
    rows = {h["name"]: h for h in P.collect(str(tmp_path), [], [], redact=B.redact)["http"]}
    assert time.monotonic() - start < 4 * P.HTTP_TIMEOUT_S + 2
    assert rows["ok"]["status"] == "up" and "ms" in rows["ok"]
    assert rows["sick"]["status"] == "HTTP 503"
    assert rows["closed"]["status"].startswith("down")
    assert rows["remote"]["status"].startswith("skipped")
    assert rows["secret"]["status"] == "up" and "page=2" in rows["secret"]["url"]
    assert "hunter2" not in json.dumps(rows["userinfo"]) and "admin" not in rows["userinfo"]["url"]
    assert rows["malformed"]["status"].startswith("down")  # never raises, even on an invalid URL
    assert "abc123" not in json.dumps([rows["secret"], rows["malformed"]])
    flagged = P.flags({"project": "x", "config": "c", "http": list(rows.values()), "containers": []})
    assert any("sick" in f for f in flagged) and any("closed" in f for f in flagged)
    assert not any("remote" in f for f in flagged)


def test_process_and_container_probes(tmp_path):
    write_config(tmp_path, {
        "processes": [{"name": "mail", "pattern": r"dist[\\/]cli\.js mcp"}, {"name": "bad", "pattern": "("}],
        "containers": ["up-one", "stopped", "absent"],
    })
    procs = [{"pid": 11, "cmd": "node D:/x/dist/cli.js mcp --no-listen"}, {"pid": 12, "cmd": "python other.py"}]
    docker_rows = [{"name": "up-one", "status": "Up 2 hours"}, {"name": "stopped", "status": "Exited (0) 2 days ago"}]
    section = P.collect(str(tmp_path), procs, docker_rows)
    mail, bad = section["processes"]
    assert (mail["count"], mail["pids"]) == (1, [11])
    assert bad["count"] == 0 and "bad pattern" in bad["note"]
    states = {c["name"]: c["state"] for c in section["containers"]}
    assert states == {"up-one": "Up 2 hours", "stopped": "Exited (0) 2 days ago", "absent": "not found"}
    assert set(P.flags(section)) == {"container stopped: Exited (0) 2 days ago", "container absent: not found"}
    no_docker = P.collect(str(tmp_path), procs, None)
    assert {c["state"] for c in no_docker["containers"]} == {"docker not reachable"}
    assert P.flags(no_docker) == []


def test_path_probe_kinds(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.bin").write_bytes(b"x" * 2048)
    (tmp_path / "data" / "b.bin").write_bytes(b"y" * 1024)
    monkeypatch.setenv("BGS_TEST_HOME", str(tmp_path))
    write_config(tmp_path, {"paths": [
        {"name": "exists", "path": "data/a.bin", "kind": "exists"},
        {"name": "size-file", "path": "data/a.bin", "kind": "size"},
        {"name": "size-dir", "path": "%BGS_TEST_HOME%/data", "kind": "size"},
        {"name": "mtime", "path": "data", "kind": "mtime"},
        {"name": "count", "path": "data", "kind": "count"},
        {"name": "missing", "path": "nope/never", "kind": "size"},
        {"name": "weird", "path": "data", "kind": "delete"},
    ]})
    rows = {p["name"]: p for p in P.collect(str(tmp_path), [], [], now=time.time() + 5)["paths"]}
    assert rows["exists"]["value"] == "present"
    assert rows["size-file"]["value"] == 2048 and rows["size-dir"]["value"] == 3072
    assert rows["mtime"]["age_s"] >= 5
    assert rows["count"]["value"] == 2
    assert rows["missing"]["value"] == "missing"
    assert rows["weird"]["value"].startswith("unknown kind")
    text = "\n".join(P.markdown(P.collect(str(tmp_path), [], []), B.age))
    assert "3.0 KB" in text and "2 entries" in text and "updated" in text


def test_markdown_places_project_section_after_flags(tmp_path):
    write_config(tmp_path, {"notes": ["remember the thing"]})
    section = P.collect(str(tmp_path), [], [])
    snap = {"taken": "t", "flags": [], "tasks": [], "processes": [], "status_files": [], "status_files_partial": False,
            "memory": None, "gpu": None, "docker": None, "worktrees": [], "project": section}
    out = B.markdown(snap)
    assert out.index("## Flags") < out.index("## Project:") < out.index("## Claude Code background tasks")
    assert "note: remember the thing" in out
    assert os.path.basename(str(tmp_path)) in out


@pytest.fixture
def json_server():
    masked = "MY_" + "TOK" + "EN=hidden-value"   # built up so the literal never looks like a credential
    body = json.dumps({"localization_authority": {"mode": "shadow", "scan_cursor": 98135, "running": True},
                       "queue": [], "note": masked, "nested": {"a": [1, 2]}}).encode()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body if self.path == "/json" else b"<html>")

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_http_fields_pick_dotted_values_and_stay_redacted(tmp_path, json_server):
    write_config(tmp_path, {"http": [
        {"name": "drive", "url": f"{json_server}/json",
         "fields": ["localization_authority.mode", "localization_authority.scan_cursor", "queue", "nested.a",
                    "note", "no.such.key"]},
        {"name": "html", "url": f"{json_server}/page", "fields": ["x"]},
        {"name": "plain", "url": f"{json_server}/json"}]})
    rows = {h["name"]: h for h in P.collect(str(tmp_path), [], [], redact=B.redact)["http"]}
    f = rows["drive"]["fields"]
    assert f["localization_authority.mode"] == "shadow" and f["localization_authority.scan_cursor"] == 98135
    assert f["queue"] == "[]" and f["nested.a"] == "[1, 2]" and f["no.such.key"] == "missing"
    assert "hidden-value" not in str(f["note"])
    assert rows["html"]["fields"] == {"(body)": "not JSON"}
    assert "fields" not in rows["plain"]
    text = "\n".join(P.markdown(P.collect(str(tmp_path), [], [], redact=B.redact)))
    assert "localization_authority.mode=shadow" in text


def test_sql_guard_allows_one_plain_select_only():
    assert P.sql_guard("select mode, scan_cursor, updated_at from c where id = 1") is None
    assert P.sql_guard("WITH x AS (SELECT 1) SELECT * FROM x") is None
    for bad in ("update jobs set status = 'x'", "delete from jobs", "select 1; drop table jobs",
                "select * into t2 from jobs", "insert into t values (1)", "vacuum", "", "show all",
                "with d as (delete from t returning *) select * from d"):
        assert P.sql_guard(bad), bad


def test_sql_guard_rejects_side_effect_functions_but_allows_catalog_views():
    for bad in ("select pg_terminate_backend(pid) from pg_stat_activity",
                "select pg_cancel_backend (123)",
                "select pg_reload_conf()", "select pg_rotate_logfile()",
                "select pg_read_file('/etc/hostname')", "select pg_read_binary_file('/x')", "select pg_ls_dir('.')",
                "select set_config('statement_timeout', '0', false)", "select lo_import('/x')",
                "select dblink_exec('x', 'y')", "select * from dblink('x', 'y') as t(a int)",
                "select pg_advisory_lock(1)"):
        assert P.sql_guard(bad), bad
    assert P.sql_guard("select pid, state from pg_stat_activity where datname = current_database()") is None
    assert P.sql_guard("select count(*) from pg_locks") is None


def test_exec_probes_are_skipped_without_the_flag(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(P, "RUN", lambda args: calls.append(args) or (0, ""))
    write_config(tmp_path, {"container_ps": ["db"], "sql": [{"name": "q", "container": "db", "query": "select 1"}]})
    rows = [{"name": "db", "status": "Up 2 hours"}]
    section = P.collect(str(tmp_path), [], rows)
    assert section["container_ps"][0]["status"] == P.NEEDS_FLAG and section["sql"][0]["status"] == P.NEEDS_FLAG
    assert calls == []


def test_exec_probes_run_read_only_with_the_flag(tmp_path, monkeypatch):
    calls = []
    ps_out = ("  PID     ELAPSED   RSS COMMAND\n    1    02:18:12  1408 sleep infinity\n"
              "   57       10:04 204800 python -m scripts.backfill --tok" + "en zzz\n  120       00:04  2432 ps -eo pid\n")

    def fake(args):
        calls.append(args)
        return (0, ps_out) if "ps" in args else (0, "running | 12\nqueued | 3\n")

    monkeypatch.setattr(P, "RUN", fake)
    write_config(tmp_path, {"container_ps": ["db", "down", "bad name!"], "sql": [
        {"name": "jobs", "container": "db", "query": "select status, count(*) from jobs group by 1"},
        {"name": "evil", "container": "db", "query": "delete from jobs"}]})
    rows = [{"name": "db", "status": "Up 2 hours"}, {"name": "down", "status": "Exited (0)"}]
    section = P.collect(str(tmp_path), [], rows, redact=B.redact, exec_probes=True)
    ps = {c["container"]: c for c in section["container_ps"]}
    assert [p["pid"] for p in ps["db"]["procs"]] == [57] and ps["db"]["procs"][0]["mb"] == 200
    assert "zzz" not in ps["db"]["procs"][0]["cmd"]
    assert ps["down"]["status"] == "container not running" and ps["bad name!"]["status"].startswith("rejected")
    q = {s["name"]: s for s in section["sql"]}
    assert q["jobs"]["rows"] == ["running | 12", "queued | 3"] and q["evil"]["status"].startswith("rejected")
    sql_call = next(a for a in calls if "sh" in a)
    assert any(a.startswith("PGOPTIONS=") and "default_transaction_read_only=on" in a and "statement_timeout" in a
               for a in sql_call)
    assert "BGS_QUERY=select status, count(*) from jobs group by 1" in sql_call   # an env value, never shell text
    assert len(calls) == 2   # one ps, one sql: nothing ran for the stopped, bad-name or rejected entries
    text = "\n".join(P.markdown(section))
    assert "processes in db: 1" in text and "jobs: 2 row(s)" in text


def test_settings_feed_log_roots_and_slug_aliases(tmp_path):
    assert P.settings(str(tmp_path)) == {"log_roots": [], "slug_aliases": []}
    write_config(tmp_path, {"log_roots": ["logs", ".agent/scratch", 5], "slug_aliases": ["D--Projects-alias", ""]})
    sub = tmp_path / "sub"
    sub.mkdir()
    s = P.settings(str(sub))
    assert s["log_roots"] == [(tmp_path.resolve() / "logs").as_posix(),
                              (tmp_path.resolve() / ".agent" / "scratch").as_posix()]
    assert s["slug_aliases"] == ["D--Projects-alias"]
    write_config(tmp_path, "{broken")
    assert P.settings(str(tmp_path)) == {"log_roots": [], "slug_aliases": []}
