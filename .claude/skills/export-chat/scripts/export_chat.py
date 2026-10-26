#!/usr/bin/env python3
"""Export an agent chat transcript to Markdown (Claude Code, Codex, Cursor, Antigravity, Grok).

Finds the newest transcript for the workspace in the selected harness store, renders
user/assistant text plus full tool-call inputs, and writes it to a file or the clipboard.
The header carries ``Harness``, ``Transcript``, ``Workspace`` and ``Resume`` lines so
``/resume-task`` (harvest.py ``--md``) can attribute the export. Stdlib only so the skill
can be copied to any user-level skills directory and run from any project.

Stores (read-only):
- claude:      ``$CLAUDE_CONFIG_DIR|~/.claude/projects/<encoded-cwd>/<session>.jsonl``
- codex:       ``$CODEX_HOME|~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`` (``session_meta.cwd``)
- cursor:      ``~/.cursor/projects/<workspace-slug>/agent-transcripts/[<id>/]<id>.jsonl``
- antigravity: ``~/.gemini/antigravity{-cli,,-ide}/brain/<id>/.system_generated/logs/transcript_full.jsonl``
- grok:        ``$GROK_HOME|~/.grok/sessions/<url-encoded-cwd>/<id>/updates.jsonl``
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

HARNESSES = ("claude", "codex", "cursor", "antigravity", "grok")
CODEX_SCAN_LIMIT = 400
ANTIGRAVITY_SCAN_LINES = 400

WRAPPER_TAGS = (
    "agent_skills",
    "agent_transcripts",
    "attached_files",
    "git_status",
    "manually_attached_skills",
    "open_and_recently_viewed_files",
    "rules",
    "system_notification",
    "system_reminder",
    "system-reminder",
    "timestamp",
    "user_info",
    "environment_context",
    "user_instructions",
    "command-message",
    "command-args",
    "local-command-stdout",
    "local-command-stderr",
    "ide_opened_file",
    "ide_selection",
    "USER_SETTINGS_CHANGE",
    "CONTEXT_SUMMARY",
    "SYSTEM_MESSAGE",
    "ADDITIONAL_METADATA",
)
_WRAPPER_RE = re.compile(r"<(" + "|".join(re.escape(t) for t in WRAPPER_TAGS) + r")\b[^>]*>.*?</\1>", re.DOTALL)
_USER_QUERY_RE = re.compile(r"<user_query>(.*?)</user_query>", re.DOTALL)
_USER_REQUEST_RE = re.compile(r"<USER_REQUEST>(.*?)</USER_REQUEST>", re.DOTALL)
_COMMAND_NAME_RE = re.compile(r"<command-name>\s*(\S+)\s*</command-name>")
CODEX_SKIP = re.compile(r"^\s*(<environment_context>|<user_instructions>|# AGENTS\.md|<permissions|<skills_instructions>)", re.I)


class Source:
    """One transcript file. A plain class (not a dataclass) so the script also loads via spec_from_file_location."""

    def __init__(self, harness: str, path: Path, id: str, workspace: str | None = None,
                 workspace_verified: bool = True, store: str = "") -> None:
        self.harness, self.path, self.id = harness, path, id
        self.workspace, self.workspace_verified, self.store = workspace, workspace_verified, store

    @property
    def mtime(self) -> float:
        try:
            return self.path.stat().st_mtime
        except OSError:
            return 0.0


# --------------------------------------------------------------------------- helpers

def _norm(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(path))).rstrip("\\/")


def _forms(workspace: Path) -> list[Path]:
    """The workspace as launched and as resolved: junctions/symlinks (``image-scoring-pipeline`` ->
    ``image-scoring-backend``) make them differ, and harnesses record the launched path."""
    forms = [Path(os.path.abspath(workspace))]
    try:
        resolved = workspace.resolve()
        if _norm(resolved) != _norm(forms[0]):
            forms.append(resolved)
    except OSError:
        pass
    return forms


def _same_or_under(child: str | None, root: Path) -> bool:
    if not child:
        return False
    c = _norm(child)
    return any(c == r or c.startswith(r + os.sep) for r in (_norm(f) for f in _forms(root)))


def workspace_slug(workspace: Path) -> str:
    """``D:\\Projects\\my-app`` -> ``D-Projects-my-app`` (Cursor's project dir naming)."""
    return re.sub(r"[^A-Za-z0-9]+", "-", str(workspace)).strip("-")


def claude_slug(workspace: Path) -> str:
    """``D:\\Projects\\my-app`` -> ``D--Projects-my-app`` (Claude Code's project dir naming)."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(workspace))


def load_events(path: Path) -> list[dict[str, Any]]:
    events = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                events.append(obj)
    return events


def _first_json_line(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def clean_user_text(text: str, *, raw: bool) -> str:
    if raw:
        return (text or "").strip()
    reqs = _USER_REQUEST_RE.findall(text or "")
    if reqs:
        return "\n\n".join(r.strip() for r in reqs)
    queries = _USER_QUERY_RE.findall(text or "")
    if queries:
        return "\n\n".join(q.strip() for q in queries)
    text = _COMMAND_NAME_RE.sub(r"\1", text or "")
    return _WRAPPER_RE.sub("", text).strip()


# --------------------------------------------------------------------------- discovery

def find_transcript_dir(cursor_home: Path, workspace: Path) -> Path | None:
    try:
        projects = cursor_home / "projects"
        if not projects.is_dir():
            return None
        wanted = {workspace_slug(f).lower() for f in _forms(workspace)}
        for child in projects.iterdir():
            if child.is_dir() and child.name.lower() in wanted:
                transcripts = child / "agent-transcripts"
                if transcripts.is_dir():
                    return transcripts
    except OSError:
        return None
    return None


def list_transcripts(transcript_dir: Path) -> list[Path]:
    """All Cursor transcripts (nested ``<uuid>/<uuid>.jsonl`` and flat ``<uuid>.jsonl``), newest first."""
    found = {p for p in transcript_dir.glob("*.jsonl")}
    found |= {p for p in transcript_dir.glob("*/*.jsonl") if p.stem == p.parent.name}
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def cursor_sources(cursor_home: Path, workspace: Path) -> list[Source]:
    tdir = find_transcript_dir(cursor_home, workspace)
    if tdir is None:
        return []
    return [Source("cursor", p, p.stem, str(workspace)) for p in list_transcripts(tdir)]


def claude_sources(claude_home: Path, workspace: Path) -> list[Source]:
    projects = claude_home / "projects"
    wanted = {claude_slug(f).lower() for f in _forms(workspace)}
    out: list[Source] = []
    try:
        dirs = [d for d in projects.iterdir() if d.is_dir() and d.name.lower() in wanted]
    except OSError:
        return []
    for d in dirs:
        out += [Source("claude", p, p.stem, str(workspace)) for p in d.glob("*.jsonl")]
    current = os.environ.get("CLAUDE_CODE_SESSION_ID")
    out.sort(key=lambda s: (s.id == current, s.mtime), reverse=True)
    return out


def codex_sources(codex_home: Path, workspace: Path, *, any_workspace: bool = False) -> list[Source]:
    sessions = codex_home / "sessions"
    try:
        files = sorted(sessions.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return []
    out: list[Source] = []
    for p in files[:CODEX_SCAN_LIMIT]:
        meta = _first_json_line(p)
        payload = meta.get("payload") if meta.get("type") == "session_meta" else {}
        cwd = (payload or {}).get("cwd")
        if any_workspace or _same_or_under(cwd, workspace):
            sid = (payload or {}).get("id") or p.stem.replace("rollout-", "")
            out.append(Source("codex", p, sid, cwd or None, cwd is not None))
    return out


ANTIGRAVITY_STORES = (("antigravity-cli", "antigravity-cli"), ("antigravity", "antigravity-ide"),
                      ("antigravity-ide", "antigravity-ide"))


def find_antigravity_transcripts(gemini_home: Path) -> list[Path]:
    found: list[Path] = []
    for store, _ in ANTIGRAVITY_STORES:
        brain = gemini_home / store / "brain"
        try:
            children = list(brain.iterdir()) if brain.is_dir() else []
        except OSError:
            continue
        for conv in children:
            try:
                logs = conv / ".system_generated" / "logs"
                for name in ("transcript_full.jsonl", "transcript.jsonl"):
                    if (logs / name).is_file():
                        found.append(logs / name)
                        break
            except OSError:
                continue
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def _antigravity_mentions(path: Path, workspace: Path) -> bool:
    """Antigravity lines carry no cwd; look for the workspace path in tool-call arguments."""
    needles = {n for f in _forms(workspace) for n in (_norm(f), _norm(f).replace("\\", "/"))}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= ANTIGRAVITY_SCAN_LINES:
                    break
                if '"tool_calls"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for tc in obj.get("tool_calls") or []:
                    blob = os.path.normcase(json.dumps(tc.get("args") or {})).replace("\\\\", "\\")
                    if any(n in blob or n in blob.replace("\\", "/") for n in needles):
                        return True
    except OSError:
        return False
    return False


def antigravity_sources(gemini_home: Path, workspace: Path, *, any_workspace: bool = False,
                        allow_unverified: bool = False) -> list[Source]:
    out: list[Source] = []
    for p in find_antigravity_transcripts(gemini_home):
        conv = p.parent.parent.parent
        store = conv.parent.parent.name
        label = dict(ANTIGRAVITY_STORES).get(store, store)
        verified = _antigravity_mentions(p, workspace)
        if verified or any_workspace:
            out.append(Source("antigravity", p, conv.name, str(workspace) if verified else None, verified, label))
    if not out and allow_unverified:
        # Fresh conversations may not have touched a workspace path yet: offer the newest, unverified.
        newest = find_antigravity_transcripts(gemini_home)[:1]
        for p in newest:
            conv = p.parent.parent.parent
            label = dict(ANTIGRAVITY_STORES).get(conv.parent.parent.name, conv.parent.parent.name)
            out.append(Source("antigravity", p, conv.name, None, False, label))
    return out


def grok_sources(grok_home: Path, workspace: Path, *, any_workspace: bool = False) -> list[Source]:
    sessions = grok_home / "sessions"
    out: list[Source] = []
    try:
        cwd_dirs = [d for d in sessions.iterdir() if d.is_dir()]
    except OSError:
        return []
    for d in cwd_dirs:
        cwd = unquote(d.name)
        if not any_workspace and _norm(cwd) not in {_norm(f) for f in _forms(workspace)}:
            continue
        for s in d.iterdir():
            log = s / "updates.jsonl"
            if not log.is_file():
                log = s / "chat_history.jsonl"
            if log.is_file():
                out.append(Source("grok", log, s.name, cwd))
    return sorted(out, key=lambda s: s.mtime, reverse=True)


def discover(harness: str, workspace: Path, homes: dict[str, Path], *, any_workspace: bool = False,
             explicit: bool = False) -> list[Source]:
    if harness == "cursor":
        return cursor_sources(homes["cursor"], workspace)
    if harness == "claude":
        return claude_sources(homes["claude"], workspace)
    if harness == "codex":
        return codex_sources(homes["codex"], workspace, any_workspace=any_workspace)
    if harness == "antigravity":
        return antigravity_sources(homes["gemini"], workspace, any_workspace=any_workspace,
                                   allow_unverified=explicit)
    if harness == "grok":
        return grok_sources(homes["grok"], workspace, any_workspace=any_workspace)
    raise ValueError(f"unknown harness: {harness}")


def detect_harness() -> str | None:
    """Only signals verified on this setup. Anything else must pass --harness explicitly."""
    if os.environ.get("CLAUDECODE") == "1":
        return "claude"
    return None


def resolve_transcript(ref: str, candidates) -> Path | None:
    """``ref`` is a path or an id prefix. ``candidates`` is a Cursor transcript dir or a list of sources/paths."""
    path = Path(ref).expanduser()
    if path.is_file():
        return path
    if candidates is None:
        return None
    if isinstance(candidates, Path):
        candidates = list_transcripts(candidates)
    matches = []
    for c in candidates:
        if isinstance(c, Source):
            if c.id.startswith(ref):
                matches.append(c.path)
        elif c.stem.startswith(ref) or any(part.startswith(ref) for part in c.parts[-4:]):
            matches.append(c)
    return matches[0] if len(matches) == 1 else None


# --------------------------------------------------------------------------- normalization

def detect_format(events: list[dict[str, Any]]) -> str:
    for ev in events[:20]:
        if "step_index" in ev or ev.get("source") in ("USER_EXPLICIT", "MODEL"):
            return "antigravity"
        if ev.get("method") in ("session/update", "_x.ai/session/update"):
            return "grok"
        if ev.get("type") in ("session_meta", "response_item", "event_msg", "turn_context") and "payload" in ev:
            return "codex"
        if "sessionId" in ev and ev.get("type") in ("user", "assistant", "summary", "system"):
            return "claude"
    for ev in events[:20]:
        if ev.get("type") in ("user", "assistant", "system", "tool_result", "reasoning") and "role" not in ev:
            return "grok"
    return "cursor"


def is_antigravity(events: list[dict[str, Any]]) -> bool:
    return detect_format(events) == "antigravity"


def _blocks(event: dict[str, Any]) -> list[dict[str, Any]]:
    content = (event.get("message") or {}).get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [b for b in content or [] if isinstance(b, dict)]


def _json_args(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _entries_cursor(events, raw):
    for event in events:
        if event.get("type") == "turn_ended":
            yield ("turn",)
            continue
        role = event.get("role")
        if role not in ("user", "assistant"):
            continue
        for block in _blocks(event):
            kind = block.get("type")
            if kind == "text":
                text = block.get("text", "")
                text = clean_user_text(text, raw=raw) if role == "user" else text.strip()
                if text:
                    yield (role, text)
            elif kind == "tool_use":
                yield ("tool", block.get("name", "?"), block.get("input", {}))


def _entries_antigravity(events, raw):
    seen_user = False
    for ev in events:
        source, ev_type = ev.get("source"), ev.get("type")
        if ev_type == "USER_INPUT" or source == "USER_EXPLICIT":
            text = clean_user_text(ev.get("content", ""), raw=raw)
            if text:
                if seen_user:
                    yield ("turn",)
                seen_user = True
                yield ("user", text)
        elif source == "MODEL" and ev_type == "PLANNER_RESPONSE":
            content = (ev.get("content") or "").strip()
            if content:
                yield ("assistant", content)
            for tc in ev.get("tool_calls") or []:
                yield ("tool", tc.get("name", "unknown"), tc.get("args", {}))
        # GENERIC steps are tool outputs and SYSTEM steps are injected context: not exported.
    if seen_user:
        yield ("turn",)


def _entries_claude(events, raw):
    seen_user = False
    for ev in events:
        typ = ev.get("type")
        if typ not in ("user", "assistant") or ev.get("isSidechain") or ev.get("isMeta") or ev.get("isCompactSummary"):
            continue
        msg = ev.get("message") or {}
        content = msg.get("content")
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else [b for b in content or [] if isinstance(b, dict)]
        for b in blocks:
            kind = b.get("type")
            if kind == "text":
                text = b.get("text", "")
                if typ == "user":
                    text = clean_user_text(text, raw=raw)
                    if not text or text.startswith("Caveat: The messages below") or "[Request interrupted" in text:
                        continue
                    if seen_user:
                        yield ("turn",)
                    seen_user = True
                    yield ("user", text)
                elif text.strip():
                    yield ("assistant", text.strip())
            elif kind == "tool_use" and typ == "assistant":
                yield ("tool", b.get("name", "?"), b.get("input", {}))
    if seen_user:
        yield ("turn",)


def _entries_codex(events, raw):
    items = [ev for ev in events if ev.get("type") == "response_item"]
    has_messages = any((ev.get("payload") or {}).get("type") == "message" for ev in items)
    seen_user = False
    if not has_messages:  # older rollouts: event_msg only
        for ev in events:
            p = ev.get("payload") or {}
            if ev.get("type") != "event_msg":
                continue
            if p.get("type") == "user_message" and p.get("message"):
                text = clean_user_text(p["message"], raw=raw)
                if text and not CODEX_SKIP.match(text):
                    if seen_user:
                        yield ("turn",)
                    seen_user = True
                    yield ("user", text)
            elif p.get("type") == "agent_message" and p.get("message"):
                yield ("assistant", p["message"].strip())
        if seen_user:
            yield ("turn",)
        return
    for ev in items:
        p = ev.get("payload") or {}
        pt = p.get("type")
        if pt == "message" and p.get("role") in ("user", "assistant"):
            text = "\n".join(c.get("text", "") for c in p.get("content") or [] if isinstance(c, dict)).strip()
            if p["role"] == "user":
                if not text or CODEX_SKIP.match(text):
                    continue
                text = clean_user_text(text, raw=raw)
                if not text:
                    continue
                if seen_user:
                    yield ("turn",)
                seen_user = True
            if text:
                yield (p["role"], text)
        elif pt == "function_call":
            yield ("tool", p.get("name", "?"), _json_args(p.get("arguments")))
        elif pt == "custom_tool_call":
            yield ("tool", p.get("name", "?"), _json_args(p.get("input")))
        elif pt == "local_shell_call":
            yield ("tool", "local_shell", p.get("action") or {})
    if seen_user:
        yield ("turn",)


def _entries_grok(events, raw):
    if events and "method" not in events[0] and detect_format(events) == "grok":
        # chat_history.jsonl fallback: raw model messages
        seen_user = False
        for ev in events:
            typ = ev.get("type")
            if typ == "user" and "synthetic_reason" not in ev:
                text = clean_user_text("\n".join(b.get("text", "") for b in ev.get("content") or [] if isinstance(b, dict)), raw=raw)
                if text:
                    if seen_user:
                        yield ("turn",)
                    seen_user = True
                    yield ("user", text)
            elif typ == "assistant":
                if isinstance(ev.get("content"), str) and ev["content"].strip():
                    yield ("assistant", ev["content"].strip())
                for tc in ev.get("tool_calls") or []:
                    fn = tc.get("function") or tc
                    yield ("tool", fn.get("name", "?"), _json_args(fn.get("arguments")))
        if seen_user:
            yield ("turn",)
        return
    buf_role, buf = None, []

    def flush():
        if buf_role and "".join(buf).strip():
            text = "".join(buf)
            return (buf_role, clean_user_text(text, raw=raw) if buf_role == "user" else text.strip())
        return None

    for ev in events:
        update = (ev.get("params") or {}).get("update") or {}
        kind = update.get("sessionUpdate")
        if kind in ("user_message_chunk", "agent_message_chunk"):
            role = "user" if kind == "user_message_chunk" else "assistant"
            if role != buf_role:
                item = flush()
                if item:
                    yield item
                buf_role, buf = role, []
            buf.append(((update.get("content") or {}).get("text")) or "")
        elif kind == "tool_call":
            item = flush()
            if item:
                yield item
            buf_role, buf = None, []
            tool = ((update.get("_meta") or {}).get("x.ai/tool") or {}).get("name") or update.get("title") or "?"
            yield ("tool", tool, update.get("rawInput") or {})
        elif kind == "turn_completed":
            item = flush()
            if item:
                yield item
            buf_role, buf = None, []
            yield ("turn",)
    item = flush()
    if item:
        yield item


NORMALIZERS = {
    "cursor": _entries_cursor,
    "antigravity": _entries_antigravity,
    "claude": _entries_claude,
    "codex": _entries_codex,
    "grok": _entries_grok,
}


def entries(events: list[dict[str, Any]], *, raw: bool = False, harness: str | None = None):
    return list(NORMALIZERS[harness or detect_format(events)](events, raw))


def first_prompt(events: list[dict[str, Any]], harness: str | None = None) -> str:
    for item in entries(events, harness=harness):
        if item[0] == "user":
            return item[1]
    return ""


# --------------------------------------------------------------------------- rendering

def _fence(body: str) -> str:
    longest = max((len(m) for m in re.findall(r"`+", body)), default=0)
    return "`" * max(3, longest + 1)


def resume_command(harness: str, transcript_id: str, store: str = "") -> str | None:
    if not transcript_id:
        return None
    if harness == "claude":
        return f"claude --resume {transcript_id}"
    if harness == "codex":
        return f"codex resume {transcript_id}"
    if harness == "grok":
        return f"grok --resume {transcript_id}"
    if harness == "antigravity" and store == "antigravity-cli":
        return f"agy --conversation {transcript_id}"
    return None


def render_markdown(
    events: list[dict[str, Any]],
    *,
    transcript_id: str,
    workspace: str,
    raw: bool = False,
    exported_at: datetime | None = None,
    harness: str | None = None,
    store: str = "",
) -> tuple[str, dict[str, int]]:
    harness = harness or detect_format(events)
    exported_at = exported_at or datetime.now().astimezone()
    out = [
        "# Chat export",
        "",
        f"- Harness: {harness}" + (f" ({store})" if store and store != harness else ""),
        f"- Transcript: `{transcript_id}`",
        f"- Workspace: `{workspace}`",
        f"- Exported: {exported_at.isoformat(timespec='seconds')}",
    ]
    resume = resume_command(harness, transcript_id, store)
    if resume:
        out.append(f"- Resume: `{resume}`")
    out.append("")
    stats = {"user_messages": 0, "assistant_messages": 0, "tool_calls": 0, "turns": 0}
    last_role = None
    assistant_open = False

    for item in entries(events, raw=raw, harness=harness):
        kind = item[0]
        if kind == "turn":
            stats["turns"] += 1
            out += ["---", ""]
            last_role, assistant_open = None, False
            continue
        if kind == "tool":
            stats["tool_calls"] += 1
            args = item[2]
            body = args if isinstance(args, str) else json.dumps(args, indent=2, ensure_ascii=False)
            fence = _fence(body)
            part = f"**Tool: {item[1]}**\n\n{fence}{'' if isinstance(args, str) else 'json'}\n{body}\n{fence}"
            role = "assistant"
        else:
            role, part = kind, item[1]
        if role == "user" or not assistant_open:
            stats[f"{role}_messages"] += 1
        assistant_open = role == "assistant"
        if role != last_role:
            out += [f"## {role.capitalize()}", ""]
            last_role = role
        out += [part, ""]

    return "\n".join(out).rstrip() + "\n", stats


def default_filename(prompt: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")[:50].rstrip("-")
    return f"{now:%Y-%m-%d-%H%M%S}-{slug or 'chat'}.md"


def copy_to_clipboard(text: str) -> str:
    """Copy *text*; return the tool used. Raises RuntimeError when none is available."""
    if sys.platform == "win32":
        subprocess.run(["clip"], input=text.encode("utf-16"), check=True)
        return "clip"
    candidates = [
        ["pbcopy"],
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
    ]
    for cmd in candidates:
        if shutil.which(cmd[0]):
            subprocess.run(cmd, input=text.encode("utf-8"), check=True)
            return cmd[0]
    raise RuntimeError("no clipboard tool found (pbcopy, wl-copy, xclip, xsel)")


def _emit(data: dict[str, Any], *, as_json: bool, message: str) -> None:
    if as_json:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print(message)


def _protected(homes: dict[str, Path]) -> list[Path]:
    return [p for p in homes.values()] + [Path.home() / "AppData/Roaming/Cursor/User"]


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", nargs="?", help="Output file (default: timestamped .md in cwd)")
    parser.add_argument("--harness", choices=(*HARNESSES, "auto"), default="auto",
                        help="Harness whose transcript to export (auto: detect, else require one store)")
    parser.add_argument("--clipboard", action="store_true", help="Copy to clipboard instead of a file")
    parser.add_argument("--transcript", help="Transcript id (prefix ok) or .jsonl path")
    parser.add_argument("--workspace", type=Path, default=None, help="Workspace path (default: cwd)")
    parser.add_argument("--any-workspace", action="store_true", help="Do not filter by workspace (codex/antigravity/grok)")
    parser.add_argument("--cursor-home", type=Path, default=Path.home() / ".cursor")
    parser.add_argument("--claude-home", type=Path, default=Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude"))
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"))
    parser.add_argument("--gemini-home", type=Path, default=Path.home() / ".gemini")
    parser.add_argument("--grok-home", type=Path, default=Path(os.environ.get("GROK_HOME") or Path.home() / ".grok"))
    parser.add_argument("--list", action="store_true", help="List recent transcripts and exit")
    parser.add_argument("--limit", type=int, default=10, help="Rows for --list")
    parser.add_argument("--raw", action="store_true", help="Keep injected wrapper tags in user messages")
    parser.add_argument("--json", action="store_true", help="Print a JSON result summary")
    args = parser.parse_args(argv)

    workspace = Path(os.path.abspath(args.workspace or Path.cwd()))  # not resolve(): keep the launched path
    homes = {"cursor": args.cursor_home, "claude": args.claude_home, "codex": args.codex_home,
             "gemini": args.gemini_home, "grok": args.grok_home}

    def fail(msg: str) -> int:
        _emit({"ok": False, "error": msg}, as_json=args.json, message=f"error: {msg}")
        return 1

    harness = args.harness if args.harness != "auto" else detect_harness()
    selected = [harness] if harness else list(HARNESSES)
    sources: list[Source] = []
    for name in selected:
        sources += discover(name, workspace, homes, any_workspace=args.any_workspace,
                            explicit=args.harness == name)
    sources.sort(key=lambda s: s.mtime, reverse=True)

    if args.list:
        rows = []
        for src in sources[: args.limit]:
            prompt = first_prompt(load_events(src.path), src.harness).splitlines()
            rows.append({
                "harness": src.harness,
                "id": src.id,
                "modified": datetime.fromtimestamp(src.mtime).isoformat(timespec="seconds"),
                "workspace_verified": src.workspace_verified,
                "first_prompt": prompt[0][:80] if prompt else "",
                "path": str(src.path),
            })
        lines = [f"{r['modified']}  [{r['harness']}]  {r['id']}  {r['first_prompt']}" for r in rows]
        _emit({"ok": True, "transcripts": rows}, as_json=args.json, message="\n".join(lines))
        return 0

    chosen: Source | None = None
    if args.transcript:
        path = resolve_transcript(args.transcript, sources)
        if path is None:
            return fail(f"transcript not found or ambiguous: {args.transcript}")
        chosen = next((s for s in sources if s.path == path), None)
        if chosen is None:
            fmt = detect_format(load_events(path))
            chosen = Source(fmt, path, path.stem, str(workspace))
    else:
        if not sources:
            where = harness or "any harness"
            return fail(f"no transcripts for workspace {workspace} in {where}; pass --harness, --transcript or --workspace")
        harnesses_found = sorted({s.harness for s in sources})
        if not harness and len(harnesses_found) > 1:
            return fail("transcripts found in several harnesses (" + ", ".join(harnesses_found)
                        + "); pass --harness with the harness running this chat")
        chosen = sources[0]

    events = load_events(chosen.path)
    markdown, stats = render_markdown(
        events, transcript_id=chosen.id, workspace=str(workspace), raw=args.raw,
        harness=chosen.harness, store=chosen.store,
    )
    result: dict[str, Any] = {"ok": True, "harness": chosen.harness, "transcript": str(chosen.path),
                              "workspace_verified": chosen.workspace_verified, **stats}

    if args.clipboard:
        try:
            result["clipboard"] = copy_to_clipboard(markdown)
        except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
            return fail(f"clipboard copy failed: {exc}")
        _emit(result, as_json=args.json, message=f"Copied {chosen.id} to clipboard")
        return 0

    output = Path(args.output) if args.output else Path.cwd() / default_filename(first_prompt(events, chosen.harness))
    output = output.expanduser().resolve()
    for store in _protected(homes):
        try:
            if output.is_relative_to(store.expanduser().resolve()):
                return fail(f"refusing to write inside a harness store: {store}")
        except OSError:
            continue
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    result["output"] = str(output)
    _emit(result, as_json=args.json, message=f"Exported {chosen.id} to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
