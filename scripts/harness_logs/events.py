"""Tool-call and permission events per harness, read from local transcripts.

What each store can tell (verified against real stores, 2026-10-24):

- claude:      every tool_use with its tool_result. Denials carry fixed texts (rule, auto-mode
               classifier, hook, user). An allowed call does not record whether a prompt was shown.
- codex:       function/custom tool calls. ``sandbox_permissions=require_escalated`` marks an
               escalation request; ``Rejected(...)`` / ``aborted by user`` in the output mark denials.
               ``thread_settings_applied`` / ``turn_context`` give approval_policy and approvals_reviewer.
- cursor:      agent-transcripts store tool *inputs* only: outcome is ``unknown``.
- antigravity: ``run_command.BypassSandbox=true`` is an escalation request; step status ERROR marks failures.
- grok:        ``events.jsonl`` ``turn_started.yolo_mode`` is the always-approve flag; ``hook_execution``
               updates record hook runs.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterator
from urllib.parse import unquote

from .common import Event, Homes, clip, iso, mtime, read_json, read_jsonl

CLAUDE_MARKERS = (
    ("user_rejected", re.compile(r"doesn't want to proceed with this tool use|The user rejected|user denied", re.I)),
    ("rule_denied", re.compile(r"Permission to use \S+ (?:with [^\n]{0,300}? )?has been denied|denied by (?:your )?permission (?:settings|rules)", re.I)),
    ("auto_denied", re.compile(r"denied by the Claude Code auto mode classifier|auto mode classifier gave no verdict|auto mode cannot determine", re.I)),
    ("hook_blocked", re.compile(r"(?:PreToolUse|PermissionRequest):\S* hook error|blocked by (?:a |the )?\S* ?hook|<tool_use_error>Blocked:", re.I)),
)
CLAUDE_REASON = re.compile(r"Reason: \[?([^\].]{3,80})\]?|hook error: ([^\n]{3,120})", re.I)
SHELL_TOOLS = {"Bash", "PowerShell", "Shell", "run_command", "run_terminal_command", "exec_command", "shell",
               "local_shell", "terminal"}


def _command_of(tool: str, inp) -> str:
    if isinstance(inp, str):
        return inp
    if not isinstance(inp, dict):
        return ""
    for key in ("command", "cmd", "CommandLine", "commandLine"):
        value = inp.get(key)
        if isinstance(value, list):
            return " ".join(str(v) for v in value)
        if isinstance(value, str):
            return value
    for key in ("file_path", "path", "Path", "TargetFile", "target_file", "url", "pattern", "query"):
        if isinstance(inp.get(key), str):
            return f"{key}={inp[key]}"
    return json.dumps(inp, ensure_ascii=False)[:300]


# --------------------------------------------------------------------------- Claude Code

def claude_events(homes: Homes, since: datetime) -> Iterator[Event]:
    root = homes.claude / "projects"
    if not root.is_dir():
        return
    seen: set[str] = set()  # resumed/compacted sessions re-log earlier tool_use ids in a new file
    files = sorted((p for p in root.rglob("*.jsonl") if mtime(p) >= since), key=mtime)
    for path in files:
        pending: dict[str, Event] = {}
        mode = None
        for o in read_jsonl(path):
            mode = o.get("permissionMode") or mode
            msg = o.get("message") if isinstance(o.get("message"), dict) else {}
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    if b.get("id") in seen:
                        continue
                    seen.add(b.get("id", ""))
                    name = str(b.get("name") or "?")
                    pending[b.get("id", "")] = Event(
                        harness="claude", session=o.get("sessionId") or path.stem, tool=name,
                        command=clip(_command_of(name, b.get("input"))), cwd=o.get("cwd"),
                        ts=iso(o.get("timestamp")), mode=mode, source=str(path))
                elif b.get("type") == "tool_result":
                    ev = pending.pop(b.get("tool_use_id", ""), None)
                    if ev is None:
                        continue
                    text = b.get("content")
                    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
                    head = text[:600]
                    if b.get("is_error"):
                        for outcome, rx in CLAUDE_MARKERS:
                            if rx.search(head):
                                ev.outcome = outcome
                                m = CLAUDE_REASON.search(head)
                                ev.detail = clip((m.group(1) or m.group(2)) if m else "", 160)
                                break
                    yield ev
        yield from pending.values()


# --------------------------------------------------------------------------- Codex

CODEX_EXEC_IN_JS = re.compile(r"exec_command\(\{\s*cmd\s*:\s*\"((?:[^\"\\]|\\.)*)\"")


def codex_events(homes: Homes, since: datetime) -> Iterator[Event]:
    files: list[Path] = []
    for sub in ("sessions", "archived_sessions"):
        d = homes.codex / sub
        if d.is_dir():
            files += [p for p in d.rglob("rollout-*.jsonl") if mtime(p) >= since]
    for path in files:
        session, cwd, mode = path.stem.replace("rollout-", ""), None, None
        pending: dict[str, Event] = {}
        for o in read_jsonl(path):
            typ, p = o.get("type"), o.get("payload")
            p = p if isinstance(p, dict) else {}
            if typ == "session_meta":
                session, cwd = p.get("id") or session, p.get("cwd") or cwd
            elif typ == "turn_context":
                cwd = p.get("cwd") or cwd
                mode = "/".join(str(x) for x in (p.get("approval_policy"), p.get("approvals_reviewer")) if x) or mode
            elif typ == "event_msg" and p.get("type") == "thread_settings_applied":
                ts_ = p.get("thread_settings") or {}
                mode = "/".join(str(x) for x in (ts_.get("approval_policy"), ts_.get("approvals_reviewer")) if x) or mode
            elif typ == "response_item" and p.get("type") in ("function_call", "custom_tool_call", "local_shell_call"):
                name = str(p.get("name") or p.get("type"))
                raw = p.get("arguments") if p.get("type") == "function_call" else p.get("input") or p.get("action")
                args = raw
                if isinstance(raw, str):
                    try:
                        args = json.loads(raw)
                    except json.JSONDecodeError:
                        args = raw
                command = _command_of(name, args)
                if isinstance(raw, str) and name == "exec":  # JS cell; shell runs only via tools.exec_command
                    found = []
                    for m in CODEX_EXEC_IN_JS.findall(raw):
                        try:
                            found.append(json.loads(f'"{m}"'))
                        except json.JSONDecodeError:
                            found.append(m)
                    if found:
                        command = "\n".join(found)
                    else:
                        name, command = "exec(js)", clip(raw, 200)
                escalated = isinstance(args, dict) and args.get("sandbox_permissions") == "require_escalated" \
                    or isinstance(raw, str) and '"require_escalated"' in raw
                ev = Event(harness="codex", session=session, tool=name, command=clip(command),
                           cwd=(args.get("workdir") if isinstance(args, dict) else None) or cwd,
                           ts=iso(o.get("timestamp")), mode=mode, source=str(path),
                           outcome="escalation_requested" if escalated else "allowed",
                           detail=clip(args.get("justification", ""), 160) if isinstance(args, dict) else "")
                pending[p.get("call_id") or p.get("id") or str(len(pending))] = ev
            elif typ == "response_item" and p.get("type") in ("function_call_output", "custom_tool_call_output"):
                ev = pending.pop(p.get("call_id", ""), None)
                if ev is None:
                    continue
                out = p.get("output")
                out = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
                head = out[:800]
                if "Automatic approval review failed" in head or "Rejected(" in head and "review" in head:
                    ev.outcome, ev.detail = "auto_denied", "auto_review rejected"
                elif re.search(r"rejected by (?:the )?user|aborted by user|user denied", head, re.I):
                    ev.outcome = "user_rejected"
                elif "Rejected(" in head:
                    ev.outcome = "rule_denied"
                yield ev
        yield from pending.values()


def codex_persisted_grants(homes: Homes) -> Iterator[dict]:
    """``rules/*.rules``: ``prefix_rule(pattern=[...], decision="allow")`` written by "always allow"."""
    rx = re.compile(r"prefix_rule\(\s*pattern\s*=\s*(\[.*?\])\s*,\s*decision\s*=\s*\"(\w+)\"", re.S)
    for path in sorted((homes.codex / "rules").glob("*.rules")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern, decision in rx.findall(text):
            try:
                tokens = json.loads(pattern)
            except json.JSONDecodeError:
                tokens = [pattern]
            yield {"file": str(path), "decision": decision, "pattern": [str(t) for t in tokens]}


# --------------------------------------------------------------------------- Cursor

def cursor_events(homes: Homes, since: datetime) -> Iterator[Event]:
    root = homes.cursor / "projects"
    if not root.is_dir():
        return
    for proj in root.iterdir():
        tdir = proj / "agent-transcripts"
        if not tdir.is_dir():
            continue
        files = {p for p in tdir.glob("*.jsonl")} | {p for p in tdir.glob("*/*.jsonl") if p.stem == p.parent.name}
        for path in files:
            if mtime(path) < since:
                continue
            ts = mtime(path).isoformat()
            for o in read_jsonl(path):
                if o.get("role") != "assistant":
                    continue
                content = (o.get("message") or {}).get("content") or []
                for b in content if isinstance(content, list) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        name = str(b.get("name") or "?")
                        yield Event(harness="cursor", session=path.stem, tool=name,
                                    command=clip(_command_of(name, b.get("input"))), cwd=proj.name,
                                    ts=ts, outcome="unknown", source=str(path))


# --------------------------------------------------------------------------- Antigravity

def antigravity_events(homes: Homes, since: datetime) -> Iterator[Event]:
    for store in ("antigravity-cli", "antigravity", "antigravity-ide"):
        brain = homes.gemini / store / "brain"
        if not brain.is_dir():
            continue
        for conv in brain.iterdir():
            logs = conv / ".system_generated" / "logs"
            path = logs / "transcript_full.jsonl"
            if not path.is_file():
                path = logs / "transcript.jsonl"
            if not path.is_file() or mtime(path) < since:
                continue
            last: list[Event] = []
            for o in read_jsonl(path):
                if o.get("source") == "MODEL" and o.get("type") == "PLANNER_RESPONSE":
                    last = []
                    for tc in o.get("tool_calls") or []:
                        name = str(tc.get("name") or "?")
                        args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
                        ev = Event(harness="antigravity", session=conv.name, tool=name, mode=store,
                                   command=clip(_command_of(name, args)), ts=iso(o.get("created_at")),
                                   cwd=args.get("Cwd"), source=str(path),
                                   outcome="escalation_requested" if args.get("BypassSandbox") else "allowed",
                                   detail=clip(str(args.get("toolSummary") or ""), 160))
                        last.append(ev)
                elif o.get("type") == "GENERIC" and last:
                    ev = last.pop(0)
                    content = (o.get("content") or "")[:600]
                    if o.get("status") == "ERROR" and re.search(r"permission|denied|rejected|not allowed", content, re.I):
                        ev.outcome, ev.detail = "rule_denied", clip(content, 160)
                    yield ev
            yield from last


# --------------------------------------------------------------------------- Grok

def grok_events(homes: Homes, since: datetime) -> Iterator[Event]:
    root = homes.grok / "sessions"
    if not root.is_dir():
        return
    for cwd_dir in root.iterdir():
        if not cwd_dir.is_dir():
            continue
        cwd = unquote(cwd_dir.name)
        for sdir in cwd_dir.iterdir():
            updates = sdir / "updates.jsonl"
            if not updates.is_file() or mtime(updates) < since:
                continue
            yolo = None
            for o in read_jsonl(sdir / "events.jsonl"):
                if o.get("type") == "turn_started" and "yolo_mode" in o:
                    yolo = bool(o["yolo_mode"])
            mode = "always-approve" if yolo else ("ask/auto" if yolo is False else None)
            for o in read_jsonl(updates):
                u = (o.get("params") or {}).get("update") or {}
                kind = u.get("sessionUpdate")
                if kind == "current_mode_update":
                    mode = u.get("currentModeId") or mode
                elif kind == "tool_call":
                    meta = (u.get("_meta") or {}).get("x.ai/tool") or {}
                    name = str(meta.get("name") or u.get("title") or "?")
                    yield Event(harness="grok", session=sdir.name, tool=name, mode=mode, cwd=cwd,
                                command=clip(_command_of(name, u.get("rawInput"))), ts=iso(o.get("timestamp")),
                                outcome="auto_allowed" if yolo else "allowed", source=str(updates),
                                detail="read_only" if meta.get("read_only") else "")
                elif kind == "hook_execution":
                    for run in u.get("runs") or []:
                        status = (run.get("status") or {}).get("status")
                        if status in ("success", None):
                            continue
                        yield Event(harness="grok", session=sdir.name, tool="hook", kind="hook", mode=mode,
                                    cwd=cwd, ts=iso(o.get("timestamp")), source=str(updates),
                                    outcome="hook_blocked" if status in ("deny", "denied", "blocked") else "allowed",
                                    detail=clip(f"{u.get('event_name')}: {run.get('name')} {status}", 160))


READERS = {
    "claude": claude_events,
    "codex": codex_events,
    "cursor": cursor_events,
    "antigravity": antigravity_events,
    "grok": grok_events,
}


def iter_events(homes: Homes, since: datetime, harnesses=READERS) -> Iterator[Event]:
    for name in harnesses:
        yield from READERS[name](homes, since)


def summary_by_harness(events) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for ev in events:
        row = out.setdefault(ev.harness, {})
        row[ev.outcome] = row.get(ev.outcome, 0) + 1
        row["total"] = row.get("total", 0) + 1
    return out


__all__ = ["READERS", "iter_events", "codex_persisted_grants", "summary_by_harness", "read_json"]
