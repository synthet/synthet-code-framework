"""Merge local harness config. Never prints file bodies or credentials."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("JEV_ENGINEERING_ROOT", r"D:\Projects\_agent-infra\jev"))
MARKER = "<!-- BEGIN JEV ENGINEERING -->"
SERVER_KEY = "jev-engineering"
HOOK_PRE = "hook-pre-tool.ps1"
HOOK_PROMPT = "hook-prompt.ps1"

INSTRUCTION_TARGETS = (
    Path.home() / ".claude" / "CLAUDE.md",
    Path.home() / ".codex" / "AGENTS.md",
    Path.home() / ".gemini" / "GEMINI.md",
)


def mcp_entry(root: Path = ROOT) -> dict[str, Any]:
    uv = shutil.which("uv") or (
        r"C:\Users\dmnsy\AppData\Local\Microsoft\WinGet\Packages"
        r"\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.EXE"
    )
    return {
        "command": uv,
        "args": [
            "run",
            "--project",
            str(root),
            "python",
            str(root / "scripts" / "run_mcp.py"),
        ],
        "env": {
            "JEV_ENV_FILE": os.environ.get("JEV_ENV_FILE", r"D:\Projects\jev-mcp\.env"),
            "JEV_ENGINEERING_ROOT": str(root),
        },
    }


def apply(home: Path | None = None, root: Path = ROOT) -> dict[str, Any]:
    home = home or Path.home()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_dir = root / "backups" / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, str]] = []
    entry = mcp_entry(root)
    cursor_entry = dict(entry)
    cursor_entry["type"] = "stdio"

    json_targets = [
        (home / ".cursor" / "mcp.json", cursor_entry),
        (home / ".claude.json", entry),
        (home / ".gemini" / "settings.json", entry),
        (home / ".gemini" / "antigravity" / "mcp_config.json", entry),
        (home / ".gemini" / "config" / "mcp_config.json", entry),
    ]
    for path, server in json_targets:
        files.append(_merge_json(path, server, backup_dir))

    files.append(_merge_codex(home / ".codex" / "config.toml", entry, backup_dir))
    files.append(_merge_claude_hooks(home / ".claude" / "settings.json", root, backup_dir))

    block = (root / "instructions" / "JEV_ENGINEERING.md").read_text(encoding="utf-8")
    for path in (
        home / ".claude" / "CLAUDE.md",
        home / ".codex" / "AGENTS.md",
        home / ".gemini" / "GEMINI.md",
    ):
        files.append(_append_marker(path, block, backup_dir))

    rule = (root / "instructions" / "cursor-rule.mdc").read_text(encoding="utf-8")
    files.append(_write_if_absent(home / ".cursor" / "rules" / "jev-engineering.mdc", rule, backup_dir))

    receipt = {
        "stamp": stamp,
        "backup_dir": str(backup_dir),
        "files": [item for item in files if item["status"] == "written"],
        "unchanged": [item["path"] for item in files if item["status"] != "written"],
    }
    receipt_path = backup_dir / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    latest = root / "backups" / "latest.json"
    latest.write_text(json.dumps({"receipt": str(receipt_path)}, indent=2) + "\n", encoding="utf-8")
    print(f"OK receipt {receipt_path}")
    for item in files:
        print(f"{item['status'].upper()} {item['path']}")
    return receipt


def rollback(receipt_path: Path) -> int:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    restored = 0
    for item in receipt["files"]:
        path = Path(item["path"])
        if not path.exists():
            print(f"SKIP missing {path}")
            continue
        if _sha(path) != item["after_sha"]:
            print(f"SKIP changed since install {path}")
            continue
        if item.get("created") == "true":
            path.unlink()
            restored += 1
            print(f"REMOVED {path}")
            continue
        backup = Path(item["backup"])
        if _sha(backup) != item["before_sha"]:
            print(f"SKIP backup mismatch {backup}")
            continue
        path.write_bytes(backup.read_bytes())
        restored += 1
        print(f"RESTORED {path}")
    print(f"OK restored {restored}")
    return 0


def _merge_json(path: Path, entry: dict[str, Any], backup_dir: Path) -> dict[str, str]:
    if not path.exists():
        print(f"SKIP missing {path}", file=sys.stderr)
        return {"status": "missing", "path": str(path)}
    raw = path.read_bytes()
    original = raw.decode("utf-8-sig")
    data = json.loads(original)
    if not isinstance(data, dict) or not isinstance(data.get("mcpServers"), dict):
        print(f"SKIP no mcpServers object {path}", file=sys.stderr)
        return {"status": "skipped", "path": str(path)}
    if SERVER_KEY in data["mcpServers"]:
        return {"status": "unchanged", "path": str(path)}
    updated = _insert_server(original, entry)
    parsed = json.loads(updated)
    expected = json.loads(original)
    expected["mcpServers"][SERVER_KEY] = entry
    if parsed != expected:
        raise SystemExit(f"Refusing to rewrite {path}: merge check failed")
    return _commit(path, raw, updated.encode("utf-8"), backup_dir)


def _insert_server(text: str, entry: dict[str, Any]) -> str:
    key_at = _top_level_key(text, "mcpServers")
    brace = text.find("{", key_at)
    end = _matching_brace(text, brace)
    blob = json.dumps(entry, indent=2)
    indented = "\n".join(("    " + line) if line else line for line in blob.splitlines())
    insertion = f'\n    "{SERVER_KEY}": {indented.strip()}'
    return text[:end] + "," + insertion + "\n  " + text[end:]


def _top_level_key(text: str, key: str) -> int:
    needle = f'"{key}"'
    depth = 0
    in_str = False
    esc = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            if depth == 1 and text.startswith(needle, i):
                return i
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    raise ValueError(f"top-level {key} not found")


def _matching_brace(text: str, open_index: int) -> int:
    depth = 0
    in_str = False
    esc = False
    for i in range(open_index, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("unbalanced json")


def _merge_codex(path: Path, entry: dict[str, Any], backup_dir: Path) -> dict[str, str]:
    if not path.exists():
        print(f"SKIP missing {path}", file=sys.stderr)
        return {"status": "missing", "path": str(path)}
    raw = path.read_bytes()
    original = raw.decode("utf-8")
    before = tomllib.loads(original)
    servers = before.get("mcp_servers") or {}
    if SERVER_KEY in servers:
        return {"status": "unchanged", "path": str(path)}
    block = (
        f"\n[mcp_servers.{SERVER_KEY}]\n"
        f"command = {json.dumps(entry['command'])}\n"
        f"args = {json.dumps(entry['args'])}\n\n"
        f"[mcp_servers.{SERVER_KEY}.env]\n"
    )
    for key, value in entry["env"].items():
        block += f"{key} = {json.dumps(value)}\n"
    updated = original
    if updated and not updated.endswith("\n"):
        updated += "\n"
    updated += block
    after = tomllib.loads(updated)
    if after.get("approval_policy") != before.get("approval_policy"):
        raise SystemExit("Refusing Codex edit: approval_policy changed")
    if after.get("sandbox_mode") != before.get("sandbox_mode"):
        raise SystemExit("Refusing Codex edit: sandbox_mode changed")
    if after.get("model") != before.get("model"):
        raise SystemExit("Refusing Codex edit: model changed")
    if set(before.get("mcp_servers") or {}) | {SERVER_KEY} != set(after.get("mcp_servers") or {}):
        raise SystemExit("Refusing Codex edit: MCP server set changed unexpectedly")
    for name, server in (before.get("mcp_servers") or {}).items():
        if after["mcp_servers"][name] != server:
            raise SystemExit(f"Refusing Codex edit: existing server {name} changed")
    return _commit(path, raw, updated.encode("utf-8"), backup_dir)


def _merge_claude_hooks(path: Path, root: Path, backup_dir: Path) -> dict[str, str]:
    if not path.exists():
        print(f"SKIP missing {path}", file=sys.stderr)
        return {"status": "missing", "path": str(path)}
    raw = path.read_bytes()
    original_text = raw.decode("utf-8-sig")
    original_data = json.loads(original_text)
    if not isinstance(original_data.get("hooks"), dict):
        print(f"SKIP no hooks object {path}", file=sys.stderr)
        return {"status": "skipped", "path": str(path)}
    pre = f'pwsh -NoProfile -File "{(root / "scripts" / HOOK_PRE).as_posix()}"'
    prompt = f'pwsh -NoProfile -File "{(root / "scripts" / HOOK_PROMPT).as_posix()}"'
    updated = original_text
    changed = False
    if not _hook_marker(original_data, "PreToolUse", HOOK_PRE):
        updated = _insert_hooks_property(updated, "PreToolUse", pre, timeout=5)
        changed = True
    if not _hook_marker(original_data, "UserPromptSubmit", HOOK_PROMPT):
        updated = _append_hook_group(updated, "UserPromptSubmit", prompt, timeout=3)
        changed = True
    if not changed:
        return {"status": "unchanged", "path": str(path)}
    parsed = json.loads(updated)
    if (parsed.get("permissions") or {}).get("defaultMode") != (
        original_data.get("permissions") or {}
    ).get("defaultMode"):
        raise SystemExit("Refusing Claude settings edit: defaultMode changed")
    if parsed.get("model") != original_data.get("model"):
        raise SystemExit("Refusing Claude settings edit: model changed")
    for key, value in original_data.items():
        if key != "hooks" and parsed.get(key) != value:
            raise SystemExit(f"Refusing Claude settings edit: {key} changed")
    return _commit(path, raw, updated.encode("utf-8"), backup_dir)


def _hook_marker(data: dict[str, Any], event: str, marker: str) -> bool:
    for group in (data.get("hooks") or {}).get(event) or []:
        for hook in group.get("hooks") or []:
            if marker in str(hook.get("command")):
                return True
    return False


def _insert_hooks_property(text: str, event: str, command: str, *, timeout: int) -> str:
    key_at = _top_level_key(text, "hooks")
    brace = text.find("{", key_at)
    end = _matching_brace(text, brace)
    group = json.dumps({"hooks": [{"type": "command", "command": command, "timeout": timeout}]})
    insertion = f'\n    "{event}": [{group}]'
    return text[:end] + "," + insertion + text[end:]


def _append_hook_group(text: str, event: str, command: str, *, timeout: int) -> str:
    hooks_at = _top_level_key(text, "hooks")
    hooks_end = _matching_brace(text, text.find("{", hooks_at))
    region = text[hooks_at:hooks_end]
    relative = region.find(f'"{event}"')
    if relative < 0:
        return _insert_hooks_property(text, event, command, timeout=timeout)
    bracket = text.find("[", hooks_at + relative)
    end = _matching_bracket(text, bracket)
    group = json.dumps(
        {"hooks": [{"type": "command", "command": command, "timeout": timeout}]}
    )
    return text[:end] + ", " + group + text[end:]


def _matching_bracket(text: str, open_index: int) -> int:
    depth_brace = 0
    depth_bracket = 0
    in_str = False
    esc = False
    for i in range(open_index, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket -= 1
            if depth_bracket == 0 and depth_brace == 0:
                return i
    raise ValueError("unbalanced json array")


def _append_marker(path: Path, block: str, backup_dir: Path) -> dict[str, str]:
    if not path.exists():
        print(f"SKIP missing {path}", file=sys.stderr)
        return {"status": "missing", "path": str(path)}
    raw = path.read_bytes()
    original = raw.decode("utf-8")
    if MARKER in original:
        return {"status": "unchanged", "path": str(path)}
    updated = original
    if updated and not updated.endswith("\n"):
        updated += "\n"
    updated += "\n" + block
    if not updated.endswith("\n"):
        updated += "\n"
    return _commit(path, raw, updated.encode("utf-8"), backup_dir)


def _write_if_absent(path: Path, content: str, backup_dir: Path) -> dict[str, str]:
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if MARKER in current:
            return {"status": "unchanged", "path": str(path)}
        print(f"SKIP existing unmanaged {path}", file=sys.stderr)
        return {"status": "skipped", "path": str(path)}
    path.parent.mkdir(parents=True, exist_ok=True)
    # No previous bytes. Rollback removes the file only when the after hash still matches.
    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
    return {
        "status": "written",
        "path": str(path),
        "backup": "",
        "before_sha": "",
        "after_sha": _sha(path),
        "created": "true",
    }


def _commit(path: Path, before: bytes, after: bytes, backup_dir: Path) -> dict[str, str]:
    backup = backup_dir / (path.name + ".bak")
    # Disambiguate identical filenames from different directories.
    if backup.exists():
        backup = backup_dir / f"{path.parent.name}-{path.name}.bak"
    backup.write_bytes(before)
    path.write_bytes(after)
    return {
        "status": "written",
        "path": str(path),
        "backup": str(backup),
        "before_sha": hashlib.sha256(before).hexdigest(),
        "after_sha": hashlib.sha256(after).hexdigest(),
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "apply"
    if command == "apply":
        apply()
        return 0
    if command == "rollback":
        receipt = Path(args[1]) if len(args) > 1 else json.loads(
            (ROOT / "backups" / "latest.json").read_text(encoding="utf-8")
        )["receipt"]
        return rollback(Path(receipt))
    print("usage: python -m jev_engineering.install_config apply|rollback [receipt]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
