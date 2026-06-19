#!/usr/bin/env python3
"""Seed a new project from synthet-code-framework.

Copies this framework's scaffold into a target directory and substitutes ${PLACEHOLDER} tokens.

Usage:
    python bootstrap.py --target ../my-app --name "My App" --stack python
    python bootstrap.py --target ../my-app --name "My App" --desc "..." --stack node \
        --repo-url https://github.com/me/my-app

Placeholders resolved here:
    PROJECT_NAME, PROJECT_SLUG, PROJECT_DESC, REPO_URL, STACK,
    BUILD_CMD, TEST_CMD, LINT_CMD, MCP_PREFIX, PROJECT_BOARD_URL,
    PROJECT_OWNER, PROJECT_REPO, PROJECT_NUMBER, PROJECT_NODE_ID,
    STAGE_FIELD_ID + STAGE_*_ID

Board/stage IDs can't be known at seed time; unset ones become a clear `TODO(<KEY>)` marker you fill
in from your GitHub Project later (so no raw ${...} tokens remain).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# Import lazily to avoid hard dependency when running --detect-only without full install
def _detect_commands(target: Path, stack: str) -> dict[str, str]:
    try:
        from scripts.detect_commands import detect_commands
        return detect_commands(target, stack)
    except ImportError:
        return {}

FRAMEWORK_ROOT = Path(__file__).resolve().parent
PLACEHOLDER_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")

# Paths (relative to framework root) NOT copied into a seeded project.
EXCLUDE = {
    ".git",
    "bootstrap.py",
    "README.md",        # framework README; replaced with a minimal project README
}
EXCLUDE_DIR_NAMES = {"__pycache__", ".agent-runs"}
# Working dirs: copy the dir (and .gitkeep) but not their contents.
EMPTY_KEEP_DIRS = {
    Path(".agent/scratch"),
    Path(".agent-memory/raw-sessions"),
    Path(".agent-memory/dreams"),
}

STACK_DEFAULTS = {
    "python": {
        "BUILD_CMD": "pip install -e .",
        "TEST_CMD": "python -m pytest",
        "LINT_CMD": "ruff check .",
    },
    "node": {
        "BUILD_CMD": "npm run build",
        "TEST_CMD": "npm test",
        "LINT_CMD": "npm run lint && npx tsc --noEmit",
    },
    "go": {
        "BUILD_CMD": "go build ./...",
        "TEST_CMD": "go test ./...",
        "LINT_CMD": "go vet ./... && gofmt -l .",
    },
    "generic": {
        "BUILD_CMD": "<build command>",
        "TEST_CMD": "<test command>",
        "LINT_CMD": "<lint command>",
    },
}

BOARD_KEYS = [
    "PROJECT_BOARD_URL", "PROJECT_OWNER", "PROJECT_REPO", "PROJECT_NUMBER",
    "PROJECT_NODE_ID", "STAGE_FIELD_ID", "STAGE_BACKLOG_ID", "STAGE_READY_ID",
    "STAGE_CLAIMED_ID", "STAGE_IN_PROGRESS_ID", "STAGE_BLOCKED_ID",
    "STAGE_REVIEW_ID", "STAGE_DONE_ID",
]

TEXT_SUFFIXES = {".md", ".mdc", ".json", ".txt", ".py", ".yml", ".yaml", ".toml", ".cfg", ".gitignore"}


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "project"


def build_values(args: argparse.Namespace) -> dict[str, str]:
    slug = args.slug or slugify(args.name)
    stack = args.stack if args.stack in STACK_DEFAULTS else "generic"
    vals: dict[str, str] = {
        "PROJECT_NAME": args.name,
        "PROJECT_SLUG": slug,
        "PROJECT_DESC": args.desc or "TODO(PROJECT_DESC)",
        "REPO_URL": args.repo_url or "TODO(REPO_URL)",
        "STACK": stack,
        "MCP_PREFIX": args.mcp_prefix or slug,
        **STACK_DEFAULTS[stack],
    }
    for key in BOARD_KEYS:
        vals[key] = f"TODO({key})"
    if args.board_url:
        vals["PROJECT_BOARD_URL"] = args.board_url
    if args.owner:
        vals["PROJECT_OWNER"] = args.owner
        vals["PROJECT_REPO"] = args.repo or slug
    return vals


def substitute(text: str, vals: dict[str, str]) -> str:
    return PLACEHOLDER_RE.sub(lambda m: vals.get(m.group(1), m.group(0)), text)


def is_text(path: Path) -> bool:
    return path.suffix in TEXT_SUFFIXES or path.name == ".gitignore"


def iter_sources() -> list[Path]:
    out: list[Path] = []
    for p in FRAMEWORK_ROOT.rglob("*"):
        rel = p.relative_to(FRAMEWORK_ROOT)
        parts = set(rel.parts)
        if parts & EXCLUDE_DIR_NAMES:
            continue
        if rel.parts and rel.parts[0] in EXCLUDE or str(rel) in EXCLUDE:
            continue
        # Skip contents of working dirs except .gitkeep
        if any(_under(rel, d) and rel.name != ".gitkeep" for d in EMPTY_KEEP_DIRS) and p.is_file():
            continue
        out.append(p)
    return out


def _under(rel: Path, base: Path) -> bool:
    return rel != base and str(rel).replace("\\", "/").startswith(str(base).replace("\\", "/") + "/")


def project_readme(vals: dict[str, str]) -> str:
    return (
        f"# {vals['PROJECT_NAME']}\n\n{vals['PROJECT_DESC']}\n\n"
        "Seeded from **synthet-code-framework**. Agent scaffolding lives in `.claude/`, `.cursor/`,\n"
        "`.agent/`, and `.agent-memory/`. Start with [`CLAUDE.md`](CLAUDE.md) and [`AGENTS.md`](AGENTS.md).\n\n"
        "Fill in build/test/lint commands in `CLAUDE.md` + `AGENTS.md`, and your GitHub Project board\n"
        "IDs (search for `TODO(` markers).\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed a project from synthet-code-framework")
    ap.add_argument("--target", required=True, type=Path, help="Destination directory")
    ap.add_argument("--name", help="Project display name (required unless --detect-only)")
    ap.add_argument("--slug", help="Project slug (default: derived from name)")
    ap.add_argument("--desc", help="One-line description")
    ap.add_argument("--stack", default="generic", help="python|node|go|generic")
    ap.add_argument("--repo-url", help="Git remote URL")
    ap.add_argument("--mcp-prefix", help="MCP server name prefix (default: slug)")
    ap.add_argument("--board-url", help="GitHub Project board URL")
    ap.add_argument("--owner", help="GitHub owner")
    ap.add_argument("--repo", help="GitHub repo name (default: slug)")
    ap.add_argument("--force", action="store_true", help="Allow non-empty target")
    ap.add_argument(
        "--auto-detect",
        action="store_true",
        help="After seeding, probe target for build/test/lint commands and fill them in",
    )
    ap.add_argument(
        "--detect-only",
        action="store_true",
        help="Only probe --target for commands (no seeding); useful for existing projects",
    )
    args = ap.parse_args()

    target: Path = args.target.resolve()

    if args.detect_only:
        if not target.is_dir():
            print(f"ERROR: target {target} is not a directory", file=sys.stderr)
            return 1
        if not args.name and not args.detect_only:
            print("ERROR: --name is required unless --detect-only is set", file=sys.stderr)
            return 1
        stack = args.stack if args.stack in STACK_DEFAULTS else "generic"
        detected = _detect_commands(target, stack)
        if not detected:
            print("No commands detected (no recognised config files found).")
        else:
            for key, value in detected.items():
                print(f"{key}={value}")
        return 0

    if not args.name:
        print("ERROR: --name is required", file=sys.stderr)
        return 1

    if target.exists() and any(target.iterdir()) and not args.force:
        print(f"ERROR: target {target} is not empty (use --force)", file=sys.stderr)
        return 1

    vals = build_values(args)
    count = 0
    for src in iter_sources():
        rel = src.relative_to(FRAMEWORK_ROOT)
        dst = target / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if is_text(src):
            dst.write_text(substitute(src.read_text(encoding="utf-8"), vals), encoding="utf-8")
        else:
            shutil.copy2(src, dst)
        count += 1

    (target / "README.md").write_text(project_readme(vals), encoding="utf-8")

    print(f"Seeded '{vals['PROJECT_NAME']}' into {target} ({count} files).")

    if args.auto_detect:
        stack = args.stack if args.stack in STACK_DEFAULTS else "generic"
        detected = _detect_commands(target, stack)
        if detected:
            print(f"\nAuto-detected commands (stack: {stack}):")
            _apply_detected_commands(target, detected, vals)
            for key, value in detected.items():
                print(f"  {key} = {value}")
            missing = [k for k in ("BUILD_CMD", "TEST_CMD", "LINT_CMD") if k not in detected]
            if missing:
                print(f"  Still TODO: {', '.join(missing)}")
        else:
            print("\nAuto-detect: no recognised config files found — fill in commands manually.")

    print("\nNext steps:")
    if not args.auto_detect:
        print("  1. cd into the target and `git init` (or push to your remote).")
        print("  2. Fill in build/test/lint commands in CLAUDE.md + AGENTS.md.")
        print("  3. Replace TODO(...) markers (board IDs, repo URL) once your Project board exists.")
        print("  4. `python scripts/sync_assistant_trees.py` after editing .claude/ assets.")
    else:
        print("  1. cd into the target and `git init` (or push to your remote).")
        print("  2. Review auto-detected commands in CLAUDE.md + AGENTS.md (marked # auto-detected).")
        print("  3. Replace TODO(...) markers (board IDs, repo URL) once your Project board exists.")
        print("  4. `python scripts/sync_assistant_trees.py` after editing .claude/ assets.")
    return 0


def _apply_detected_commands(
    target: Path, detected: dict[str, str], seeded_vals: dict[str, str]
) -> None:
    """Replace seeded stack-default command values in CLAUDE.md/AGENTS.md with detected ones.

    Replaces the value that was substituted during seeding (e.g. 'pip install -e .') with the
    detected value (e.g. 'poetry install  # auto-detected'). Only replaces when the detected
    value actually differs from the default.
    """
    for filename in ("CLAUDE.md", "AGENTS.md"):
        path = target / filename
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for key, new_value in detected.items():
            old_value = seeded_vals.get(key, "")
            if old_value and old_value != new_value:
                text = text.replace(old_value, f"{new_value}  # auto-detected")
            elif not old_value:
                text = text.replace(f"TODO({key})", f"{new_value}  # auto-detected")
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
