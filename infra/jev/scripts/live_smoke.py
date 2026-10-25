"""One live System One call when a credential is already configured."""

from __future__ import annotations

import os
from pathlib import Path


def main() -> int:
    os.environ.setdefault("JEV_ENV_FILE", r"D:\Projects\jev-mcp\.env")
    os.environ.pop("JEV_MOCK", None)
    from jev_mcp.dotenv_util import load_credential_env

    load_credential_env(project_root=Path(r"D:\Projects\jev-mcp"))
    env_file = os.environ.get("JEV_ENV_FILE")
    if env_file:
        load_credential_env(project_root=Path(env_file).parent)
    if not (os.environ.get("JEV_TOKEN") or os.environ.get("TYPESAFE_API_KEY")):
        print("blocked: no credential")
        return 0
    from jev_engineering.client import DecisionClient

    try:
        result = DecisionClient().judge(
            {"task": "connectivity check"},
            {
                "up": {
                    "type": "noul",
                    "instructions": "Is this a connectivity check that contains no private data?",
                }
            },
        )
    except Exception as exc:  # noqa: BLE001 — report the class only
        print(f"blocked: {type(exc).__name__}")
        return 0
    if result.get("ok"):
        print(f"ok model={result.get('model')}")
    else:
        print(f"blocked: {result.get('fallback_reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
