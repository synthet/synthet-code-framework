#!/usr/bin/env python3
"""Generate the Cursor assistant tree (.cursor/) from the canonical Claude tree (.claude/).

Single source of truth: author rules/commands/skills/agents under `.claude/`, then run this script
to regenerate `.cursor/`. Idempotent: re-running produces no diff.

Mappings:
  .claude/commands/*.md        -> .cursor/commands/*.md       (verbatim)
  .claude/skills/<n>/**        -> .cursor/skills/<n>/**       (verbatim, whole dir)
  .claude/agents/*.md          -> .cursor/agents/*.md         (verbatim)
  .claude/rules/*.md           -> .cursor/rules/*.mdc         (extension change; content kept)

`.cursor/mcp.example.json` and other hand-authored Cursor files are left untouched.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / ".claude"
CURSOR = ROOT / ".cursor"

# (subdir, dest_subdir, mode) — mode: "tree" copies whole dir, "rules" converts .md->.mdc
SUBDIRS = [
    ("commands", "commands", "files"),
    ("skills", "skills", "tree"),
    ("agents", "agents", "files"),
    ("rules", "rules", "rules"),
]


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def sync(
    check: bool = False,
    claude_root: Path | None = None,
    cursor_root: Path | None = None,
) -> int:
    claude_root = claude_root or CLAUDE
    cursor_root = cursor_root or CURSOR
    changes: list[str] = []
    for src_name, dst_name, mode in SUBDIRS:
        src = claude_root / src_name
        dst = cursor_root / dst_name
        if not src.is_dir():
            continue
        if check:
            changes.extend(_diff(src, dst, mode))
            continue
        _reset_dir(dst)
        if mode == "tree":
            for child in sorted(src.iterdir()):
                if child.is_dir():
                    shutil.copytree(child, dst / child.name)
                else:
                    shutil.copy2(child, dst / child.name)
        elif mode == "rules":
            for md in sorted(src.glob("*.md")):
                (dst / f"{md.stem}.mdc").write_text(
                    md.read_text(encoding="utf-8"), encoding="utf-8"
                )
        else:  # files
            for md in sorted(src.glob("*.md")):
                shutil.copy2(md, dst / md.name)
        print(f"synced {src_name} -> .cursor/{dst_name}")
    if check:
        if changes:
            print("OUT OF SYNC:")
            for c in changes:
                print(f"  {c}")
            return 1
        print("in sync")
    return 0


def _expected_name(p: Path, mode: str) -> str:
    return f"{p.stem}.mdc" if mode == "rules" else p.name


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _compare_file_sets(
    src_files: dict[str, Path], dst_files: dict[str, Path], dst_label: str
) -> list[str]:
    out: list[str] = []
    src_names = set(src_files)
    dst_names = set(dst_files)
    for name in sorted(src_names - dst_names):
        out.append(f"missing in .cursor: {dst_label}/{name}")
    for name in sorted(dst_names - src_names):
        out.append(f"stale in .cursor: {dst_label}/{name}")
    for name in sorted(src_names & dst_names):
        if _read(src_files[name]) != _read(dst_files[name]):
            out.append(f"differs: {dst_label}/{name}")
    return out


def _diff(src: Path, dst: Path, mode: str) -> list[str]:
    if mode == "tree":
        src_files = {str(p.relative_to(src)): p for p in src.rglob("*") if p.is_file()}
        dst_files = (
            {str(p.relative_to(dst)): p for p in dst.rglob("*") if p.is_file()}
            if dst.is_dir()
            else {}
        )
        return _compare_file_sets(src_files, dst_files, dst.name)

    src_files = {_expected_name(f, mode): f for f in sorted(src.glob("*.md"))}
    dst_pattern = "*.mdc" if mode == "rules" else "*.md"
    dst_files = (
        {f.name: f for f in sorted(dst.glob(dst_pattern))} if dst.is_dir() else {}
    )
    return _compare_file_sets(src_files, dst_files, dst.name)


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync .cursor/ from .claude/")
    ap.add_argument(
        "--check", action="store_true", help="Report drift without writing (CI gate)"
    )
    args = ap.parse_args()
    return sync(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
