"""Claude Code and Cursor pre-tool hooks. Advisory output never allows."""

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

# Cursor command-hook event names. Claude uses PreToolUse / PermissionRequest.
_CURSOR_EVENTS = frozenset({
    "preToolUse",
    "postToolUse",
    "postToolUseFailure",
    "beforeShellExecution",
    "afterShellExecution",
    "beforeMCPExecution",
    "afterMCPExecution",
    "beforeReadFile",
    "afterFileEdit",
    "subagentStart",
    "subagentStop",
    "sessionStart",
    "sessionEnd",
    "beforeSubmitPrompt",
    "preCompact",
    "afterAgentResponse",
    "afterAgentThought",
    "beforeTabFileRead",
    "afterTabFileEdit",
})


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    mode = args[0] if args else "pre-tool"
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
        print(json.dumps(_failure(payload)))
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
    command = str(tool_input.get("command") or tool_input.get("cmd") or payload.get("command") or "")
    paths = _paths(tool_input)
    extra = str(tool_input.get("description") or "")
    tool_name = str(payload.get("tool_name") or ("Shell" if payload.get("command") else ""))
    live = os.environ.get("JEV_HOOK_LIVE") == "1"
    result = Engineering().assess_risk(
        command=command,
        paths=paths,
        extra=extra,
        tool_name=tool_name,
        live=live,
    )
    decision = result.get("decision")
    if decision not in {"deny", "ask", "defer"}:
        decision = "defer"
    reason = str(result.get("reason") or result.get("fallback_reason") or "advisory")
    if _cursor_event(payload):
        return _cursor_response(decision, reason)
    return _claude_response(decision, reason)


def _cursor_event(payload: dict[str, Any]) -> bool:
    name = payload.get("hook_event_name")
    if isinstance(name, str) and name in _CURSOR_EVENTS:
        return True
    if "conversation_id" in payload or "generation_id" in payload:
        return True
    return isinstance(payload.get("command"), str) and "tool_input" not in payload


def _cursor_response(decision: str, reason: str) -> dict[str, Any]:
    """Cursor rejects an empty object. Defer and ask both stay ask; never allow."""
    permission = "deny" if decision == "deny" else "ask"
    message = f"jev-engineering: {reason}"
    return {
        "permission": permission,
        "user_message": message,
        "agent_message": message if permission == "deny" else "",
    }


def _claude_response(decision: str, reason: str) -> dict[str, Any]:
    # Claude -p treats permissionDecision="defer" as pause-and-exit, not abstention.
    # Emit no decision so native permission checks still run; never emit "allow".
    if decision == "defer":
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": f"jev-engineering: {reason}",
        }
    }


def _failure(payload: dict[str, Any]) -> dict[str, Any]:
    if _cursor_event(payload):
        return _cursor_response("ask", "hook failed")
    return {}


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
