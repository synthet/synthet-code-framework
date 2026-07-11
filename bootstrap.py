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

GitHub Projects board/stage IDs are optional provider settings. Unset ones become clear
`TODO(<KEY>)` markers, but generic projects can use Local Markdown or GitHub Issues without filling
them in.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
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

# Paths (relative to framework root) NOT copied into a seeded project (framework-only assets).
EXCLUDE = {
    ".git",
    ".github",          # framework CI (tests bootstrap.py, which is not shipped)
    ".github-template",  # starter CI templates copied to .github/workflows when enabled
    "tests",            # framework self-tests
    "bootstrap.py",
    "README.md",        # framework README; replaced with a minimal project README
    "CHANGELOG.md",     # framework history; replaced with a fresh skeleton
}
EXCLUDE_DIR_NAMES = {"__pycache__", ".agent-runs"}
# Local/private files documented in .gitignore that must never be seeded,
# even if they exist in a dirty source checkout or are accidentally tracked.
PRIVATE_SOURCE_PATHS = {
    Path(".cursor/mcp.json"),
    Path(".claude/settings.local.json"),
    Path("secrets.json"),
    Path(".env"),
}
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
    return path.suffix in TEXT_SUFFIXES or path.name in {".gitignore", "env.example"}


def _tracked_source_paths() -> list[Path]:
    """Return tracked files in FRAMEWORK_ROOT using git's index as the source manifest."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(FRAMEWORK_ROOT), "ls-files", "-z"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            f"Unable to enumerate tracked scaffold files from {FRAMEWORK_ROOT}; "
            "run bootstrap.py from a git checkout or provide a tracked-file manifest."
        ) from exc

    return sorted(Path(raw) for raw in proc.stdout.decode("utf-8").split("\0") if raw)


def _is_private_source_path(rel: Path) -> bool:
    return rel in PRIVATE_SOURCE_PATHS or rel.match(".env.*")


def _is_excluded_source_path(rel: Path) -> bool:
    parts = set(rel.parts)
    if parts & EXCLUDE_DIR_NAMES:
        return True
    if rel.parts and rel.parts[0] in EXCLUDE or str(rel) in EXCLUDE:
        return True
    if _is_private_source_path(rel):
        return True
    # Skip contents of working dirs (files and local subdirs) except .gitkeep.
    if any(_under(rel, d) and rel.name != ".gitkeep" for d in EMPTY_KEEP_DIRS):
        return True
    return False


def iter_sources() -> list[Path]:
    out: list[Path] = []
    for rel in _tracked_source_paths():
        if _is_excluded_source_path(rel):
            continue
        src = FRAMEWORK_ROOT / rel
        if src.exists():
            out.append(src)
    return out


def iter_ci_templates() -> list[Path]:
    template_root = FRAMEWORK_ROOT / ".github-template" / "workflows"
    if not template_root.is_dir():
        return []
    return sorted(p for p in template_root.glob("*") if p.is_file())


def _under(rel: Path, base: Path) -> bool:
    return rel != base and str(rel).replace("\\", "/").startswith(str(base).replace("\\", "/") + "/")


def project_changelog(vals: dict[str, str]) -> str:
    return (
        f"# Changelog — {vals['PROJECT_NAME']}\n\n"
        "All notable changes to this project are documented here. Format follows\n"
        "[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow\n"
        "[Semantic Versioning](https://semver.org/).\n\n"
        "## [Unreleased]\n\n"
        "### Added\n\n"
        "- Project seeded from synthet-code-framework.\n"
    )


def project_readme(vals: dict[str, str]) -> str:
    return (
        f"# {vals['PROJECT_NAME']}\n\n{vals['PROJECT_DESC']}\n\n"
        "Seeded from **synthet-code-framework**. Agent scaffolding lives in `.claude/`, `.cursor/`,\n"
        "`.agents/`, `.codex/`, `.agent/`, and `.agent-memory/`. Start with [`CLAUDE.md`](CLAUDE.md)\n"
        "and [`AGENTS.md`](AGENTS.md); Codex setup is documented in [`.codex/README.md`](.codex/README.md).\n\n"
        "Fill in build/test/lint commands in `CLAUDE.md` + `AGENTS.md`, choose a backlog provider,\n"
        "and fill optional provider IDs (for example, GitHub Projects IDs) only when that provider needs them\n"
        "(search for `TODO(` markers).\n"
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
    ci_group = ap.add_mutually_exclusive_group()
    ci_group.add_argument(
        "--include-ci",
        dest="include_ci",
        action="store_true",
        default=True,
        help="Include starter GitHub Actions workflows (default)",
    )
    ci_group.add_argument(
        "--no-include-ci",
        dest="include_ci",
        action="store_false",
        help="Skip starter GitHub Actions workflows",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print planned files without writing")
    args = ap.parse_args()

    target: Path = args.target.resolve()

    if args.detect_only:
        if not target.is_dir():
            print(f"ERROR: target {target} is not a directory", file=sys.stderr)
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

    vals = build_values(args)

    if args.dry_run:
        files = sorted(
            src.relative_to(FRAMEWORK_ROOT).as_posix() for src in iter_sources() if src.is_file()
        )
        if args.include_ci:
            files.extend(f".github/workflows/{src.name}" for src in iter_ci_templates())
            files.sort()
        print(f"DRY RUN: would seed '{vals['PROJECT_NAME']}' into {target}")
        print("Substitutions:")
        for key in sorted(vals):
            print(f"  {key} = {vals[key]}")
        print(f"Files ({len(files)} + generated README.md, CHANGELOG.md):")
        for f in files:
            print(f"  {f}")
        return 0

    if target.exists() and any(target.iterdir()) and not args.force:
        print(f"ERROR: target {target} is not empty (use --force)", file=sys.stderr)
        return 1

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

    if args.include_ci:
        for src in iter_ci_templates():
            dst = target / ".github" / "workflows" / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if is_text(src):
                dst.write_text(substitute(src.read_text(encoding="utf-8"), vals), encoding="utf-8")
            else:
                shutil.copy2(src, dst)
            count += 1

    (target / "README.md").write_text(project_readme(vals), encoding="utf-8")
    (target / "CHANGELOG.md").write_text(project_changelog(vals), encoding="utf-8")

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
        print("  3. Choose a backlog provider; fill GitHub Projects TODO(...) IDs only if you use that provider.")
        print("  4. `python scripts/sync_assistant_trees.py` after editing .claude/ assets.")
    else:
        print("  1. cd into the target and `git init` (or push to your remote).")
        print("  2. Review auto-detected commands in CLAUDE.md + AGENTS.md (marked # auto-detected).")
        print("  3. Choose a backlog provider; fill GitHub Projects TODO(...) IDs only if you use that provider.")
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
