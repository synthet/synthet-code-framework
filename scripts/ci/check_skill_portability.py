#!/usr/bin/env python3
"""Fail when agent assets would not work, or would leak, outside this machine.

Checks skill names and descriptions, and scans asset text for machine paths.
--deny-file adds a local list of names that must not appear. Keep that list out
of public repositories; this script never stores one.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.agent_setup import frontmatter  # noqa: E402

MAX_DESCRIPTION = 1024
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# A drive path into a home or projects folder. /c:/ and <placeholder> forms are not real paths.
MACHINE_PATH = re.compile(r"(?<![/\w])[A-Za-z]:[\\/]+(?:Projects|Users)\b(?![\\/]+[<{$%])")
TEXT = {".md", ".mdc", ".py", ".ps1", ".sh", ".json", ".yaml", ".yml", ".toml", ".txt"}
ASSETS = (".claude/skills", ".claude/commands", ".claude/agents", ".claude/rules")


def check_skill(skill: Path, root: Path) -> list[str]:
    rel = skill.relative_to(root).as_posix()
    meta = frontmatter(skill.read_text(encoding="utf-8"))
    folder = skill.parent.name
    name, description = meta.get("name", ""), meta.get("description", "")
    errors = []
    if name != folder:
        errors.append(f"{rel}: name {name!r} must match folder {folder!r}")
    if not NAME.fullmatch(folder) or len(folder) > 64:
        errors.append(f"{rel}: name must be 1-64 lowercase letters, digits and single hyphens")
    if not description:
        errors.append(f"{rel}: missing description")
    elif len(description) > MAX_DESCRIPTION:
        errors.append(f"{rel}: description has {len(description)} characters, limit {MAX_DESCRIPTION}")
    return errors


def asset_files(root: Path):
    for folder in ASSETS:
        for path in sorted((root / folder).rglob("*")):
            if path.is_file() and path.suffix in TEXT and "__pycache__" not in path.parts:
                yield path


def check_text(path: Path, root: Path, denied: list[str]) -> list[str]:
    rel = path.relative_to(root).as_posix()
    errors = []
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if MACHINE_PATH.search(line):
            errors.append(f"{rel}:{number}: machine path")
        low = line.lower()
        errors += [f"{rel}:{number}: denied name" for name in denied if name in low]
    return errors


def check(root: Path, denied: list[str]) -> list[str]:
    errors = []
    for skill in sorted((root / ".claude/skills").glob("*/SKILL.md")):
        errors += check_skill(skill, root)
    for path in asset_files(root):
        errors += check_text(path, root, denied)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--deny-file", type=Path, help="local file with one denied name per line")
    args = parser.parse_args(argv)
    denied = []
    if args.deny_file:
        denied = [x.strip().lower() for x in args.deny_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    errors = check(args.root.resolve(), denied)
    for error in errors:
        print(error)
    print(f"Skill portability check {'failed: ' + str(len(errors)) + ' problem(s)' if errors else 'passed'}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
