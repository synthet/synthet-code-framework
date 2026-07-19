"""Framework self-verify command catalog and secret path gates."""

from __future__ import annotations

import re
from pathlib import Path

FRAMEWORK_VERIFY_COMMANDS: list[tuple[str, str]] = [
    (
        "okf_lint",
        "python scripts/okf_lint.py --profile project --exclude-prefix archive/ docs",
    ),
    ("sync_check", "python scripts/sync_assistant_trees.py --check"),
    ("frontmatter", "python scripts/ci/check_agent_frontmatter.py"),
    ("cli_skills", "python scripts/validate_cli_skills.py"),
    ("pytest", "python -m pytest tests -q"),
]

CLAIM_PROOF_CATALOG: dict[str, dict[str, str]] = {
    "tests_pass": {
        "claim": "Tests pass",
        "proof": "python -m pytest tests -q",
        "not_enough": "Previous run or narrow subset for a broad claim",
    },
    "lint_clean": {
        "claim": "Lint/typecheck clean",
        "proof": "python scripts/okf_lint.py --profile project --exclude-prefix archive/ docs",
        "not_enough": "Formatting only",
    },
    "assets_synced": {
        "claim": "Generated assets in sync",
        "proof": "python scripts/sync_assistant_trees.py --check",
        "not_enough": "Manual copy or assumed sync",
    },
    "frontmatter_ok": {
        "claim": "Agent frontmatter valid",
        "proof": "python scripts/ci/check_agent_frontmatter.py",
        "not_enough": "Spot-check of one file",
    },
    "ready_to_commit": {
        "claim": "Ready to commit",
        "proof": "git status --short && git diff --check",
        "not_enough": "Memory of earlier status",
    },
}

SECRET_PATH_PATTERNS = [
    re.compile(r"(?i)(^|/|\\)\.env(\.|$)"),
    re.compile(r"(?i)secrets\.json$"),
    re.compile(r"(?i)\.pem$"),
    re.compile(r"(?i)id_rsa"),
    re.compile(r"(?i)\.p12$"),
]


def is_secret_path(path: str | Path) -> bool:
    text = str(path).replace("\\", "/")
    return any(p.search(text) for p in SECRET_PATH_PATTERNS)


def framework_verify_commands() -> list[dict[str, str]]:
    return [{"id": cid, "command": cmd} for cid, cmd in FRAMEWORK_VERIFY_COMMANDS]
