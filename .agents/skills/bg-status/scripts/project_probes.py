"""Project-specific probes for bg-status.

A project can describe its own background pieces in `.claude/bg-status.json`, found by walking up from --cwd:

    {
      "http":       [{"name": "...", "url": "http://127.0.0.1:8787/api/health"}],
      "processes":  [{"name": "...", "pattern": "regex over the command line"}],
      "containers": ["docker container name", ...],
      "paths":      [{"name": "...", "path": "%USERPROFILE%/x or repo/relative", "kind": "exists|size|mtime|count"}],
      "notes":      ["one-line reminder", ...]
    }

Rules:
- Read-only. Loopback-only HTTP GETs, regex matches over the process list bg-status already collected,
  the `docker ps` rows it already has, and file stats. The file never runs commands, so a repo's config
  cannot execute anything on this machine.
- Bounded. HTTP probes time out after HTTP_TIMEOUT_S; directory walks stop at COUNT_CAP entries.
- Never raises. A missing, unreachable or malformed item becomes a note in its row.
- Process patterns only see the processes bg-status lists (python, node, cmd, PowerShell); other executables
  cannot be matched.
- An absent file returns None, so bg-status output is unchanged.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

CONFIG = Path(".claude") / "bg-status.json"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
HTTP_TIMEOUT_S = 2.0
COUNT_CAP = 10_000
BODY_CAP = 256 * 1024     # bytes read from an HTTP body, only when "fields" are requested
FIELD_WIDTH = 120
MISSING = object()
KINDS = {"exists", "size", "mtime", "count"}


def _identity(text: str) -> str:
    return text


def find_config(cwd: str) -> Path | None:
    try:
        here = Path(cwd).resolve()
    except OSError:
        return None
    for folder in (here, *here.parents):
        candidate = folder / CONFIG
        if candidate.is_file():
            return candidate
    return None


def load(cwd: str) -> tuple[dict, Path] | None:
    path = find_config(cwd)
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"error": f"unreadable {CONFIG.as_posix()}: {exc}"}, path
    if not isinstance(data, dict):
        return {"error": f"{CONFIG.as_posix()} is not a JSON object"}, path
    return data, path


def expand(raw: str, root: Path) -> Path:
    text = re.sub(r"%([A-Za-z_][A-Za-z0-9_]*)%", lambda m: os.environ.get(m.group(1), m.group(0)), raw)
    p = Path(os.path.expandvars(os.path.expanduser(text)))
    return p if p.is_absolute() else root / p


def is_loopback(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and host in LOOPBACK


SECRET_QUERY = re.compile(r"(?i)([?&][^=&#]*(?:token|key|secret|pass|auth|sig)[^=&#]*=)[^&#]*")


def safe_url(url: str, redact: Callable[[str], str] = _identity) -> str:
    """URL for display: no user:password@, sensitive query values masked, then the caller's redact()."""
    shown = re.sub(r"(?i)^([a-z][a-z0-9+.-]*://)[^/@]*@", r"\1***@", url)
    return redact(SECRET_QUERY.sub(r"\1***", shown))


def pick_fields(body: bytes, paths: list[str], redact: Callable[[str], str] = _identity) -> dict:
    """Selected values from a JSON body by dotted path ("a.b.c"); a missing key or a non-JSON body says so."""
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
    except ValueError:
        return {"(body)": "not JSON"}
    out = {}
    for path in paths:
        cur = data
        for part in str(path).split("."):
            cur = cur.get(part, MISSING) if isinstance(cur, dict) else MISSING
            if cur is MISSING:
                break
        value = "missing" if cur is MISSING else json.dumps(cur, default=str) if isinstance(cur, (dict, list)) else cur
        out[str(path)] = redact(str(value))[:FIELD_WIDTH] if isinstance(value, str) else value
    return out


def http_probe(item: dict, redact: Callable[[str], str] = _identity) -> dict:
    name, url = str(item.get("name", "")), str(item.get("url", ""))
    fields = [f for f in item.get("fields", []) if isinstance(f, str)] if isinstance(item.get("fields"), list) else []
    shown = safe_url(url, redact)
    if not is_loopback(url):
        return {"name": name, "url": shown, "status": "skipped: only loopback URLs are probed"}
    start = time.monotonic()
    body = b""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=HTTP_TIMEOUT_S) as resp:
            code = resp.status
            if fields:
                body = resp.read(BODY_CAP)
    except urllib.error.HTTPError as exc:
        code = exc.code
    except Exception as exc:  # noqa: BLE001 - a probe never raises; any failure is reported as "down"
        reason = getattr(exc, "reason", None) or type(exc).__name__
        return {"name": name, "url": shown, "status": f"down ({safe_url(str(reason), redact)})"}
    ms = round((time.monotonic() - start) * 1000)
    row = {"name": name, "url": shown, "status": "up" if 200 <= code < 400 else f"HTTP {code}", "ms": ms}
    if fields and row["status"] == "up":
        row["fields"] = pick_fields(body, fields, redact)
    return row


# --- exec probes: declared in the file, run only with --exec-probes ------------------------------------------------
EXEC_TIMEOUT_S = 5
EXEC_ROWS = 12
CONTAINER_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
SQL_START = re.compile(r"(?is)^\s*(select|with)\b")
SQL_WRITE = re.compile(r"(?i)\b(insert|update|delete|merge|drop|alter|create|truncate|grant|revoke|copy|call|do|"
                       r"vacuum|analyze|cluster|reindex|refresh|lock|set|reset|listen|notify|prepare|execute|"
                       r"begin|commit|rollback|savepoint|discard|comment|security|into)\b")
# Side-effect functions still run inside a read-only transaction: killing backends, reloading config, reading
# server files, settings, large objects, dblink, advisory locks. Views such as pg_stat_activity are not calls.
SQL_CALL = re.compile(r"(?i)\b(pg_\w+|set_config|lo_\w+|dblink\w*)\s*\(")
PG_READ_ONLY = f"-c default_transaction_read_only=on -c statement_timeout={(EXEC_TIMEOUT_S - 2) * 1000}"
NEEDS_FLAG = "skipped: needs --exec-probes"
PS_NOISE = re.compile(r"^(ps -eo|sleep infinity$|/bin/sh -c sleep|tail -f /dev/null$)")


def sql_guard(query: str) -> str | None:
    """None when the query may run; otherwise why not. The read-only transaction is the real guard; this is a
    second line that keeps a repo file to one plain SELECT/WITH."""
    q = (query or "").strip()
    if not q:
        return "empty query"
    if ";" in q:
        return "rejected: ';' (one statement only)"
    if not SQL_START.match(q):
        return "rejected: only SELECT or WITH"
    m = SQL_WRITE.search(q) or SQL_CALL.search(q)
    return f"rejected: '{m.group(1)}' is not allowed" if m else None


def _exec(args: list[str]) -> tuple[int, str]:
    """Run one docker command with the exec timeout; (returncode, text). Never raises."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=EXEC_TIMEOUT_S)
        return p.returncode, p.stdout if p.returncode == 0 else (p.stderr or p.stdout)
    except subprocess.TimeoutExpired:
        return -1, f"timed out after {EXEC_TIMEOUT_S} s"
    except OSError as exc:
        return -1, f"docker not runnable ({exc.strerror or exc})"


RUN = _exec   # tests swap this out


def _running(name: str, docker_rows: list[dict] | None) -> str | None:
    """None when the container is up; otherwise the reason to skip it."""
    if not CONTAINER_NAME.match(name):
        return "rejected: bad container name"
    if docker_rows is None:
        return "docker not reachable"
    row = next((r for r in docker_rows if r.get("name") == name), None)
    return None if row and str(row.get("status", "")).startswith("Up") else "container not running"


def container_ps(name: str, docker_rows: list[dict] | None, enabled: bool,
                 redact: Callable[[str], str] = _identity) -> dict:
    if not enabled:
        return {"container": name, "status": NEEDS_FLAG}
    skip = _running(name, docker_rows)
    if skip:
        return {"container": name, "status": skip}
    rc, out = RUN(["docker", "exec", name, "ps", "-eo", "pid,etime,rss,args"])
    if rc != 0:
        return {"container": name, "status": f"failed: {redact(out.strip())[:FIELD_WIDTH]}"}
    rows = []
    for line in out.splitlines()[1:]:
        parts = line.split(None, 3)
        if len(parts) == 4 and parts[0].isdigit() and not PS_NOISE.match(parts[3]):
            mb = round(int(parts[2]) / 1024) if parts[2].isdigit() else parts[2]
            rows.append({"pid": int(parts[0]), "etime": parts[1], "mb": mb, "cmd": redact(parts[3])[:140]})
    return {"container": name, "status": "ok", "procs": rows[:EXEC_ROWS], "more": max(0, len(rows) - EXEC_ROWS)}


def sql_probe(item: dict, docker_rows: list[dict] | None, enabled: bool,
              redact: Callable[[str], str] = _identity) -> dict:
    name, container, query = str(item.get("name", "")), str(item.get("container", "")), str(item.get("query", ""))
    if not enabled:
        return {"name": name, "status": NEEDS_FLAG}
    bad = sql_guard(query) or _running(container, docker_rows)
    if bad:
        return {"name": name, "status": bad}
    # The query travels as an environment value, so no shell ever parses it; credentials stay in the container env.
    rc, out = RUN(["docker", "exec", "-e", f"PGOPTIONS={PG_READ_ONLY}", "-e", f"BGS_QUERY={query}", container, "sh", "-c",
                   'psql -X -At -F " | " -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$BGS_QUERY"'])
    if rc != 0:
        return {"name": name, "status": f"failed: {redact(out.strip())[:FIELD_WIDTH]}"}
    lines = [redact(ln)[:160] for ln in out.splitlines() if ln.strip()]
    return {"name": name, "status": "ok", "rows": lines[:EXEC_ROWS], "more": max(0, len(lines) - EXEC_ROWS)}


def settings(cwd: str) -> dict:
    """Inputs the core snapshot takes from the probe file: extra log roots (absolute globs) and task-slug aliases.

    Empty lists when there is no file, so the snapshot is unchanged.
    """
    loaded = load(cwd)
    if loaded is None or "error" in loaded[0]:
        return {"log_roots": [], "slug_aliases": []}
    cfg, path = loaded
    root = path.parent.parent

    def strings(key: str) -> list[str]:
        value = cfg.get(key, [])
        return [str(v) for v in value if isinstance(v, str) and v.strip()] if isinstance(value, list) else []

    return {"log_roots": [expand(g, root).as_posix() for g in strings("log_roots")],
            "slug_aliases": strings("slug_aliases")}


def process_probe(item: dict, procs: list[dict]) -> dict:
    name, pattern = str(item.get("name", "")), str(item.get("pattern", ""))
    try:
        rx = re.compile(pattern, re.I)
    except re.error as exc:
        return {"name": name, "count": 0, "pids": [], "note": f"bad pattern: {exc}"}
    hits = [p for p in procs if rx.search(str(p.get("cmd") or ""))]
    return {"name": name, "count": len(hits), "pids": [p.get("pid") for p in hits][:12]}


def container_states(names: list[str], docker_rows: list[dict] | None) -> list[dict]:
    if docker_rows is None:
        return [{"name": n, "state": "docker not reachable"} for n in names]
    by_name = {str(r.get("name", "")): r for r in docker_rows}
    return [{"name": n, "state": str(by_name[n].get("status", "?")) if n in by_name else "not found"} for n in names]


def path_probe(item: dict, root: Path, now: float) -> dict:
    name, kind = str(item.get("name", "")), str(item.get("kind", "exists"))
    raw = str(item.get("path", ""))
    out: dict[str, object] = {"name": name, "kind": kind}
    if kind not in KINDS:
        return {**out, "path": raw, "value": f"unknown kind (use {', '.join(sorted(KINDS))})"}
    p = expand(raw, root)
    out["path"] = str(p)
    try:
        if not p.exists():
            return {**out, "value": "missing"}
        if kind == "exists":
            out["value"] = "present"
        elif kind == "size":
            out["value"] = p.stat().st_size if p.is_file() else sum(
                f.stat().st_size for _, f in zip(range(COUNT_CAP), p.iterdir()) if f.is_file())
        elif kind == "mtime":
            newest = p.stat().st_mtime
            if p.is_dir():
                for _, f in zip(range(COUNT_CAP), p.iterdir()):
                    newest = max(newest, f.stat().st_mtime)
            out["value"], out["age_s"] = newest, max(0.0, now - newest)
        else:  # count
            out["value"] = sum(1 for _ in zip(range(COUNT_CAP), p.iterdir())) if p.is_dir() else 1
    except OSError as exc:
        out["value"] = f"unreadable ({exc.strerror or exc})"
    return out


def collect(cwd: str, procs: list[dict], docker_rows: list[dict] | None, now: float | None = None,
            redact: Callable[[str], str] = _identity, exec_probes: bool = False) -> dict | None:
    """Return the Project section, or None when the project has no probe file.

    container_ps and sql entries run `docker exec` only when exec_probes is True (the --exec-probes flag);
    otherwise they are listed as skipped.
    """
    loaded = load(cwd)
    if loaded is None:
        return None
    cfg, path = loaded
    root = path.parent.parent
    base = {"config": str(path), "project": root.name}
    if "error" in cfg:
        return {**base, "error": cfg["error"]}
    now = time.time() if now is None else now

    def items(key: str) -> list:
        value = cfg.get(key, [])
        return value if isinstance(value, list) else []

    return {
        **base,
        "http": [http_probe(i, redact) for i in items("http") if isinstance(i, dict)],
        "processes": [process_probe(i, procs) for i in items("processes") if isinstance(i, dict)],
        "containers": container_states([str(n) for n in items("containers")], docker_rows),
        "paths": [path_probe(i, root, now) for i in items("paths") if isinstance(i, dict)],
        "container_ps": [container_ps(str(n), docker_rows, exec_probes, redact) for n in items("container_ps")],
        "sql": [sql_probe(i, docker_rows, exec_probes, redact) for i in items("sql") if isinstance(i, dict)],
        "notes": [str(n) for n in items("notes")],
    }


def flags(section: dict | None) -> list[str]:
    """Things the project said should be up but are not."""
    if not section:
        return []
    if "error" in section:
        return [f"project probe file: {section['error']}"]
    out = [f"{h['name']} is {h['status']} ({h['url']})" for h in section["http"]
           if h["status"] != "up" and not h["status"].startswith("skipped")]
    out += [f"container {c['name']}: {c['state']}" for c in section["containers"]
            if not c["state"].startswith("Up") and c["state"] != "docker not reachable"]
    return out


def _human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def markdown(section: dict | None, age_fmt: Callable[[float], str] | None = None) -> list[str]:
    if not section:
        return []
    lines = [f"## Project: {section['project']}", "", f"Probes from `{section['config']}`.", ""]
    if "error" in section:
        return lines + [f"- {section['error']}", ""]
    for h in section["http"]:
        ms = f", {h['ms']} ms" if "ms" in h else ""
        lines.append(f"- {h['name']}: **{h['status']}**{ms} ({h['url']})")
        if h.get("fields"):
            lines.append("  - " + ", ".join(f"{k}={v}" for k, v in h["fields"].items()))
    for p in section["processes"]:
        pids = f" (PID {', '.join(map(str, p['pids']))})" if p.get("pids") else ""
        lines.append(f"- {p['name']}: {p.get('note') or str(p['count']) + ' running'}{pids}")
    for c in section["containers"]:
        lines.append(f"- container {c['name']}: {c['state']}")
    for p in section["paths"]:
        v = p["value"]
        if p["kind"] == "size" and isinstance(v, int):
            v = _human_bytes(v)
        elif p["kind"] == "mtime" and "age_s" in p:
            v = f"updated {age_fmt(p['age_s']) if age_fmt else str(round(p['age_s'])) + ' s'} ago"
        elif p["kind"] == "count" and isinstance(v, int):
            v = f"{v}{'+' if v >= COUNT_CAP else ''} entries"
        lines.append(f"- {p['name']}: {v}")
    for c in section.get("container_ps", []):
        if c["status"] != "ok":
            lines.append(f"- processes in {c['container']}: {c['status']}")
            continue
        lines.append(f"- processes in {c['container']}: {len(c['procs']) + c['more']}"
                     + ("" if c["procs"] else " (idle)"))
        lines += [f"  - PID {p['pid']}, {p['etime']}, {p['mb']} MB: `{p['cmd']}`" for p in c["procs"]]
        if c["more"]:
            lines.append(f"  - ... {c['more']} more")
    for q in section.get("sql", []):
        if q["status"] != "ok":
            lines.append(f"- {q['name']}: {q['status']}")
            continue
        lines.append(f"- {q['name']}: " + ("none" if not q["rows"] else f"{len(q['rows']) + q['more']} row(s)"))
        lines += [f"  - {r}" for r in q["rows"]] + ([f"  - ... {q['more']} more"] if q["more"] else [])
    lines += [f"- note: {n}" for n in section["notes"]]
    return lines + [""]
