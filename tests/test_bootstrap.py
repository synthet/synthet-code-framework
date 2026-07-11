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
    ".agents/skills/validate-implementation/SKILL.md",
    ".codex/config.toml",
    ".codex/README.md",
    ".codex/agents/pr-ready-hygiene.toml",
    ".agent/SAFETY.md",
    ".agent-memory/memory.md",
    "docs/CANONICAL_SOURCES.md",
    "scripts/sync_assistant_trees.py",
    "scripts/ci/check_agent_frontmatter.py",
    "scripts/ci/check_secrets.py",
]

# Framework-only paths that must NOT ship to seeded projects.
FRAMEWORK_ONLY = ["bootstrap.py", "tests", ".github", ".git"]


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


def test_board_ids_become_todo_markers(tmp_path: Path) -> None:
    target = run_bootstrap(tmp_path, "python")
    backlog = (target / "docs/project/00-backlog-workflow.md").read_text(encoding="utf-8")
    assert "TODO(PROJECT_BOARD_URL)" in backlog
    assert not unresolved_placeholders(backlog)


def test_assistant_trees_consistent(tmp_path: Path) -> None:
    target = run_bootstrap(tmp_path, "generic")
    claude_cmds = {p.name for p in (target / ".claude/commands").glob("*.md")}
    cursor_cmds = {p.name for p in (target / ".cursor/commands").glob("*.md")}
    assert claude_cmds == cursor_cmds

    claude_skills = {p.name for p in (target / ".claude/skills").iterdir() if p.is_dir()}
    cursor_skills = {p.name for p in (target / ".cursor/skills").iterdir() if p.is_dir()}
    assert claude_skills == cursor_skills

    codex_skills = {p.name for p in (target / ".agents/skills").iterdir() if p.is_dir()}
    assert claude_skills == codex_skills

    claude_rules = {p.stem for p in (target / ".claude/rules").glob("*.md")}
    cursor_rules = {p.stem for p in (target / ".cursor/rules").glob("*.mdc")}
    assert claude_rules == cursor_rules

    claude_agents = {p.stem for p in (target / ".claude/agents").glob("*.md")}
    codex_agents = {p.stem for p in (target / ".codex/agents").glob("*.toml")}
    assert claude_agents == codex_agents


def test_seeded_codex_toml_is_valid(tmp_path: Path) -> None:
    import tomllib

    target = run_bootstrap(tmp_path, "generic")
    config = tomllib.loads((target / ".codex/config.toml").read_text(encoding="utf-8"))
    assert config["agents"]["max_threads"] == 4
    assert config["mcp_servers"]["openaiDeveloperDocs"]["url"].startswith("https://")

    for agent_path in (target / ".codex/agents").glob("*.toml"):
        agent = tomllib.loads(agent_path.read_text(encoding="utf-8"))
        assert agent["name"] == agent_path.stem
        assert agent["description"]
        assert agent["developer_instructions"]


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
