"""Command catalog: split shell commands into segments and count segment heads per outcome.

Agents mostly send compound commands (``cd X && VAR=1 python - <<'EOF' … EOF | tail``). The
catalog splits them on ``&&``, ``||``, ``;``, ``|`` and newlines (outside quotes and heredoc
bodies), drops navigation and environment prefixes, and reduces each segment to a *head* such as
``git status``, ``python -m pytest``, ``python <script>`` or ``python - (inline)``.
The permission policy is reviewed against these heads.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Iterable

from .common import Event

SUBCOMMAND_TOOLS = {"git", "gh", "npm", "pnpm", "yarn", "uv", "docker", "docker-compose", "cargo", "dotnet",
                    "codex", "agy", "claude", "grok", "wsl", "kubectl", "terraform", "pip", "pip3", "go",
                    "rustup", "winget", "choco", "scoop", "az", "gcloud", "aws", "llmwiki", "graphify", "jj"}
PYTHONS = {"python", "python3", "py", "python.exe", "py.exe", "python3.exe"}
NAV = re.compile(r"^(?:cd|pushd|popd|set-location|sl|chdir)\b", re.I)
ENV_PREFIX = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*=(?:'[^']*'|\"[^\"]*\"|\S*)\s+)+")
PS_ENV = re.compile(r"^\$env:[A-Za-z_][A-Za-z0-9_]*\s*=", re.I)
PS_ASSIGN = re.compile(r"^\$[A-Za-z_][\w:]*\s*=\s*")
WRAPPERS = {"timeout", "time", "nice", "nohup", "env", "command", "exec", "sudo", "&", "."}
NOISE = {"do", "then", "else", "elif", "done", "fi", "esac", "{", "}", "(", ")", "begin", "end", "try", "catch", "finally"}
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def split_segments(command: str) -> list[str]:
    """Split on && || ; | and newlines outside quotes; heredoc bodies stay with their command."""
    segments: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    lines = command.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        j = 0
        while j < len(line):
            ch = line[j]
            if quote:
                buf.append(ch)
                if ch == quote and (quote == "'" or j == 0 or line[j - 1] != "\\"):
                    quote = None
            elif ch in ("'", '"'):
                quote = ch
                buf.append(ch)
            elif line.startswith(("&&", "||"), j):
                segments.append("".join(buf))
                buf = []
                j += 1
            elif ch in ";|" or (ch == "&" and j + 1 < len(line) and line[j + 1] == " " and buf and "".join(buf).strip()):
                segments.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
            j += 1
        heredoc = HEREDOC.search(line) if not quote else None
        if heredoc:  # swallow the body up to the terminator
            terminator = heredoc.group(2)
            body = []
            i += 1
            while i < len(lines) and lines[i].strip() != terminator:
                body.append(lines[i])
                i += 1
            buf.append(" <<" + terminator + " [" + str(len(body)) + " lines]")
        if quote:  # a quoted string spans lines
            buf.append("\n")
        else:
            segments.append("".join(buf))
            buf = []
        i += 1
    segments.append("".join(buf))
    return [s.strip() for s in segments if s.strip()]


def _strip_prefixes(seg: str) -> str:
    seg = seg.strip()
    for _ in range(6):
        before = seg
        seg = ENV_PREFIX.sub("", seg).strip()
        if PS_ENV.match(seg):
            return ""
        seg = PS_ASSIGN.sub("", seg).strip()
        first = seg.split(" ", 1)[0].lower() if seg else ""
        if first in NOISE:
            seg = seg[len(first):].strip()
        elif first in WRAPPERS:
            rest = seg[len(first):].strip()
            if first == "timeout":  # timeout [-k N] N cmd
                rest = re.sub(r"^(?:-\S+\s+\S+\s+)*\d+[smhd]?\s+", "", rest)
            seg = rest
        if seg == before:
            break
    return seg


def _tokens(seg: str) -> list[str]:
    return re.findall(r"'[^']*'|\"[^\"]*\"|\S+", seg)


def _base(token: str) -> str:
    token = token.strip("'\"")
    name = re.split(r"[\\/]", token)[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


def head(segment: str) -> str:
    """``git -C x status -s`` -> ``git status``; ``python -m pytest -q`` -> ``python -m pytest``."""
    seg = _strip_prefixes(segment)
    if not seg or NAV.match(seg):
        return ""
    toks = _tokens(seg)
    if not toks:
        return ""
    tool = _base(toks[0])
    rest = toks[1:]
    if tool in PYTHONS or tool.startswith("python3."):
        tool = "python"
        while rest and rest[0] in ("-I", "-u", "-B", "-E", "-X", "utf8", "-3"):
            rest = rest[1:]
        if not rest:
            return "python"
        if rest[0] == "-m" and len(rest) > 1:
            return f"python -m {rest[1]}"
        if rest[0] == "-c":
            return "python -c (inline)"
        if rest[0] == "-" or rest[0].startswith("<<"):
            return "python - (inline)"
        return "python <script>"
    if tool in ("node", "deno", "bun"):
        if rest and rest[0] in ("-e", "--eval", "-p"):
            return f"{tool} -e (inline)"
        return f"{tool} <script>" if rest else tool
    if tool in ("pwsh", "powershell"):
        flags = [t.lower() for t in rest if t.startswith("-")]
        if "-file" in flags:
            return f"{tool} -File <script>"
        if "-command" in flags or "-c" in flags:
            return f"{tool} -Command (inline)"
        return tool
    if tool in ("bash", "sh", "zsh", "cmd"):
        if rest and rest[0].lower() in ("-c", "-lc", "/c", "-ec"):
            return f"{tool} {rest[0]} (inline)"
        return f"{tool} <script>" if rest else tool
    if tool in SUBCOMMAND_TOOLS:
        i = 0
        while i < len(rest) and rest[i].startswith("-"):  # git -C dir / -c k=v / --no-pager
            i += 2 if rest[i] in ("-C", "-c", "--git-dir", "--work-tree", "-d", "--distribution", "-p", "--project") else 1
        sub = rest[i].strip("'\"") if i < len(rest) else ""
        if tool == "uv" and sub == "run" and i + 1 < len(rest):
            nxt = _base(rest[i + 1])
            return f"uv run {'python' if nxt in PYTHONS else nxt}"
        if tool in ("npm", "pnpm", "yarn") and sub == "run" and i + 1 < len(rest):
            return f"{tool} run {rest[i + 1]}"
        if tool in ("gh", "docker", "kubectl", "az", "gcloud", "aws") and i + 1 < len(rest) and not rest[i + 1].startswith("-"):
            return f"{tool} {sub} {rest[i + 1].strip(chr(39) + chr(34))}"
        return f"{tool} {sub}".strip()
    if re.match(r"^[a-z]+-[a-z]+$", tool):  # PowerShell Verb-Noun
        return toks[0].strip("'\"").split("\\")[-1]
    if "/" in toks[0] or "\\" in toks[0]:
        return f"<path>/{tool}"
    return tool


def heads(command: str) -> list[str]:
    return [h for h in (head(s) for s in split_segments(command)) if h]


def build_catalog(events: Iterable[Event], shell_tools: set[str] | None = None) -> list[dict]:
    """One row per (harness, head) with total and per-outcome counts and up to 3 redacted examples."""
    from .events import SHELL_TOOLS

    shell_tools = shell_tools or SHELL_TOOLS
    rows: dict[tuple[str, str], dict] = {}
    for ev in events:
        if ev.kind != "tool_call":
            continue
        if ev.tool in shell_tools or ev.harness == "codex" and ev.tool in ("exec",):
            hs = heads(ev.command) or ["(empty)"]
        else:
            hs = [f"tool:{ev.tool}"]
        compound = len(hs) > 1
        for h in dict.fromkeys(hs):
            row = rows.setdefault((ev.harness, h), {"harness": ev.harness, "head": h, "total": 0,
                                                    "in_compound": 0, "outcomes": Counter(), "examples": []})
            row["total"] += 1
            row["in_compound"] += int(compound)
            row["outcomes"][ev.outcome] += 1
            if len(row["examples"]) < 3 and ev.command and ev.command not in row["examples"]:
                row["examples"].append(ev.command[:240])
    out = []
    for row in rows.values():
        row["outcomes"] = dict(row["outcomes"])
        out.append(row)
    return sorted(out, key=lambda r: (-r["total"], r["harness"], r["head"]))


def merge_harnesses(catalog: list[dict]) -> list[dict]:
    merged: dict[str, dict] = defaultdict(lambda: {"total": 0, "harnesses": Counter(), "outcomes": Counter(), "examples": []})
    for row in catalog:
        m = merged[row["head"]]
        m["head"] = row["head"]
        m["total"] += row["total"]
        m["harnesses"][row["harness"]] += row["total"]
        m["outcomes"].update(row["outcomes"])
        for ex in row["examples"]:
            if len(m["examples"]) < 3:
                m["examples"].append(ex)
    out = [{**m, "harnesses": dict(m["harnesses"]), "outcomes": dict(m["outcomes"])} for m in merged.values()]
    return sorted(out, key=lambda r: -r["total"])
