"""Claude Code hook entrypoints. Failures defer; they never allow."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from .redact import is_sensitive

PROMPT_HINT = (
    "Jev engineering: implement the request from local files and project conventions. "
    "Call jev_route_task before a model handoff and keep that choice for the task. "
    "jev_assess_risk never permits an action. Deterministic deny rules win."
)
SECRET_HINT = (
    "Jev engineering: credential material is in this prompt. "
    "Do not read, print, or send secrets to Jev or any other external service."
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    mode = args[0] if args else "pre-tool"
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            payload = {}
    except json.JSONDecodeError:
        payload = {}
    if mode == "prompt":
        print(json.dumps(prompt_decision(payload)))
        return 0
    try:
        print(json.dumps(pre_tool_decision(payload)))
    except Exception:
        print(json.dumps(_defer("jev-engineering hook failed")))
    return 0


def prompt_decision(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = str(payload.get("prompt") or "")
    text = SECRET_HINT if is_sensitive(prompt) else PROMPT_HINT
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": text,
        }
    }


def pre_tool_decision(payload: dict[str, Any]) -> dict[str, Any]:
    from .service import Engineering

    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    command = str(tool_input.get("command") or tool_input.get("cmd") or "")
    paths = _paths(tool_input)
    extra = str(tool_input.get("description") or "")
    live = os.environ.get("JEV_HOOK_LIVE") == "1"
    result = Engineering().assess_risk(
        command=command,
        paths=paths,
        extra=extra,
        tool_name=str(payload.get("tool_name") or ""),
        live=live,
    )
    decision = result.get("decision")
    if decision not in {"deny", "ask", "defer"}:
        decision = "defer"
    reason = str(result.get("reason") or result.get("fallback_reason") or "advisory")
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": f"jev-engineering: {reason}",
        }
    }


def _defer(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "defer",
            "permissionDecisionReason": reason,
        }
    }


def _paths(tool_input: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for key in ("file_path", "path", "pattern"):
        value = tool_input.get(key)
        if isinstance(value, str):
            found.append(value)
    raw_paths = tool_input.get("paths")
    if isinstance(raw_paths, list):
        found.extend(str(path) for path in raw_paths)
    return found


if __name__ == "__main__":
    raise SystemExit(main())
