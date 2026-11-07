#!/usr/bin/env python3
"""bg-status: a read-only snapshot of background work on this machine.

Sections:
- Claude Code background tasks (and their exit markers);
- detached worker processes;
- recent status and log files;
- GPU, Docker and memory;
- git worktrees.

Flags come first. Nothing is stopped, started or written. Every probe has a timeout, and a missing tool skips its
section. Command lines are redacted before printing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from collections.abc import Iterable
from pathlib import Path

import project_probes  # sibling module: optional per-project probes from .claude/bg-status.json

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
EXIT = re.compile(r"\[exited with code (-?\d+)\]\s*$")
KILLED = re.compile(r"\[?killed\]\s*$")
ACTIVE_S = 600            # a task written within this many seconds is "active"
QUIET_FLAG_S = 1800       # a quiet task older than this is flagged
LOW_RAM_GB = 3.0
BIG_WORKER_GB = 4.0
DONE_WORDS = re.compile(r"\b(done|complete|completed|finished|exit 0)\b", re.I)
REDACT_FLAG = re.compile(r"(?i)(--?(?:token|key|api[-_]?key|pass(?:word|wd)?|secret|auth)[ =])(\S+)")
REDACT_ENV = re.compile(r"\b([A-Z][A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|PASSWD)[A-Z0-9_]*=)(\S+)")
INFRA = [r"run_jev_mcp", r"llmwiki", r"run_mcp\.py", r"langserver", r"uvicorn", r"mcp[-_]server", r"\bmcp\b"]
WORKER = [r"-m scripts\.", r"\btrain_\w+\.py", r"\.cmd\b", r"\s-u\s", r"\bworker\b",
          r"(?i)\bdocker(?:\.exe)?\"?\s+(?:exec|run)\b.*(?:\bpython3?\b|\.py\b|\.sh\b|-m\s)"]
DOCKER_JOB = re.compile(r"(?i)\bdocker(?:\.exe)?\"?\s+(?:exec|run)\b")   # other docker CLI calls are noise
PRUNE = {".git", "node_modules", "img", "images", "masks", "file-backup", "sidecar-backup", "cache", "data",
         "__pycache__", ".venv", "venv", "weights", "labels"}


# --- pure helpers (unit-tested) ----------------------------------------------------------------------------------
def clean_last_line(text: str, width: int = 160) -> str:
    text = ANSI.sub("", text).replace("\r", "\n")
    lines = [ln.strip() for ln in text.splitlines()
             if ln.strip() and not EXIT.search(ln.strip()) and not KILLED.fullmatch(ln.strip())]
    return lines[-1][:width] if lines else ""


def task_status(tail: str, age_s: float) -> str:
    m = EXIT.search(tail.strip())
    if m:
        return f"exited {m.group(1)}"
    if KILLED.search(tail.strip()):
        return "killed"
    return "active" if age_s < ACTIVE_S else "quiet"


def redact(cmd: str) -> str:
    return REDACT_ENV.sub(r"\1***", REDACT_FLAG.sub(r"\1***", cmd or ""))


def bucket(cmd: str) -> str:
    c = cmd or ""
    if any(re.search(p, c) for p in INFRA):
        return "infrastructure"
    if any(re.search(p, c) for p in WORKER):
        return "worker"
    return "other"


def project_slug(path: str | Path) -> str:
    """Claude Code's folder name for a working directory, e.g. D:\\Projects\\x_y -> D--Projects-x-y.

    Every character other than a letter or digit becomes '-' (so '_' and '.' do too).
    """
    return re.sub(r"[^A-Za-z0-9]", "-", str(path)).rstrip("-")


def task_slugs(cwd: str, aliases: Iterable[str] = ()) -> set[str]:
    """Slugs whose tasks belong to cwd: as given, through junctions/symlinks resolved, plus project aliases."""
    slugs = {project_slug(cwd).lower()}
    try:
        slugs.add(project_slug(Path(cwd).resolve()).lower())
    except OSError:
        pass
    return slugs | {str(a).lower() for a in aliases if a}


def default_ref(repo: str, run=None) -> str | None:
    """The remote default branch to test 'merged' against: origin/HEAD, else origin/main, else origin/master."""
    run = run or _run
    out = run(["git", "-C", str(repo), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], 5)
    if out and out.strip():
        return out.strip()
    for ref in ("origin/main", "origin/master"):
        if run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", ref], 5):
            return ref
    return None


def unique_repos(paths: list[Path]) -> list[Path]:
    """Drop paths that resolve to a repo already listed (a junction to another checkout)."""
    seen, out = set(), []
    for p in paths:
        try:
            key = os.path.normcase(str(Path(p).resolve()))
        except OSError:
            key = os.path.normcase(str(p))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def status_key(name: str) -> str:
    """'e8-worker-20261101-status.txt' -> 'e8-worker-20261101'; '' when too short to match on."""
    key = re.sub(r"[-_]?status\.txt$", "", name, flags=re.I)
    return key if len(key) >= 6 else ""


def false_done(status_files: list[dict], workers: list[dict]) -> list[str]:
    """Status files that say done while a worker naming them is still running."""
    out = []
    for f in status_files:
        key = status_key(Path(f["path"]).name)
        if key and DONE_WORDS.search(f.get("last", "")) and any(key in (w.get("cmd") or "") for w in workers):
            out.append(f["path"])
    return out


def age(seconds: float) -> str:
    seconds = max(0.0, seconds)   # clock skew between file systems
    if seconds < 90:
        return f"{int(seconds)}s"
    if seconds < 5400:
        return f"{int(seconds / 60)}m"
    if seconds < 172800:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


# --- probes (read-only, bounded) ---------------------------------------------------------------------------------
def _run(args, timeout=8):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return p.stdout if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _ps_json(script, timeout=10):
    out = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], timeout)
    if not out or not out.strip():
        return []
    data = json.loads(out)
    return data if isinstance(data, list) else [data]


def _read_tail(path: Path, n: int = 4096) -> str:
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - n))
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def claude_tasks(cwd: str, all_projects: bool, now: float, aliases: Iterable[str] = ()) -> list[dict]:
    root = Path(tempfile.gettempdir()) / "claude"
    slugs = task_slugs(cwd, aliases)
    rows = []
    for proj in (root.iterdir() if root.is_dir() else []):
        if not proj.is_dir() or (not all_projects and proj.name.lower() not in slugs):
            continue
        for f in proj.glob("*/tasks/*.output"):
            try:
                st = f.stat()
            except OSError:
                continue
            tail = _read_tail(f)
            a = now - st.st_mtime
            rows.append({"task": f.stem, "session": f.parent.parent.name[:8], "project": proj.name,
                         "status": task_status(tail, a), "age_s": a, "bytes": st.st_size,
                         "last": clean_last_line(tail)})
    rows.sort(key=lambda r: r["age_s"])
    return rows


def processes(now: float) -> list[dict]:
    script = ("Get-CimInstance Win32_Process -Filter \"Name like 'python%' or Name='cmd.exe' or Name like 'pwsh%' "
              "or Name like 'powershell%' or Name='node.exe' or Name='docker.exe'\" | Select-Object ProcessId,ParentProcessId,Name,"
              "WorkingSetSize,@{n='Created';e={[int64](($_.CreationDate.ToUniversalTime())-[datetime]'1970-01-01')"
              ".TotalSeconds}},CommandLine | ConvertTo-Json -Compress")
    me = {os.getpid(), os.getppid()}
    rows = []
    for p in _ps_json(script):
        pid = p.get("ProcessId")
        cmd = p.get("CommandLine") or ""
        if pid in me or "bg_status.py" in cmd or "Get-CimInstance Win32_Process" in cmd:
            continue
        if str(p.get("Name") or "").lower() == "docker.exe" and not DOCKER_JOB.search(cmd):
            continue   # only `docker exec` / `docker run` can be background work
        rows.append({"pid": pid, "ppid": p.get("ParentProcessId"), "name": p.get("Name"),
                     "gb": round((p.get("WorkingSetSize") or 0) / 2**30, 2),
                     "age_s": now - (p.get("Created") or now), "bucket": bucket(cmd), "cmd": redact(cmd)[:160]})
    return rows


def memory() -> dict:
    both = _ps_json("$o=Get-CimInstance Win32_OperatingSystem; $t=Get-Process | Sort-Object WorkingSet64 -Descending | "
                    "Select-Object -First 5 Name,Id,@{n='GB';e={[math]::Round($_.WorkingSet64/1GB,2)}}; "
                    "@{os=@{FreePhysicalMemory=$o.FreePhysicalMemory;TotalVisibleMemorySize=$o.TotalVisibleMemorySize};"
                    "top=@($t)} | ConvertTo-Json -Compress -Depth 4")
    if not both:
        return {}
    o, top = both[0]["os"], both[0]["top"]
    return {"free_gb": round(o["FreePhysicalMemory"] / 2**20, 1), "total_gb": round(o["TotalVisibleMemorySize"] / 2**20, 1),
            "top": [{"name": t["Name"], "pid": t["Id"], "gb": t["GB"]} for t in top]}


def gpu() -> dict:
    out = _run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits"], 6)
    if not out:
        return {}
    name, util, used, total = [x.strip() for x in out.splitlines()[0].split(",")]
    apps = _run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"], 6) or ""
    procs = []
    for line in apps.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) == 2 and parts[0].isdigit():
            procs.append({"pid": int(parts[0]), "mib": parts[1]})
    return {"name": name, "util": util, "used_mib": used, "total_mib": total, "procs": procs}


def docker() -> list[dict] | None:
    out = _run(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Image}}"], 5)
    if out is None:
        return None
    return [dict(zip(("name", "status", "image"), ln.split("\t"))) for ln in out.splitlines() if ln.strip()]


def status_files(roots: list[str], hours: float, now: float, budget_s: float = 3.0) -> tuple[list[dict], bool]:
    """Recent *status*.txt and *.log files under the roots (pruned walk, depth <= 6, time-boxed)."""
    import glob

    start, rows, partial, seen = time.monotonic(), [], False, set()
    for pattern in roots:
        for base in glob.glob(pattern):
            base_depth = Path(base).resolve().as_posix().count("/")
            for dirpath, dirnames, filenames in os.walk(base):
                if time.monotonic() - start > budget_s:
                    return rows, True
                depth = Path(dirpath).resolve().as_posix().count("/") - base_depth
                keep = []
                for d in dirnames:
                    if d in PRUNE or depth >= 6:
                        continue
                    try:   # below depth 2, only folders changed within the window (new files land there)
                        if depth >= 2 and now - os.stat(os.path.join(dirpath, d)).st_mtime > hours * 3600:
                            continue
                    except OSError:
                        continue
                    keep.append(d)
                dirnames[:] = keep
                for fn in filenames:
                    low = fn.lower()
                    if not (low.endswith(".log") or ("status" in low and low.endswith(".txt"))):
                        continue
                    p = Path(dirpath) / fn
                    try:
                        mt = p.stat().st_mtime
                    except OSError:
                        continue
                    key = os.path.normcase(os.path.abspath(p))
                    if now - mt <= hours * 3600 and key not in seen:   # overlapping root globs
                        seen.add(key)
                        rows.append({"path": str(p), "age_s": max(0.0, now - mt),
                                     "last": clean_last_line(_read_tail(p, 2048))})
    rows.sort(key=lambda r: r["age_s"])
    return rows, partial


def worktrees(repos_root: str, budget_s: float = 6.0) -> list[dict]:
    start, rows = time.monotonic(), []
    repos = sorted(Path(repos_root).iterdir()) if Path(repos_root).is_dir() else []
    for repo in unique_repos([r for r in repos if (r / ".git").is_dir()]):
        if time.monotonic() - start > budget_s:
            break
        out = _run(["git", "-C", str(repo), "worktree", "list", "--porcelain"], 5)
        if not out:
            continue
        base = None   # resolved lazily: only repos with extra worktrees pay for it
        entries, cur = [], {}
        for line in out.splitlines() + [""]:
            if not line.strip():
                if cur:
                    entries.append(cur)
                cur = {}
            elif " " in line:
                k, v = line.split(" ", 1)
                cur[k] = v
            else:
                cur[line] = True
        for e in entries[1:]:            # the first entry is the main checkout
            path = e.get("worktree", "")
            branch = e.get("branch", "").replace("refs/heads/", "") or "(detached)"
            dirty = _run(["git", "-C", path, "status", "--porcelain"], 5)
            merged = None
            if base is None:
                base = default_ref(str(repo)) or ""
            if branch != "(detached)" and base:   # no default branch resolved: merged stays None ("?")
                try:
                    rc = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", branch, base],
                                        capture_output=True, timeout=5).returncode
                    merged = True if rc == 0 else False if rc == 1 else None   # 128 = git error, not "unmerged"
                except (OSError, subprocess.TimeoutExpired):
                    merged = None
            rows.append({"repo": repo.name, "path": path, "branch": branch,
                         "dirty": None if dirty is None else len([x for x in dirty.splitlines() if x.strip()]),
                         "merged": merged})
    return rows


# --- report ------------------------------------------------------------------------------------------------------
def collect(args) -> dict:
    now = time.time()
    procs = processes(now)
    workers = [p for p in procs if p["bucket"] == "worker"]
    extra = project_probes.settings(args.cwd)   # empty lists without a probe file
    files, partial = status_files(extra["log_roots"] + args.root, args.hours, now)   # project roots get the budget first
    snap = {"taken": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tasks": claude_tasks(args.cwd, args.all_projects, now, extra["slug_aliases"]),
            "processes": procs, "status_files": files, "status_files_partial": partial, "memory": memory(),
            "gpu": gpu(), "docker": docker(), "worktrees": [] if args.no_worktrees else worktrees(args.repos_root)}
    flags = []
    mem = snap["memory"]
    if mem and mem["free_gb"] < LOW_RAM_GB:
        flags.append(f"low memory: {mem['free_gb']} GB free of {mem['total_gb']} GB")
    flags += [f"large worker PID {w['pid']}: {w['gb']} GB" for w in workers if w["gb"] > BIG_WORKER_GB]
    flags += [f"quiet task {t['task']} ({age(t['age_s'])} since last write): watch loop or reaped?"
              for t in snap["tasks"] if t["status"] == "quiet" and t["age_s"] > QUIET_FLAG_S and t["age_s"] < 86400]
    flags += [f"status file says done but its worker is still running: {p}" for p in false_done(files, workers)]
    flags += [f"merged worktree still present: {w['path']} ({w['branch']})" for w in snap["worktrees"]
              if w["merged"] and not w["dirty"]]
    project = project_probes.collect(args.cwd, procs, snap["docker"], now, redact=redact,
                                     exec_probes=getattr(args, "exec_probes", False))
    if project is not None:  # no probe file: snapshot and output stay exactly as before
        snap["project"] = project
        flags += project_probes.flags(project)
    snap["flags"] = flags
    return snap


def markdown(s: dict, max_tasks: int = 15) -> str:
    workers = [p for p in s["processes"] if p["bucket"] == "worker"]
    live = [t for t in s["tasks"] if t["status"] in ("active", "quiet") and t["age_s"] < 86400]
    mem, g = s["memory"], s["gpu"]
    lines = [f"# Background status ({s['taken']})", "",
             f"{len(workers)} workers | {len(live)} live/quiet Claude tasks | "
             + (f"GPU {g['util']}% {g['used_mib']}/{g['total_mib']} MiB | " if g else "GPU n/a | ")
             + (f"RAM {mem['free_gb']}/{mem['total_gb']} GB free | " if mem else "")
             + ("Docker down" if s["docker"] is None else f"{len(s['docker'])} containers"), ""]
    lines += ["## Flags", ""] + ([f"- {f}" for f in s["flags"]] or ["- none"]) + [""]
    lines += project_probes.markdown(s.get("project"), age)
    lines += ["## Claude Code background tasks", "", "| Task | Session | Status | Last write | Last line |", "|---|---|---|---|---|"]
    for t in s["tasks"][:max_tasks]:
        lines.append(f"| {t['task']} | {t['session']} | {t['status']} | {age(t['age_s'])} | {t['last'].replace('|', '/')} |")
    if len(s["tasks"]) > max_tasks:
        lines.append(f"| ... {len(s['tasks']) - max_tasks} older | | | | |")
    lines += ["", "## Workers (detached processes)", "", "| PID | Parent | Age | RAM GB | Command |", "|---|---|---|---|---|"]
    for p in workers:
        lines.append(f"| {p['pid']} | {p['ppid']} | {age(p['age_s'])} | {p['gb']} | `{p['cmd']}` |")
    infra = [p for p in s["processes"] if p["bucket"] == "infrastructure"]
    lines += ["", f"Infrastructure processes (MCP servers, language servers): {len(infra)}, "
              f"{round(sum(p['gb'] for p in infra), 2)} GB.", ""]
    if g:
        names = {p["pid"]: p["cmd"][:90] for p in s["processes"]}
        lines += [f"## GPU: {g['name']}", "", "| PID | MiB | Process |", "|---|---|---|"] + \
                 [f"| {p['pid']} | {p['mib'].replace('[N/A]', 'n/a (WDDM)')} | `{names.get(p['pid'], '')}` |"
                  for p in g["procs"]] + (["| (per-process list unavailable) | | |"] if not g["procs"] else []) + [""]
    if mem:
        lines += ["## Memory: top processes", "", "| Name | PID | GB |", "|---|---|---|"] + \
                 [f"| {t['name']} | {t['pid']} | {t['gb']} |" for t in mem["top"]] + [""]
    lines += ["## Docker", ""] + (["- daemon not reachable"] if s["docker"] is None else
                                  [f"- {c['name']}: {c['status']} ({c['image']})" for c in s["docker"]] or ["- no containers"]) + [""]
    lines += ["## Recent status and log files" + (" (partial: time budget)" if s["status_files_partial"] else ""), "",
              "| Age | File | Last line |", "|---|---|---|"]
    for f in s["status_files"][:20]:
        lines.append(f"| {age(f['age_s'])} | `{f['path']}` | {f['last'].replace('|', '/')} |")
    if s["worktrees"]:
        lines += ["", "## Git worktrees (non-main)", "", "| Repo | Branch | Dirty | Merged | Path |", "|---|---|---|---|---|"]
        for w in s["worktrees"]:
            lines.append(f"| {w['repo']} | {w['branch']} | {w['dirty']} | {w['merged']} | `{w['path']}` |")
    return "\n".join(lines) + "\n"


def default_repos_root() -> str:
    """PROJECTS_ROOT, else the folder that holds the current repository."""
    configured = os.environ.get("PROJECTS_ROOT")
    if configured:
        return configured
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return str(Path(top.stdout.strip() or os.getcwd()).parent)


def default_status_roots(repos_root: str) -> list[str]:
    return [f"{repos_root}/_wt-*/runs", f"{repos_root}/*/runs", f"{repos_root}/*/work"]


def main():
    ap = argparse.ArgumentParser(description="Read-only snapshot of background work.")
    ap.add_argument("--cwd", default=os.getcwd(), help="project directory whose Claude tasks to show")
    ap.add_argument("--all-projects", action="store_true", help="Claude tasks from every project")
    ap.add_argument("--root", action="append", help="glob for status/log roots (repeatable)")
    ap.add_argument("--hours", type=float, default=48, help="status/log files modified within this many hours")
    ap.add_argument("--repos-root", help="folder whose repos' worktrees to list (default: PROJECTS_ROOT, else the current repo's parent)")
    ap.add_argument("--no-worktrees", action="store_true")
    ap.add_argument("--exec-probes", action="store_true",
                    help="also run the project's container_ps/sql probes (docker exec, read-only, 5 s each)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    a.repos_root = a.repos_root or default_repos_root()
    a.root = a.root or default_status_roots(a.repos_root)
    snap = collect(a)
    try:   # Windows consoles default to cp1252; command lines can hold any character
        import sys
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    print(json.dumps(snap, indent=1, default=str) if a.json else markdown(snap))


if __name__ == "__main__":
    main()
