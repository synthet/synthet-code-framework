"""Shared model and read-only helpers for harness transcript/config parsing.

Readers never write to a harness store. Live SQLite databases are opened ``mode=ro``;
if the owning app holds a lock, the database is copied to a temp dir first.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

log = logging.getLogger("harness_logs")
UTC = timezone.utc
MAX_COMMAND = 2000

HARNESSES = ("claude", "codex", "cursor", "antigravity", "grok")

# Outcomes a tool call can have, as far as the transcript shows it.
OUTCOMES = (
    "allowed",              # ran; the transcript does not say whether a prompt was shown
    "auto_allowed",         # ran under an always-approve / yolo mode
    "escalation_requested",  # asked to run outside the sandbox (approved, since it ran)
    "user_rejected",        # the user declined a prompt or aborted the call
    "rule_denied",          # a deny rule refused it
    "auto_denied",          # a native AI reviewer / classifier refused it
    "hook_blocked",         # a PreToolUse-style hook refused it
    "unknown",              # no result recorded (e.g. Cursor transcripts store inputs only)
)


@dataclass
class Event:
    harness: str
    session: str
    tool: str
    kind: str = "tool_call"          # tool_call | hook | mode
    command: str = ""
    cwd: str | None = None
    ts: str | None = None
    outcome: str = "allowed"
    mode: str | None = None          # permission mode / approval policy in effect
    detail: str = ""                 # short reason (denial reason, justification, hook name)
    source: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Rule:
    harness: str
    scope: str                       # global | project | template | ide
    file: str
    action: str                      # allow | ask | deny | mode | hook | trust | setting
    rule: str
    project: str | None = None
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Homes:
    claude: Path
    codex: Path
    cursor: Path
    cursor_user: Path
    gemini: Path
    grok: Path
    extra: dict[str, Path] = field(default_factory=dict)

    @classmethod
    def detect(cls, home: Path | None = None) -> "Homes":
        h = home or Path.home()
        appdata = Path(os.environ.get("APPDATA") or h / "AppData" / "Roaming")
        return cls(
            claude=Path(os.environ.get("CLAUDE_CONFIG_DIR") or h / ".claude"),
            codex=Path(os.environ.get("CODEX_HOME") or h / ".codex"),
            cursor=h / ".cursor",
            cursor_user=appdata / "Cursor" / "User",
            gemini=h / ".gemini",
            grok=Path(os.environ.get("GROK_HOME") or h / ".grok"),
        )


SECRET_PATTERNS = (
    re.compile(r"sk-(?:ant-|proj-)?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{12,}"),
    re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)(\s*[:=]\s*)['\"]?[^\s'\"]{6,}"),
)


def _keep_label(match: re.Match) -> str:
    if match.lastindex == 2:          # "token=" keeps its key and separator
        return match.group(1) + match.group(2) + "[REDACTED]"
    if match.lastindex == 1:          # "Bearer" keeps its scheme
        return match.group(1) + " [REDACTED]"
    return "[REDACTED]"


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(_keep_label, text)
    return text


def clip(text: str, limit: int = MAX_COMMAND) -> str:
    text = redact(text or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def parse_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            x = float(value)
            if x > 1e14:
                x /= 1e6
            elif x > 1e11:
                x /= 1e3
            return datetime.fromtimestamp(x, UTC)
        d = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    except (ValueError, OSError, OverflowError):
        return None


def iso(value: Any) -> str | None:
    d = parse_time(value)
    return d.isoformat() if d else None


def mtime(path: Path) -> datetime:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, UTC)
    except OSError:
        return datetime.fromtimestamp(0, UTC)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    try:
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
                    yield obj
    except OSError as exc:
        log.debug("cannot read %s: %s", path, exc)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        log.debug("cannot read %s: %s", path, exc)
        return None


def open_sqlite_ro(path: Path) -> tuple[sqlite3.Connection | None, str | None]:
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        con.execute("select 1").fetchone()
        return con, None
    except sqlite3.Error:
        pass
    tmpdir = tempfile.mkdtemp(prefix="harness-logs-db-")
    try:
        for suffix in ("", "-wal", "-shm", "-journal"):
            src = Path(str(path) + suffix)
            if src.exists():
                shutil.copy2(src, Path(tmpdir) / (path.name + suffix))
        return sqlite3.connect(f"file:{Path(tmpdir) / path.name}?mode=ro", uri=True), tmpdir
    except (OSError, sqlite3.Error) as exc:
        log.debug("cannot open %s: %s", path, exc)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None, None


def close_sqlite(con: sqlite3.Connection | None, tmpdir: str | None) -> None:
    if con is not None:
        con.close()
    if tmpdir:
        shutil.rmtree(tmpdir, ignore_errors=True)


def recent(paths: Iterator[Path] | list[Path], since: datetime) -> list[Path]:
    return [p for p in paths if mtime(p) >= since]
