"""Confirm the stdio server lists the engineering tools. Prints names only."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _send(proc: subprocess.Popen[bytes], message: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
    proc.stdin.flush()


def _read(proc: subprocess.Popen[bytes]) -> dict:
    assert proc.stdout is not None
    line = proc.stdout.readline()
    if not line:
        raise SystemExit("mcp handshake closed before a response")
    return json.loads(line)


def main() -> int:
    python = ROOT / ".venv" / "Scripts" / "python.exe"
    env = os.environ.copy()
    env["JEV_MOCK"] = "1"
    env["JEV_ENGINEERING_ROOT"] = str(ROOT)
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [str(python), "-m", "jev_engineering.cli", "mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=ROOT,
    )
    try:
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "jev-engineering-verify", "version": "0.1.0"},
                },
            },
        )
        init = _read(proc)
        if "error" in init:
            print("blocked: initialize failed")
            return 1
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        listed = _read(proc)
        names = sorted(tool["name"] for tool in listed["result"]["tools"])
        print(" ".join(names))
        required = {"jev_assess_risk", "jev_decide", "jev_route_task", "jev_select_context"}
        return 0 if required <= set(names) else 1
    finally:
        proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
