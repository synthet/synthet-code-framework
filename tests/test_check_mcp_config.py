from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.check_mcp_config import validate_config  # noqa: E402


def write_config(tmp_path: Path, servers: dict) -> Path:
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps({"mcpServers": servers}, indent=2), encoding="utf-8")
    return path


def test_valid_local_config(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        {
            "demo-ro-search": {
                "side_effects": "read-only",
                "command": "fff-mcp",
                "args": [],
                "env": {"WORKSPACE_ROOT": "${workspaceFolder}"},
            }
        },
    )

    assert validate_config(path) == []


def test_valid_remote_config_disabled_with_env_auth(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        {
            "demo-rw-issues": {
                "side_effects": "write-capable",
                "approval_required": True,
                "approval_note": "Required before creating, updating, or deleting issues.",
                "enabled": False,
                "url": "https://mcp.example.com/issues",
                "headers": {"Authorization": "Bearer ${MCP_ISSUES_TOKEN}"},
            }
        },
    )

    assert validate_config(path) == []


def test_inline_secret_rejected(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        {
            "demo-ro-docs": {
                "side_effects": "read-only",
                "enabled": False,
                "url": "https://mcp.example.com/docs",
                "headers": {"Authorization": "Bearer sk-liveInlineToken1234567890"},
            }
        },
    )

    errors = validate_config(path)

    assert any("possible inline secret" in error for error in errors)


def test_missing_side_effect_classification_rejected(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        {
            "demo-rw-issues": {
                "approval_required": True,
                "approval_note": "Required before creating, updating, or deleting issues.",
                "command": "issue-mcp",
            }
        },
    )

    errors = validate_config(path)

    assert any("missing side_effects classification" in error for error in errors)
