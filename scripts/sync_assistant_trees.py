#!/usr/bin/env python3
"""Generate Cursor and Codex assets from the canonical Claude tree.

Single source of truth: author rules, commands, skills, and agents under
``.claude/``, then run this script. Re-running is idempotent.

Mappings:
  .claude/commands/*.md  -> .cursor/commands/*.md        (verbatim)
  .claude/skills/**      -> .cursor/skills/**            (verbatim)
  .claude/agents/*.md    -> .cursor/agents/*.md          (verbatim)
  .claude/rules/*.md     -> .cursor/rules/*.mdc          (extension change)
  .claude/skills/**      -> .agents/skills/**            (Codex, verbatim)
  .claude/agents/*.md    -> .codex/agents/*.toml         (Codex config layer)

Hand-authored files such as ``.cursor/mcp.example.json`` and
``.codex/config.toml`` are left untouched.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / ".claude"
CURSOR = ROOT / ".cursor"
CODEX_SKILLS = ROOT / ".agents" / "skills"
CODEX_AGENTS = ROOT / ".codex" / "agents"

# (source subdir, destination, mode)
CURSOR_TARGETS = [
    ("commands", CURSOR / "commands", "files"),
    ("skills", CURSOR / "skills", "tree"),
    ("agents", CURSOR / "agents", "files"),
    ("rules", CURSOR / "rules", "rules"),
]

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")


def _reset_dir(path: Path) -> None:
    resolved_root = ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_path == resolved_root or resolved_root not in resolved_path.parents:
        raise ValueError(f"refusing to reset path outside the repository: {resolved_path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _normalise(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _parse_agent(md: Path) -> tuple[str, str, str]:
    """Return name, description, and body from a canonical Claude agent."""
    text = _normalise(md.read_text(encoding="utf-8"))
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{md}: missing or unterminated YAML frontmatter")

    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key_match = _KEY_RE.match(line)
        if key_match:
            metadata[key_match.group(1)] = key_match.group(2).strip().strip("\"'")

    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if not name or not description:
        raise ValueError(f"{md}: agent frontmatter requires name and description")
    if name != md.stem:
        raise ValueError(f"{md}: agent name {name!r} must match file stem {md.stem!r}")

    body = match.group(2).strip()
    if '"""' in body:
        raise ValueError(f'{md}: agent body cannot contain TOML delimiter """')
    return name, description, body


def _render_codex_agent(md: Path) -> str:
    name, description, body = _parse_agent(md)
    return (
        f"name = {json.dumps(name, ensure_ascii=False)}\n"
        f"description = {json.dumps(description, ensure_ascii=False)}\n"
        'developer_instructions = """\n'
        f"{body}\n"
        '"""\n'
    )


def _copy_cursor_target(src: Path, dst: Path, mode: str) -> None:
    _reset_dir(dst)
    if mode == "tree":
        for child in sorted(src.iterdir()):
            if child.is_dir():
                shutil.copytree(child, dst / child.name)
            else:
                shutil.copy2(child, dst / child.name)
    elif mode == "rules":
        for md in sorted(src.glob("*.md")):
            # Preserve bytes/newlines exactly; only the extension changes.
            shutil.copyfile(md, dst / f"{md.stem}.mdc")
    else:
        for md in sorted(src.glob("*.md")):
            shutil.copy2(md, dst / md.name)


def _sync_codex() -> None:
    _reset_dir(CODEX_SKILLS)
    for child in sorted((CLAUDE / "skills").iterdir()):
        if child.is_dir():
            shutil.copytree(child, CODEX_SKILLS / child.name)
        else:
            shutil.copy2(child, CODEX_SKILLS / child.name)

    _reset_dir(CODEX_AGENTS)
    for md in sorted((CLAUDE / "agents").glob("*.md")):
        (CODEX_AGENTS / f"{md.stem}.toml").write_text(
            _render_codex_agent(md), encoding="utf-8", newline="\n"
        )


def sync(check: bool = False) -> int:
    if check:
        changes: list[str] = []
        for src_name, dst, mode in CURSOR_TARGETS:
            changes.extend(_diff_cursor(CLAUDE / src_name, dst, mode))
        changes.extend(_diff_tree(CLAUDE / "skills", CODEX_SKILLS, ".agents/skills"))
        changes.extend(_diff_codex_agents())
        if changes:
            print("OUT OF SYNC:")
            for change in changes:
                print(f"  {change}")
            return 1
        print("in sync: .cursor, .agents/skills, .codex/agents")
        return 0

    for src_name, dst, mode in CURSOR_TARGETS:
        _copy_cursor_target(CLAUDE / src_name, dst, mode)
        print(f"synced {src_name} -> {dst.relative_to(ROOT).as_posix()}")
    _sync_codex()
    print("synced skills -> .agents/skills")
    print("synced agents -> .codex/agents")
    return 0


def _file_map(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file()
    }


def _diff_tree(src: Path, dst: Path, label: str | None = None) -> list[str]:
    """Recursively compare two trees, including nested content and stale files."""
    out: list[str] = []
    src_files = _file_map(src)
    dst_files = _file_map(dst)
    display = label or dst.as_posix()
    for rel in sorted(src_files.keys() - dst_files.keys()):
        out.append(f"missing in {display}: {rel}")
    for rel in sorted(dst_files.keys() - src_files.keys()):
        out.append(f"stale in {display}: {rel}")
    for rel in sorted(src_files.keys() & dst_files.keys()):
        if src_files[rel].read_bytes() != dst_files[rel].read_bytes():
            out.append(f"differs: {display}/{rel}")
    return out


def _diff_cursor(src: Path, dst: Path, mode: str) -> list[str]:
    if mode == "tree":
        return _diff_tree(src, dst, f".cursor/{dst.name}")

    out: list[str] = []
    expected = {
        (f"{path.stem}.mdc" if mode == "rules" else path.name): path
        for path in src.glob("*.md")
    }
    actual = {path.name: path for path in dst.glob("*") if path.is_file()} if dst.is_dir() else {}
    for name in sorted(expected.keys() - actual.keys()):
        out.append(f"missing in .cursor/{dst.name}: {name}")
    for name in sorted(actual.keys() - expected.keys()):
        out.append(f"stale in .cursor/{dst.name}: {name}")
    for name in sorted(expected.keys() & actual.keys()):
        if expected[name].read_bytes() != actual[name].read_bytes():
            out.append(f"differs: .cursor/{dst.name}/{name}")
    return out


def _diff_codex_agents() -> list[str]:
    out: list[str] = []
    expected = {
        f"{md.stem}.toml": _render_codex_agent(md)
        for md in (CLAUDE / "agents").glob("*.md")
    }
    actual = (
        {path.name: path for path in CODEX_AGENTS.glob("*.toml")}
        if CODEX_AGENTS.is_dir()
        else {}
    )
    for name in sorted(expected.keys() - actual.keys()):
        out.append(f"missing in .codex/agents: {name}")
    for name in sorted(actual.keys() - expected.keys()):
        out.append(f"stale in .codex/agents: {name}")
    for name in sorted(expected.keys() & actual.keys()):
        if _normalise(actual[name].read_text(encoding="utf-8")) != expected[name]:
            out.append(f"differs: .codex/agents/{name}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Cursor and Codex assets from .claude/"
    )
    parser.add_argument("--check", action="store_true", help="Report drift without writing")
    args = parser.parse_args()
    return sync(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
