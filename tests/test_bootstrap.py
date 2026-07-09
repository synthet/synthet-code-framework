"""Combinatorial tests for bootstrap.py: seed every supported stack and prove the output."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import bootstrap  # noqa: E402

STACKS = sorted(bootstrap.STACK_DEFAULTS)
RAW_PLACEHOLDER_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")

# Placeholders bootstrap.py is responsible for resolving. Other ${...} tokens
# (e.g. shell examples in scripts) are intentionally left alone.
KNOWN_KEYS = frozenset(
    ["PROJECT_NAME", "PROJECT_SLUG", "PROJECT_DESC", "REPO_URL", "STACK", "MCP_PREFIX",
     "BUILD_CMD", "TEST_CMD", "LINT_CMD", *bootstrap.BOARD_KEYS]
)


def unresolved_placeholders(text: str) -> list[str]:
    return [k for k in RAW_PLACEHOLDER_RE.findall(text) if k in KNOWN_KEYS]

# Files every seeded project must contain.
REQUIRED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "CHANGELOG.md",
    "env.example",
    ".gitignore",
    ".mcp.json",
    ".claude/rules/sdlc-core.md",
    ".claude/commands/spec.md",
    ".claude/skills/validate-implementation/SKILL.md",
    ".cursor/rules/sdlc-core.mdc",
    ".cursor/commands/spec.md",
    ".agent/SAFETY.md",
    ".agent-memory/memory.md",
    "docs/CANONICAL_SOURCES.md",
    "scripts/sync_assistant_trees.py",
    "scripts/ci/check_agent_frontmatter.py",
    "scripts/ci/check_secrets.py",
    ".github/workflows/project-ci.yml",
    ".github/workflows/dependency-review.yml",
    ".github/workflows/codeql.yml",
]

# Framework-only paths that must NOT ship to seeded projects.
# `.github` is intentionally generated when CI templates are included.
FRAMEWORK_ONLY = ["bootstrap.py", "tests", ".git"]


def run_bootstrap(tmp_path: Path, stack: str, extra: list[str] | None = None) -> Path:
    target = tmp_path / f"seeded-{stack}"
    argv = [
        "bootstrap.py",
        "--target", str(target),
        "--name", "Demo App",
        "--desc", "A demo project",
        "--stack", stack,
        "--repo-url", "https://github.com/example/demo-app",
        *(extra or []),
    ]
    old_argv = sys.argv
    sys.argv = argv
    try:
        assert bootstrap.main() == 0
    finally:
        sys.argv = old_argv
    return target


def iter_text_files(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and bootstrap.is_text(p):
            yield p


@pytest.mark.parametrize("stack", STACKS)
def test_seed_stack(tmp_path: Path, stack: str) -> None:
    target = run_bootstrap(tmp_path, stack)

    for rel in REQUIRED_FILES:
        assert (target / rel).is_file(), f"missing {rel}"
    for rel in FRAMEWORK_ONLY:
        assert not (target / rel).exists(), f"framework-only path shipped: {rel}"

    for p in iter_text_files(target):
        leftover = unresolved_placeholders(p.read_text(encoding="utf-8"))
        assert not leftover, f"raw placeholders {leftover} left in {p.relative_to(target)}"

    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    if stack != "generic":
        assert bootstrap.STACK_DEFAULTS[stack]["TEST_CMD"] in agents

    claude_md = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Demo App" in claude_md


def test_ci_workflows_included_by_default(tmp_path: Path) -> None:
    target = run_bootstrap(tmp_path, "python")

    workflows = target / ".github" / "workflows"
    assert (workflows / "project-ci.yml").is_file()
    assert (workflows / "dependency-review.yml").is_file()
    assert (workflows / "codeql.yml").is_file()

    project_ci = (workflows / "project-ci.yml").read_text(encoding="utf-8")
    assert "permissions:" in project_ci
    assert "contents: read" in project_ci
    assert bootstrap.STACK_DEFAULTS["python"]["BUILD_CMD"] in project_ci
    assert bootstrap.STACK_DEFAULTS["python"]["TEST_CMD"] in project_ci
    assert bootstrap.STACK_DEFAULTS["python"]["LINT_CMD"] in project_ci

    dependency_review = (workflows / "dependency-review.yml").read_text(encoding="utf-8")
    codeql = (workflows / "codeql.yml").read_text(encoding="utf-8")
    assert "contents: read" in dependency_review
    assert "actions/dependency-review-action" in dependency_review
    assert "contents: read" in codeql
    assert "github/codeql-action/init" in codeql


def test_ci_workflows_can_be_intentionally_skipped(tmp_path: Path) -> None:
    target = run_bootstrap(tmp_path, "python", ["--no-include-ci"])

    assert not (target / ".github" / "workflows" / "project-ci.yml").exists()
    assert not (target / ".github" / "workflows" / "dependency-review.yml").exists()
    assert not (target / ".github" / "workflows" / "codeql.yml").exists()
    assert not (target / ".github-template").exists()


def test_include_ci_flag_is_explicit_default(tmp_path: Path) -> None:
    target = run_bootstrap(tmp_path, "python", ["--include-ci"])

    assert (target / ".github" / "workflows" / "project-ci.yml").is_file()
    assert (target / ".github" / "workflows" / "dependency-review.yml").is_file()
    assert (target / ".github" / "workflows" / "codeql.yml").is_file()


def test_board_ids_become_todo_markers(tmp_path: Path) -> None:
    target = run_bootstrap(tmp_path, "python")
    backlog = (target / "docs/project/00-backlog-workflow.md").read_text(encoding="utf-8")
    assert "TODO(PROJECT_BOARD_URL)" in backlog
    assert not unresolved_placeholders(backlog)


def test_claude_cursor_trees_consistent(tmp_path: Path) -> None:
    target = run_bootstrap(tmp_path, "generic")
    claude_cmds = {p.name for p in (target / ".claude/commands").glob("*.md")}
    cursor_cmds = {p.name for p in (target / ".cursor/commands").glob("*.md")}
    assert claude_cmds == cursor_cmds

    claude_skills = {p.name for p in (target / ".claude/skills").iterdir() if p.is_dir()}
    cursor_skills = {p.name for p in (target / ".cursor/skills").iterdir() if p.is_dir()}
    assert claude_skills == cursor_skills

    claude_rules = {p.stem for p in (target / ".claude/rules").glob("*.md")}
    cursor_rules = {p.stem for p in (target / ".cursor/rules").glob("*.mdc")}
    assert claude_rules == cursor_rules


def test_working_dirs_kept_empty(tmp_path: Path) -> None:
    target = run_bootstrap(tmp_path, "python")
    for rel in bootstrap.EMPTY_KEEP_DIRS:
        d = target / rel
        assert d.is_dir(), f"missing working dir {rel}"
        contents = [p.name for p in d.iterdir()]
        assert contents in ([], [".gitkeep"]), f"{rel} not empty: {contents}"


def test_dry_run_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "seeded-dry"
    argv = [
        "bootstrap.py", "--target", str(target), "--name", "Demo App",
        "--stack", "python", "--dry-run",
    ]
    old_argv = sys.argv
    sys.argv = argv
    try:
        assert bootstrap.main() == 0
    finally:
        sys.argv = old_argv
    assert not target.exists()
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "AGENTS.md" in out


def test_non_empty_target_rejected(tmp_path: Path) -> None:
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "existing.txt").write_text("hi", encoding="utf-8")
    argv = ["bootstrap.py", "--target", str(target), "--name", "Demo App"]
    old_argv = sys.argv
    sys.argv = argv
    try:
        assert bootstrap.main() == 1
    finally:
        sys.argv = old_argv

def test_private_and_working_dir_files_are_not_seeded_from_source_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "framework"
    source.mkdir()
    public_files = [
        "AGENTS.md",
        "CLAUDE.md",
        ".gitignore",
        "env.example",
        ".cursor/mcp.example.json",
        ".agent/scratch/.gitkeep",
    ]
    private_files = [
        ".cursor/mcp.json",
        ".claude/settings.local.json",
        "secrets.json",
        ".env",
        ".env.local",
        ".agent/scratch/local-notes.md",
    ]
    for rel in [*public_files, *private_files]:
        path = source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"contents for {rel}\n", encoding="utf-8")

    monkeypatch.setattr(bootstrap, "FRAMEWORK_ROOT", source)
    monkeypatch.setattr(
        bootstrap,
        "_tracked_source_paths",
        lambda: sorted(Path(rel) for rel in [*public_files, *private_files]),
    )

    target = run_bootstrap(tmp_path, "python", ["--no-include-ci"])

    assert (target / ".cursor/mcp.example.json").is_file()
    assert (target / ".agent/scratch").is_dir()
    assert (target / ".agent/scratch/.gitkeep").is_file()
    for rel in private_files:
        if rel == ".agent/scratch/local-notes.md":
            assert not (target / rel).exists(), "working-dir contents should not be seeded"
        else:
            assert not (target / rel).exists(), f"private source path seeded: {rel}"
