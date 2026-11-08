#!/usr/bin/env python3
"""Load, validate and audit the shared agent harness registry.

The registry (``.agent/harnesses/registry.json``) is the one list of coding-agent harnesses
(Claude Code, Codex, Cursor, Antigravity, Grok, retired Gemini CLI): ids, aliases, CLI argv,
home and config paths, hook formats and permission-gate support. Consumers read it instead of
keeping their own tables.

Usage:
    python scripts/harness_registry.py validate
    python scripts/harness_registry.py list [--json] [--all]
    python scripts/harness_registry.py resolve <id-or-alias>
    python scripts/harness_registry.py audit --root <projects-root> [--json]

``audit`` is read-only. It reads the harness tokens that sibling repos still hard-code and reports
tokens the registry does not know and active harnesses a consumer is missing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / ".agent" / "harnesses" / "registry.json"

_ID = re.compile(r"^[a-z][a-z0-9-]*$")
_TOP_KEYS = {"$schema", "schema_version", "harnesses"}
_HARNESS_KEYS = {"id", "name", "status", "retired_reason", "aliases", "cli", "home", "instructions",
                 "mcp_configs", "permission_files", "hooks", "transcripts", "gate"}
_REQUIRED = _HARNESS_KEYS - {"retired_reason"}
_FILE_FORMATS = {"json", "toml", "codex-rules", "sqlite"}


class RegistryError(ValueError):
    """The registry file does not match the schema contract."""


def load(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Read and validate the registry; raise RegistryError on any contract violation."""
    data = json.loads(path.read_text(encoding="utf-8"))
    problems = validate(data)
    if problems:
        raise RegistryError(f"{path}: " + "; ".join(problems))
    return data


def _check_path(where: str, value: Any, problems: list[str]) -> None:
    if not isinstance(value, str) or not (value.startswith("~/") or value.startswith("%APPDATA%/")):
        problems.append(f"{where}: path must start with ~/ or %APPDATA%/")


def _check_argv(where: str, value: Any, problems: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, list) or not value or not all(isinstance(v, str) and v for v in value):
        problems.append(f"{where}: must be null or a non-empty list of strings")


def _check_files(where: str, value: Any, problems: list[str]) -> None:
    if not isinstance(value, list):
        problems.append(f"{where}: must be a list")
        return
    for i, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != {"path", "format", "key"}:
            problems.append(f"{where}[{i}]: needs exactly path, format, key")
            continue
        _check_path(f"{where}[{i}].path", item["path"], problems)
        if item["format"] not in _FILE_FORMATS:
            problems.append(f"{where}[{i}].format: unknown format {item['format']!r}")
        if item["key"] is not None and not isinstance(item["key"], str):
            problems.append(f"{where}[{i}].key: must be a string or null")


def validate(data: Any) -> list[str]:
    """Return every contract violation (empty list when valid). Mirrors registry.schema.json."""
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["registry must be a JSON object"]
    extra = set(data) - _TOP_KEYS
    if extra:
        problems.append(f"unknown top-level keys: {sorted(extra)}")
    if data.get("schema_version") != 1:
        problems.append("schema_version must be 1")
    harnesses = data.get("harnesses")
    if not isinstance(harnesses, list) or not harnesses:
        return problems + ["harnesses must be a non-empty list"]

    seen: dict[str, str] = {}
    for n, h in enumerate(harnesses):
        where = f"harnesses[{n}]"
        if not isinstance(h, dict):
            problems.append(f"{where}: must be an object")
            continue
        missing = _REQUIRED - set(h)
        if missing:
            problems.append(f"{where}: missing {sorted(missing)}")
            continue
        unknown = set(h) - _HARNESS_KEYS
        if unknown:
            problems.append(f"{where}: unknown keys {sorted(unknown)}")
        hid = h["id"]
        where = f"harness {hid!r}"
        for token in [hid, *h["aliases"]]:
            if not isinstance(token, str) or not _ID.match(token):
                problems.append(f"{where}: bad id or alias {token!r}")
            elif token in seen:
                problems.append(f"{where}: {token!r} already used by {seen[token]!r}")
            else:
                seen[token] = hid
        if h["status"] not in ("active", "retired"):
            problems.append(f"{where}: status must be active or retired")
        if h["status"] == "retired" and not h.get("retired_reason"):
            problems.append(f"{where}: retired harness needs retired_reason")
        cli = h["cli"]
        if not isinstance(cli, dict) or not isinstance(cli.get("command"), str) or not cli["command"]:
            problems.append(f"{where}: cli.command is required")
        else:
            _check_argv(f"{where}.cli.print_argv", cli.get("print_argv"), problems)
            _check_argv(f"{where}.cli.acp_argv", cli.get("acp_argv"), problems)
        home = h["home"]
        if not isinstance(home, dict) or set(home) != {"path", "env"}:
            problems.append(f"{where}: home needs exactly path and env")
        else:
            _check_path(f"{where}.home.path", home["path"], problems)
        for key in ("instructions", "transcripts"):
            if not isinstance(h[key], list):
                problems.append(f"{where}.{key}: must be a list")
            else:
                for i, p in enumerate(h[key]):
                    _check_path(f"{where}.{key}[{i}]", p, problems)
        _check_files(f"{where}.mcp_configs", h["mcp_configs"], problems)
        _check_files(f"{where}.permission_files", h["permission_files"], problems)
        hooks = h["hooks"]
        if hooks is not None:
            if not isinstance(hooks, dict) or set(hooks) != {"path", "format", "key", "events"}:
                problems.append(f"{where}.hooks: needs exactly path, format, key, events")
            else:
                _check_path(f"{where}.hooks.path", hooks["path"], problems)
                if not hooks["events"]:
                    problems.append(f"{where}.hooks.events: must not be empty")
        gate = h["gate"]
        if not isinstance(gate, dict) or set(gate) != {"supported", "can_approve"}:
            problems.append(f"{where}.gate: needs exactly supported and can_approve")
        elif gate["can_approve"] and not gate["supported"]:
            problems.append(f"{where}.gate: can_approve requires supported")
    return problems


def harnesses(data: dict[str, Any], *, include_retired: bool = False) -> list[dict[str, Any]]:
    return [h for h in data["harnesses"] if include_retired or h["status"] == "active"]


def active_ids(data: dict[str, Any]) -> tuple[str, ...]:
    return tuple(h["id"] for h in harnesses(data))


def resolve(data: dict[str, Any], token: str) -> dict[str, Any] | None:
    """Return the harness whose id or alias is ``token`` (case-insensitive), else None."""
    token = token.strip().lower()
    for h in data["harnesses"]:
        if token == h["id"] or token in h["aliases"]:
            return h
    return None


def expand(path: str, *, home: Path | None = None, env: Mapping[str, str] | None = None) -> Path:
    """Expand ``~/`` and ``%APPDATA%/`` registry paths for this machine."""
    vars_: Mapping[str, str] = os.environ if env is None else env
    base = home or Path.home()
    if path.startswith("%APPDATA%/"):
        appdata = Path(vars_.get("APPDATA") or base / "AppData" / "Roaming")
        return appdata / path[len("%APPDATA%/"):]
    return base / path[2:]


def home_dir(h: dict[str, Any], *, home: Path | None = None, env: Mapping[str, str] | None = None) -> Path:
    """The harness home, honouring its override variable (e.g. CLAUDE_CONFIG_DIR)."""
    vars_: Mapping[str, str] = os.environ if env is None else env
    var = h["home"]["env"]
    override = vars_.get(var) if var else None
    if override:
        return Path(override)
    return expand(h["home"]["path"], home=home, env=vars_)


# --------------------------------------------------------------------------- audit

@dataclass
class Probe:
    """Where a sibling repo still hard-codes a list of harness tokens."""
    repo: str
    file: str
    pattern: str          # regex with one group per token, applied with findall
    within: str | None = None  # optional regex selecting the region to search
    expect_all_active: bool = True


@dataclass
class Finding:
    probe: Probe
    found: bool
    tokens: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"repo": self.probe.repo, "file": self.probe.file, "found": self.found,
                "tokens": self.tokens, "unknown": self.unknown, "missing": self.missing}


PROBES = (
    Probe("synthet-agent-swarm", "agent-orchestrator/src/harness/registry.ts", r'^\s+id: "([a-z-]+)"'),
    Probe("synthet-agent-swarm", "agent-orchestrator/config.default.json", r'"([a-z-]+)"',
          within=r'"allowedAgents"\s*:\s*\[[^\]]*\]'),
    Probe("synthet-code-framework", "infra/jev/src/jev_engineering/permission/adapters.py", r'"([a-z-]+)"',
          within=r"^HARNESSES = \([^)]*\)"),
    Probe("_agent-infra", "jev/src/jev_engineering/permission/adapters.py", r'"([a-z-]+)"',
          within=r"^HARNESSES = \([^)]*\)"),
)


def audit(data: dict[str, Any], root: Path, probes: tuple[Probe, ...] = PROBES) -> list[Finding]:
    out: list[Finding] = []
    active = set(active_ids(data))
    for probe in probes:
        path = root / probe.repo / probe.file
        if not path.is_file():
            out.append(Finding(probe, found=False))
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if probe.within:
            m = re.search(probe.within, text, re.MULTILINE | re.DOTALL)
            text = m.group(0) if m else ""
        tokens = sorted(set(re.findall(probe.pattern, text, re.MULTILINE)))
        resolved = {t: resolve(data, t) for t in tokens}
        unknown = [t for t, h in resolved.items() if h is None]
        covered = {h["id"] for h in resolved.values() if h is not None}
        missing = sorted(active - covered) if probe.expect_all_active else []
        out.append(Finding(probe, True, tokens, unknown, missing))
    return out


def _cmd_list(data: dict[str, Any], args: argparse.Namespace) -> int:
    rows = harnesses(data, include_retired=args.all)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for h in rows:
        alias = f" (aliases: {', '.join(h['aliases'])})" if h["aliases"] else ""
        gate = "gate" if h["gate"]["supported"] else "no gate"
        print(f"{h['id']:<12} {h['status']:<8} {h['cli']['command']:<8} {gate:<8} {h['name']}{alias}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness_registry", description=__doc__.split("\n\n")[0])
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("validate", help="Check the registry against its contract")
    ls = sub.add_parser("list", help="List harnesses")
    ls.add_argument("--json", action="store_true")
    ls.add_argument("--all", action="store_true", help="Include retired harnesses")
    rs = sub.add_parser("resolve", help="Map an id or alias to its canonical id")
    rs.add_argument("token")
    au = sub.add_parser("audit", help="Read-only drift report for repos that still hard-code harness lists")
    au.add_argument("--root", type=Path, required=True, help="Folder that holds the sibling checkouts")
    au.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        data = load(args.registry)
    except (RegistryError, json.JSONDecodeError) as exc:
        print(f"invalid registry: {exc}", file=sys.stderr)
        return 1

    if args.action == "validate":
        print(f"OK {args.registry} ({len(data['harnesses'])} harnesses, {len(active_ids(data))} active)")
        return 0
    if args.action == "list":
        return _cmd_list(data, args)
    if args.action == "resolve":
        h = resolve(data, args.token)
        if h is None:
            print(f"unknown harness {args.token!r}", file=sys.stderr)
            return 1
        print(h["id"])
        return 0

    findings = audit(data, args.root)
    drift = any(f.unknown or f.missing for f in findings)
    if args.json:
        print(json.dumps([f.as_dict() for f in findings], indent=2))
    else:
        for f in findings:
            where = f"{f.probe.repo}/{f.probe.file}"
            if not f.found:
                print(f"SKIP  {where} (not found)")
                continue
            state = "DRIFT" if f.unknown or f.missing else "OK   "
            detail = f"tokens={','.join(f.tokens)}"
            if f.unknown:
                detail += f" unknown={','.join(f.unknown)}"
            if f.missing:
                detail += f" missing={','.join(f.missing)}"
            print(f"{state} {where} {detail}")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
