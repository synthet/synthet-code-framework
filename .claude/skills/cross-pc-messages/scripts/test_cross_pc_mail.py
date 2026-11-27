"""Tests for cross_pc_mail.py. No network; each test builds a throwaway share under tmp_path."""
from __future__ import annotations

import importlib.util
import json
import os
import threading
import time
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("cross_pc_mail", Path(__file__).with_name("cross_pc_mail.py"))
mail = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mail)

AGENTS = """# Share rules

| Host id | Machine | Local path |
|---------|---------|------------|
| `alpha` | ALPHA (desktop) | `C:\\Share` |
| `beta` | BETA (laptop) | `D:\\Share` |
"""


@pytest.fixture
def share(tmp_path, monkeypatch):
    root = tmp_path / "share"
    for pair in ("alpha-to-beta", "beta-to-alpha"):
        (root / pair).mkdir(parents=True)
    (root / "AGENTS.md").write_text(AGENTS, encoding="utf-8")
    (root / ".sync").mkdir()
    monkeypatch.setenv("CROSS_PC_SHARE", str(root))
    monkeypatch.setenv("CROSS_PC_HOST", "ALPHA")  # Machine-column match, case-insensitive
    monkeypatch.setattr(mail, "CANDIDATES", ())
    return root


def test_whoami_resolves_host_and_folders(share, capsys):
    assert mail.main(["whoami", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["host"] == "alpha" and out["peers"] == ["beta"]
    assert out["outgoing"]["beta"].endswith("alpha-to-beta")
    assert out["incoming"]["beta"].endswith("beta-to-alpha")


def test_manifest_and_verify_detect_drift(share, tmp_path, monkeypatch, capsys):
    skill = tmp_path / "src" / "cross-pc-messages"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("skill\n", encoding="utf-8")
    (skill / "scripts" / "cross_pc_mail.py").write_text("print(1)\n", encoding="utf-8")
    installed = tmp_path / "home" / "skills" / "cross-pc-messages"
    (installed / "scripts").mkdir(parents=True)
    # The installer rewrites Markdown (e.g. appends a line to SKILL.md); scripts are copied as-is.
    (installed / "SKILL.md").write_text("skill\nResolve helper paths from this skill directory.\n", encoding="utf-8")
    (installed / "scripts" / "cross_pc_mail.py").write_text("print(1)\n", encoding="utf-8")
    monkeypatch.setattr(mail, "SKILL_DIR", skill)
    monkeypatch.setattr(mail, "INSTALL_TREES", (str(tmp_path / "home" / "skills"),))
    release = share / "private" / "guides" / "cross-pc-messages" / f"v{mail.VERSION}"
    release.mkdir(parents=True)
    with pytest.raises(SystemExit):
        mail.main(["verify"])  # no manifest yet
    assert mail.main(["manifest", str(installed)]) == 0  # the release manifest comes from an installed copy
    (release / "SHA256SUMS").write_text(capsys.readouterr().out, encoding="utf-8")
    assert mail.main(["verify"]) == 0
    out = capsys.readouterr().out
    assert f"same v{mail.VERSION} (non-Markdown files)  source" in out and f"same v{mail.VERSION}  {installed}" in out
    (installed / "scripts" / "cross_pc_mail.py").write_text("print(2)\n", encoding="utf-8")
    assert mail.main(["verify"]) == 1
    assert f"DRIFT v{mail.VERSION}  {installed}  scripts/cross_pc_mail.py" in capsys.readouterr().out


def test_verify_ignores_line_endings_but_not_content(share, tmp_path, monkeypatch, capsys):
    """One PC installs from an LF tree, the other from a CRLF (autocrlf) checkout of the same commit."""
    files = {"SKILL.md": b"skill\nline two\n", "scripts/cross_pc_mail.py": b"print(1)\nprint(2)\n",
             "assets/logo.bin": b"\x00\r\n\x01"}  # binary: hashed as-is
    trees = {}
    for name, eol in (("lf", b"\n"), ("crlf", b"\r\n")):
        d = tmp_path / name / "skills" / "cross-pc-messages"
        for rel, data in files.items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_bytes(data if rel.endswith(".bin") else data.replace(b"\n", eol))
        trees[name] = d
    monkeypatch.setattr(mail, "SKILL_DIR", trees["lf"])
    monkeypatch.setattr(mail, "INSTALL_TREES", tuple(str(d.parent) for d in trees.values()))
    assert mail.main(["manifest", str(trees["crlf"])]) == 0
    crlf_sums = capsys.readouterr().out
    assert mail.main(["manifest", str(trees["lf"])]) == 0
    assert capsys.readouterr().out == crlf_sums  # same manifest from either checkout
    release = share / "private" / "guides" / "cross-pc-messages" / f"v{mail.VERSION}"
    release.mkdir(parents=True)
    (release / "SHA256SUMS").write_text(crlf_sums, encoding="utf-8")
    assert mail.main(["verify"]) == 0
    assert capsys.readouterr().out.count(f"same v{mail.VERSION}") == 2
    (trees["crlf"] / "scripts" / "cross_pc_mail.py").write_bytes(b"print(1)\r\nprint(3)\r\n")
    assert mail.main(["verify"]) == 1
    assert "DRIFT" in capsys.readouterr().out


def test_status_skips_folders_without_readme(share, capsys):
    (share / "beta-to-alpha" / "ssh").mkdir()
    (share / "beta-to-alpha" / "ssh" / "beta.pub").write_text("ssh-ed25519 AAAA example\n", encoding="utf-8")
    mail.main(["status", "--json", "--since", "0"])
    assert json.loads(capsys.readouterr().out) == []


def test_unknown_host_exits(share, monkeypatch):
    monkeypatch.setenv("CROSS_PC_HOST", "gamma")
    with pytest.raises(SystemExit):
        mail.main(["whoami"])


def test_new_creates_package_and_refuses_overwrite(share, capsys):
    assert mail.main(["new", "--to", "beta", "--topic", "gpu-setup", "--date", "2026-11-18"]) == 0
    readme = share / "alpha-to-beta" / "gpu-setup-2026-11-18" / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert "**From:** agent on alpha" in text and "beta-to-alpha/gpu-setup-2026-11-18-reply.md" in text
    with pytest.raises(SystemExit):
        mail.main(["new", "--to", "beta", "--topic", "gpu-setup", "--date", "2026-11-18"])
    with pytest.raises(SystemExit):
        mail.main(["new", "--to", "beta", "--topic", "Bad Topic"])


def test_reply_links_original_and_status_sees_it(share, capsys):
    pkg = share / "beta-to-alpha" / "ask-2026-11-18"
    pkg.mkdir()
    (pkg / "README.md").write_text("# ask\n", encoding="utf-8")
    mail.main(["status", "--json"])
    rows = json.loads(capsys.readouterr().out)
    assert [(r["thread"], r["messages"], r["state"]) for r in rows] == [("ask-2026-11-18", 1, "your turn")]
    assert mail.main(["reply", "--to", "beta", "--re", "ask-2026-11-18", "--kind", "result"]) == 0
    capsys.readouterr()
    reply = share / "alpha-to-beta" / "ask-2026-11-18-result.md"
    assert "](../beta-to-alpha/ask-2026-11-18/README.md)" in reply.read_text(encoding="utf-8")
    # A free-form follow-up from the peer joins the same thread and makes it your turn again.
    later = share / "beta-to-alpha" / "ask-2026-11-18-parity-notice.md"
    later.write_text("more\n", encoding="utf-8")
    t = reply.stat().st_mtime + 5
    os.utime(later, (t, t))
    mail.main(["status", "--json"])
    rows = json.loads(capsys.readouterr().out)
    assert [(r["thread"], r["messages"], r["state"], r["last"]) for r in rows] == [
        ("ask-2026-11-18", 3, "your turn", "ask-2026-11-18-parity-notice.md")]


def test_cross_topic_reply_and_fyi(share, capsys):
    out_dir, in_dir = share / "alpha-to-beta", share / "beta-to-alpha"
    (out_dir / "link-2026-11-18").mkdir()
    (out_dir / "link-2026-11-18" / "README.md").write_text("# link\n", encoding="utf-8")
    (out_dir / "run-2026-11-17-warning.md").write_text("# warning\n", encoding="utf-8")
    (out_dir / "run-2026-11-17").mkdir()
    (out_dir / "run-2026-11-17" / "README.md").write_text("# run\n", encoding="utf-8")
    reply = in_dir / "link-2026-11-18-reply.md"
    reply.write_text(
        "# reply\n- **Replies to:** [`alpha-to-beta/link-2026-11-18/README.md`](../alpha-to-beta/link-2026-11-18/README.md)\n"
        "  and [`run-2026-11-17-warning.md`](../alpha-to-beta/run-2026-11-17-warning.md)\n", encoding="utf-8")
    note = in_dir / "status-2026-11-18.md"
    note.write_text("# status\n- **Reply needed:** no\n", encoding="utf-8")
    # Quoting the header in prose is not an FYI marker.
    (in_dir / "idea-2026-11-18.md").write_text("Suggest a line `- **Reply needed:** no` for notes.\n", encoding="utf-8")
    t = time.time() + 10
    os.utime(reply, (t, t))
    os.utime(note, (t + 1, t + 1))
    mail.main(["status", "--json", "--since", "0"])
    rows = {r["thread"]: (r["state"], r["messages"]) for r in json.loads(capsys.readouterr().out)}
    # The second link wraps onto an indented continuation line and still counts: both threads are answered.
    # The run package and its -warning sibling are one thread, and the reply is counted once in it.
    assert rows["link-2026-11-18"] == ("your turn", 2)
    assert rows["run-2026-11-17"] == ("your turn", 3)
    assert rows["status-2026-11-18"] == ("fyi", 1)
    assert rows["idea-2026-11-18"] == ("your turn", 1)


def test_reply_body_file_is_atomic(share, tmp_path, capsys):
    (share / "beta-to-alpha" / "ping-2026-11-18.md").write_text("# ping\n", encoding="utf-8")
    body = tmp_path / "body.md"
    body.write_text("## Answer\n\n1. \n", encoding="utf-8")
    with pytest.raises(SystemExit):
        mail.main(["reply", "--to", "beta", "--re", "ping-2026-11-18.md", "--kind", "ack", "--body-file", str(body)])
    assert not (share / "alpha-to-beta" / "ping-2026-11-18-ack.md").exists()
    body.write_text("## Answer\n\npong\n", encoding="utf-8")
    assert mail.main(["reply", "--to", "beta", "--re", "ping-2026-11-18.md", "--kind", "ack", "--body-file", str(body)]) == 0
    text = (share / "alpha-to-beta" / "ping-2026-11-18-ack.md").read_text(encoding="utf-8")
    assert "pong" in text and "**Replies to:**" in text and "<one sentence" not in text
    assert mail.main(["check", str(share / "alpha-to-beta" / "ping-2026-11-18-ack.md")]) == 0


def test_ack_kind_and_reply_to_reply_keeps_topic(share, capsys):
    (share / "beta-to-alpha" / "ask-2026-11-18-result.md").write_text("# r\n", encoding="utf-8")
    assert mail.main(["reply", "--to", "beta", "--re", "ask-2026-11-18-result.md", "--kind", "ack"]) == 0
    assert (share / "alpha-to-beta" / "ask-2026-11-18-ack.md").is_file()


def test_new_from_file_is_atomic_and_checked(share, tmp_path, capsys):
    draft = tmp_path / "draft.md"
    draft.write_text("# hi\n- **Purpose:** <one sentence: why this message exists>\n1. \n", encoding="utf-8")
    with pytest.raises(SystemExit):
        mail.main(["new", "--to", "beta", "--topic", "hello", "--date", "2026-11-18", "--from-file", str(draft)])
    assert not (share / "alpha-to-beta" / "hello-2026-11-18").exists()
    assert mail.main(["new", "--to", "beta", "--topic", "hello", "--date", "2026-11-18", "--print"]) == 0
    assert "<one sentence" in capsys.readouterr().out and not (share / "alpha-to-beta" / "hello-2026-11-18").exists()
    draft.write_text("# hi\n- **Purpose:** say hello\n1. Reply with pong.\n", encoding="utf-8")
    assert mail.main(["new", "--to", "beta", "--topic", "hello", "--date", "2026-11-18", "--from-file", str(draft)]) == 0
    assert "pong" in (share / "alpha-to-beta" / "hello-2026-11-18" / "README.md").read_text(encoding="utf-8")


def test_watch_once_reports_new_file_and_ignores_partial_downloads(share, capsys):
    inbox = share / "beta-to-alpha"

    def drop():
        time.sleep(0.3)
        (inbox / "x.md.!sync").write_text("partial", encoding="utf-8")
        (share / ".sync" / "meta").write_text("m", encoding="utf-8")
        (inbox / "note-2026-11-18.md").write_text("hi", encoding="utf-8")

    t = threading.Thread(target=drop)
    t.start()
    assert mail.main(["watch", "--once", "--interval", "0.5"]) == 0
    t.join()
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines == ["NEW: beta-to-alpha/note-2026-11-18.md"]


def test_check_flags_secrets_without_echoing_them(tmp_path, capsys):
    secret = "ghp_" + "A" * 36
    f = tmp_path / "README.md"
    hf = "hf_" + "b" * 34
    key_header = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"  # built at runtime so repo secret scans stay quiet
    f.write_text(f"token: {secret}\n{key_header}\nTOKEN=<from private/auth>\n"
                 f"{hf}\nAuthorization: Bearer {'c' * 32}\n- **Purpose:** <one sentence: why this message exists>\n- \n", encoding="utf-8")
    assert mail.main(["check", str(f)]) == 1
    out = capsys.readouterr().out
    assert "github-token" in out and "private-key" in out and secret not in out and hf not in out
    assert ":3:" not in out  # a pointer to private storage is not a finding
    assert ":4: hf-token" in out and ":5: bearer-token" in out
    assert ":6: placeholder" in out and ":7: empty-list-item" in out
    clean = tmp_path / "ok.md"
    clean.write_text("Point to private/auth/env/ for the token.\n", encoding="utf-8")
    assert mail.main(["check", str(clean)]) == 0


def test_print_survives_a_cp1252_console(share):
    """A Windows console with a legacy code page must not crash on the template's arrow."""
    import subprocess
    import sys
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    run = subprocess.run([sys.executable, str(Path(mail.__file__)), "new", "--to", "beta", "--topic", "enc-test", "--print"],
                         capture_output=True, env=env)
    assert run.returncode == 0, run.stderr.decode("utf-8", "replace")
    assert "→" in run.stdout.decode("utf-8")
