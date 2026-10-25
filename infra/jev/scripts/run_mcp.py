"""Launch the engineering MCP server."""

from __future__ import annotations

import os
from pathlib import Path

from jev_mcp.dotenv_util import load_credential_env

from jev_engineering.mcp_server import run_stdio


def main() -> None:
    root = Path(os.environ.get("JEV_ENGINEERING_ROOT", Path(__file__).resolve().parents[1]))
    os.environ.setdefault("JEV_ENGINEERING_ROOT", str(root))
    mcp_home = Path(os.environ.get("JEV_MCP_HOME", r"D:\Projects\jev-mcp"))
    load_credential_env(project_root=mcp_home)
    env_file = os.environ.get("JEV_ENV_FILE")
    if env_file:
        load_credential_env(project_root=Path(env_file).parent)
    run_stdio()


if __name__ == "__main__":
    main()
