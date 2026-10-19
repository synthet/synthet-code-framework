#!/usr/bin/env python3
"""Write Claude and Cursor plugin manifests that point at the existing trees.

``.claude/`` remains the source of truth for skills, commands, agents, and rules.
This script does not copy those files. Claude loads ``.claude`` by its default
layout. Cursor loads ``.cursor`` and sets ``mcpServers`` so a local
``.cursor/mcp.json`` is not packaged with the plugin.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "agent-workflow"
MARKETPLACE = "synthet-code-framework"
DESCRIPTION = (
    "SDLC commands, review agents, and reusable agent skills "
    "from the synthet code framework."
)
REPOSITORY = "https://github.com/synthet/synthet-code-framework"


def version(root: Path) -> str:
    return (root / "VERSION").read_text(encoding="utf-8").strip()


def documents(root: Path) -> dict[str, dict]:
    current = version(root)
    claude_plugin = {
        "name": NAME,
        "version": current,
        "description": DESCRIPTION,
        "author": {"name": "synthet"},
        "homepage": REPOSITORY,
        "repository": REPOSITORY,
        "keywords": ["sdlc", "skills", "agents"],
    }
    cursor_plugin = {
        **claude_plugin,
        "mcpServers": {},
    }
    claude_market = {
        "name": MARKETPLACE,
        "description": DESCRIPTION,
        "owner": {"name": "synthet"},
        "plugins": [
            {
                "name": NAME,
                "source": "./.claude",
                "description": DESCRIPTION,
            }
        ],
    }
    cursor_market = {
        "name": MARKETPLACE,
        "owner": {"name": "synthet"},
        "metadata": {"description": DESCRIPTION},
        "plugins": [
            {
                "name": NAME,
                "source": ".cursor",
                "description": DESCRIPTION,
            }
        ],
    }
    return {
        ".claude/.claude-plugin/plugin.json": claude_plugin,
        ".cursor/.cursor-plugin/plugin.json": cursor_plugin,
        ".claude-plugin/marketplace.json": claude_market,
        ".cursor-plugin/marketplace.json": cursor_market,
    }


def write(root: Path) -> None:
    for relative, document in documents(root).items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(document, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if manifests differ")
    args = parser.parse_args()
    expected = documents(ROOT)
    drift = False
    for relative, document in expected.items():
        path = ROOT / relative
        rendered = json.dumps(document, indent=2) + "\n"
        if args.check:
            actual = path.read_text(encoding="utf-8") if path.is_file() else ""
            if actual != rendered:
                print(f"differs: {relative}")
                drift = True
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered, encoding="utf-8", newline="\n")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
