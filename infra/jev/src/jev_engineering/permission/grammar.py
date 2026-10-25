"""Deterministic command tiers for the permission gate.

Tiers (riskiest wins across the segments of a compound command):

- ``T0`` deny: hard stop, never approved.
- ``T1`` human: always ask the user; Jev is not called.
- ``T4`` unknown: not classified; native fallback; Jev is not called.
- ``T3`` Jev-eligible: approved only if every Jev check passes the threshold.
- ``T2`` static-safe: read-only inspection; approved without Jev.

T0/T1 patterns are searched anywhere in the command (including heredoc bodies and script
blocks), so a dangerous word anywhere forces a human decision. T2/T3 patterns are anchored at
the start of each segment after navigation/environment prefixes are removed.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..policy import screen

ORDER = {"T0": 0, "T1": 1, "T4": 2, "T3": 3, "T2": 4}  # lower = riskier
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
ENV_PREFIX = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*=(?:'[^']*'|\"[^\"]*\"|\S*)\s+)+")
PS_ENV = re.compile(r"^\$env:[A-Za-z_][A-Za-z0-9_]*\s*=", re.I)
PS_ASSIGN = re.compile(r"^\$[A-Za-z_][\w:]*(?:\[[^\]]*\])?\s*[+\-]?=\s*")
SH_ASSIGN = re.compile(r"^(?:export\s+|local\s+|declare\s+)?[A-Za-z_][A-Za-z0-9_]*=(?:'[^']*'|\"[^\"]*\"|\S*)\s*$")
NAV = re.compile(r"^(?:cd|pushd|popd|chdir|Set-Location|sl|Push-Location|Pop-Location)\b\s*(.*)$", re.I)
WRAPPERS = re.compile(r"^(?:timeout(?:\s+-\S+(?:\s+\S+)?)*\s+\d+[smhd]?|time|nice(?:\s+-n\s+-?\d+)?|nohup|env|command|exec|sudo|MSYS_NO_PATHCONV=\S+)\s+", re.I)
CALL_OP = re.compile(r"^[&.]\s+")
REDIRECT = re.compile(r"(?<![0-9&<>])(?:[1]?>>?|\*>)\s*(\"[^\"]+\"|'[^']+'|[^\s;|&)]+)")
NULL_TARGETS = re.compile(r"^(?:/dev/null|nul|\$null|&\d|con)$", re.I)
EXPRESSION = re.compile(r"^(?:\$|\[|@?['\"]|\d|-?\$)")
GIT_C = re.compile(r"\bgit\s+-C\s+(\"[^\"]+\"|'[^']+'|\S+)")
# Wrappers whose payload is itself a command: classify the payload instead of the wrapper.
SHELL_WRAP = re.compile(
    r"^(?:cmd(?:\.exe)?\s+/[cCkK]|(?:bash|sh|zsh)\s+-(?:l?c|c)|"
    r"(?:pwsh|powershell)(?:\.exe)?(?:\s+-(?:NoProfile|NonInteractive|NoLogo|ExecutionPolicy\s+\w+))*\s+-(?:Command|c)|"
    r"wsl(?:\.exe)?(?:\s+-d\s+\S+)?(?:\s+-u\s+\S+)?\s+(?:-e\s+|--exec\s+|--\s+)?(?:bash|sh)\s+-l?c)\s+(.+)$",
    re.I | re.S)
DOCKER_EXEC = re.compile(r"^docker\s+exec\s+((?:-(?:i|t|it|d)\s+|-(?:w|e|u|-workdir|-env|-user)\s+\S+\s+|--\w[\w-]*=\S+\s+)*)(\S+)\s+(.+)$", re.S)
ASSIGN = re.compile(r"""^(?:export\s+)?\$?([A-Za-z_]\w*)\s*=\s*(?:"([^"$`]*)"|'([^']*)'|([^\s;&|'"$`]+))\s*$""")


def _unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def _assignments(command: str) -> dict[str, str]:
    """Literal ``NAME=value`` / ``$name = 'value'`` assignments in the command, for path checks."""
    found: dict[str, str] = {}
    for seg in split_segments(command):
        m = ASSIGN.match(seg.strip())
        if m:
            found[m.group(1)] = next(g for g in m.groups()[1:] if g is not None)
    return found


def _substitute(target: str, variables: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        return variables.get(m.group(1) or m.group(2), m.group(0))
    return re.sub(r"\$\{(\w+)\}|\$(?!env:)(\w+)", repl, target)


@dataclass
class Rule:
    id: str
    tier: str
    rx: re.Pattern


@dataclass
class Policy:
    raw: dict[str, Any]
    rules: dict[str, list[Rule]]
    threshold: float
    projects_root: Path
    scratch_dirs: list[Path]
    approved_scope: str
    inline_max_chars: int
    shell_tools: set[str]
    exclude_repos: set[str] = field(default_factory=set)
    question_thresholds: dict[str, float] = field(default_factory=dict)
    coin_flip: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Policy":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Policy":
        rules = {tier: [Rule(r["id"], tier, re.compile(r["pattern"], re.I | re.M)) for r in raw["tiers"].get(tier, [])]
                 for tier in ("T0", "T1", "T2", "T3")}
        threshold = float(raw.get("threshold", 0.85))
        if not 0.70 <= threshold <= 1.0:
            raise ValueError("threshold must be within 0.70..1.00")
        q_thresh = {str(k): float(v) for k, v in (raw.get("question_thresholds") or {}).items()}
        for k, v in q_thresh.items():
            if not 0.70 <= v <= 1.0:
                raise ValueError(f"question_threshold[{k}] must be within 0.70..1.00")
        coin_flip = dict(raw.get("coin_flip") or {})
        scratch = [
            Path(os.path.expanduser(os.path.expandvars(p)))
            for p in raw.get("scratch_dirs", [])
            if "%" not in os.path.expandvars(p)
        ]
        return cls(
            raw=raw,
            rules=rules,
            threshold=threshold,
            projects_root=Path(raw["projects_root"]),
            scratch_dirs=scratch,
            approved_scope=str(raw["approved_scope"]).strip(),
            inline_max_chars=int(raw.get("inline_max_chars", 4096)),
            shell_tools=set(raw.get("shell_tools", [])),
            exclude_repos=set(raw.get("exclude_repos", [])),
            question_thresholds=q_thresh,
            coin_flip=coin_flip,
        )


@dataclass
class Classification:
    tier: str
    rule: str
    segments: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"tier": self.tier, "rule": self.rule, "segments": self.segments}


# --------------------------------------------------------------------------- splitting

def split_segments(command: str) -> list[str]:
    """Split on ``&& || ; | &`` newlines and script-block/sub-expression brackets, outside quotes.
    Heredoc bodies stay attached (as a placeholder) to the command that reads them."""
    segments: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    lines = command.replace("\r\n", "\n").split("\n")
    i = 0

    def cut() -> None:
        segments.append("".join(buf))
        buf.clear()

    while i < len(lines):
        line = lines[i]
        j = 0
        while j < len(line):
            ch = line[j]
            if quote:
                buf.append(ch)
                if ch == quote and (quote == "'" or line[j - 1:j] != "\\"):
                    quote = None
            elif ch in ("'", '"'):
                quote = ch
                buf.append(ch)
            elif line.startswith(("&&", "||"), j):
                cut()
                j += 1
            elif ch == "&" and line[j + 1:j + 2] == ">":  # &> redirect
                buf.append(ch)
            elif ch == "&" and line[j - 1:j] in (">", "<"):  # 2>&1
                buf.append(ch)
            elif ch == "&" and "".join(buf).strip():  # background job separator (not the call operator)
                cut()
            elif ch in ";|{}()":
                if ch == "(" and buf and buf[-1] in ("$", "@"):
                    buf.pop()
                cut()
            else:
                buf.append(ch)
            j += 1
        heredoc = None if quote else HEREDOC.search(line)
        if heredoc:
            terminator, body = heredoc.group(2), 0
            i += 1
            while i < len(lines) and lines[i].strip() != terminator:
                body += 1
                i += 1
            buf.append(f" [heredoc {body} lines]")
        if quote:
            buf.append("\n")
        else:
            cut()
        i += 1
    cut()
    return [s.strip() for s in segments if s.strip()]


def strip_prefixes(segment: str) -> tuple[str, list[str]]:
    """Remove env assignments, wrappers and the call operator. Returns (command, nav targets)."""
    seg = segment.strip()
    nav: list[str] = []
    for _ in range(8):
        before = seg
        if PS_ENV.match(seg) or SH_ASSIGN.match(seg):
            return "", nav
        m = NAV.match(seg)
        if m:
            target = m.group(1).strip().strip("'\"")
            if target and not target.startswith("-"):
                nav.append(target)
            return "", nav
        seg = ENV_PREFIX.sub("", seg).strip()
        seg = PS_ASSIGN.sub("", seg).strip()
        seg = WRAPPERS.sub("", seg).strip()
        if seg == before:
            break
    return seg, nav


# --------------------------------------------------------------------------- path checks

def _norm(p: Path | str) -> str:
    return os.path.normcase(os.path.normpath(str(p)))


def is_within(path: str, roots: list[Path]) -> bool:
    p = _norm(path)
    for r in roots:
        rn = _norm(r)
        if p == rn or p.startswith(rn.rstrip("\\/") + os.sep):
            return True
    return False


def _resolve_target(target: str, cwd: Path | None) -> str | None:
    t = target.strip().strip("'\"")
    t = os.path.expandvars(t.replace("$env:TEMP", os.environ.get("TEMP", "$env:TEMP"))
                           .replace("$TEMP", os.environ.get("TEMP", "$TEMP")))
    if re.match(r"^/[a-zA-Z]/", t) and os.name == "nt":  # git-bash /d/Projects -> D:/Projects
        t = f"{t[1].upper()}:{t[2:]}"
    if t.startswith("~"):
        t = str(Path.home()) + t[1:]
    if "$" in t or "%" in t:
        return None  # unexpanded variable: unknown target
    path = Path(t)
    if not path.is_absolute():
        if cwd is None:
            return None
        path = cwd / path
    return os.path.normpath(str(path))


# --------------------------------------------------------------------------- classification

def _first(rules: list[Rule], text: str, anchored: bool) -> Rule | None:
    for rule in rules:
        if (rule.rx.match(text) if anchored else rule.rx.search(text)):
            return rule
    return None


def classify(command: str, policy: Policy, *, cwd: Path | None = None,
             allowed_roots: list[Path] | None = None, _depth: int = 0, _container: bool = False) -> Classification:
    """``allowed_roots`` are where navigation, ``git -C`` and redirects may point (repo + scratch).
    Inside ``docker exec`` (``_container``) host path checks do not apply."""
    command = command or ""
    if not command.strip():
        return Classification("T4", "empty")
    variables = _assignments(command)
    hit = screen(command)
    if hit["decision"] == "deny":
        tier = "T0" if hit["reason"] == "destructive_command" else "T1"
        return Classification(tier, f"screen:{hit['reason']}")
    if hit["decision"] == "ask":
        return Classification("T1", f"screen:{hit['reason']}")
    for tier in ("T0", "T1"):
        rule = _first(policy.rules[tier], command, anchored=False)
        if rule:
            return Classification(tier, rule.id)

    roots = list(allowed_roots or [])
    for m in REDIRECT.finditer(_mask_quotes_and_heredocs(command)) if not _container else ():
        target = _substitute(m.group(1), variables)
        if NULL_TARGETS.match(target.strip("'\"")):
            continue
        resolved = _resolve_target(target, cwd)
        if resolved is None or not is_within(resolved, roots):
            return Classification("T1", f"redirect-outside:{m.group(1)[:60]}")
    for m in GIT_C.finditer(command) if not _container else ():
        resolved = _resolve_target(_substitute(m.group(1), variables), cwd)
        if resolved is None or not is_within(resolved, roots):
            return Classification("T1", f"git-C-outside:{m.group(1)[:60]}")

    segments: list[dict[str, str]] = []
    worst = "T2"
    worst_rule = "static-safe"
    inline = False
    for seg in split_segments(command):
        text, nav = strip_prefixes(seg)
        for target in nav if not _container else ():
            target = _substitute(target, variables)
            if target in ("-", ".."):
                continue
            resolved = _resolve_target(target, cwd)
            if resolved is None or not is_within(resolved, roots):
                return Classification("T1", f"cd-outside:{target[:60]}", segments)
        if not text:
            continue
        wrapped = SHELL_WRAP.match(text) or DOCKER_EXEC.match(text)
        if wrapped and _depth < 2:
            container = wrapped.re is DOCKER_EXEC
            inner = _unquote(wrapped.group(3) if container else wrapped.group(1))
            sub = classify(inner, policy, cwd=cwd, allowed_roots=allowed_roots, _depth=_depth + 1,
                           _container=_container or container)
            tier, rule_id = sub.tier, ("docker-exec:" if container else "wrap:") + sub.rule
            if container:
                if tier == "T2":
                    tier = "T3"  # a container is shared state: never approve without Jev
                elif tier == "T4":
                    tier = "T1"  # unknown container payload: require human review
            segments.append({"segment": seg[:200], "tier": tier, "rule": rule_id})
            worst, worst_rule = _worse(worst, worst_rule, tier, rule_id)
            continue
        if re.match(r"^docker\s+exec\b", text, re.I):
            tier, rule_id = "T1", "docker-exec"
            segments.append({"segment": seg[:200], "tier": tier, "rule": rule_id})
            worst, worst_rule = _worse(worst, worst_rule, tier, rule_id)
            continue
        if CALL_OP.match(text):
            text = CALL_OP.sub("", text)
            if text.startswith("$"):
                tier, rule_id = "T4", "dynamic-invoke"
                segments.append({"segment": seg[:200], "tier": tier, "rule": rule_id})
                worst, worst_rule = _worse(worst, worst_rule, tier, rule_id)
                continue
            text = re.sub(r"^(['\"])([^'\"]+)\1", lambda m: m.group(2).replace(" ", "_"), text)
            text = re.sub(r"^\S*[\\/](python|py|node|pwsh|powershell)(?:\.exe)?\b", r"\1", text, flags=re.I)
        elif text[0] in "'\"" and not QUOTED.fullmatch(text):
            # bash/pwsh run a quoted executable path: classify it as that command
            text = re.sub(r"^(['\"])([^'\"]+)\1", lambda m: m.group(2).replace(" ", "_"), text)
            text = re.sub(r"^\S*[\\/](python|py|node|pwsh|powershell)(?:\.exe)?\b", r"\1", text, flags=re.I)
        elif EXPRESSION.match(text):
            segments.append({"segment": seg[:200], "tier": "T2", "rule": "expression"})
            continue
        rule = _first(policy.rules["T2"], text, anchored=True)
        tier = "T2"
        if rule is None:
            rule = _first(policy.rules["T3"], text, anchored=True)
            tier = "T3"
        if rule is None:
            tier, rule_id = "T4", "unknown:" + (text.split()[0][:40] if text.split() else "?")
        else:
            rule_id = rule.id
            inline = inline or rule.id == "inline-code"
        segments.append({"segment": seg[:200], "tier": tier, "rule": rule_id})
        worst, worst_rule = _worse(worst, worst_rule, tier, rule_id)
    if inline and len(command) > policy.inline_max_chars and ORDER[worst] > ORDER["T4"]:
        return Classification("T4", "inline-too-long", segments)
    return Classification(worst, worst_rule, segments)


def _worse(cur: str, cur_rule: str, tier: str, rule: str) -> tuple[str, str]:
    return (tier, rule) if ORDER[tier] < ORDER[cur] else (cur, cur_rule)


QUOTED = re.compile(r"'[^'\n]*'|\"(?:[^\"\\\n]|\\.)*\"")


def _mask_quotes_and_heredocs(command: str) -> str:
    """Hide quoted strings and heredoc bodies so a '>' inside them is not read as a redirect.
    A quoted string right after '>' is the redirect target and stays visible."""
    text = _drop_heredoc_bodies(command)

    def mask(m: re.Match) -> str:
        if text[: m.start()].rstrip().endswith(">"):
            return m.group(0)
        return m.group(0)[0] + "_" * (len(m.group(0)) - 2) + m.group(0)[-1]

    return QUOTED.sub(mask, text)


def _drop_heredoc_bodies(command: str) -> str:
    lines = command.split("\n")
    out, i = [], 0
    while i < len(lines):
        out.append(lines[i])
        m = HEREDOC.search(lines[i])
        if m:
            i += 1
            while i < len(lines) and lines[i].strip() != m.group(2):
                i += 1
        i += 1
    return "\n".join(out)
