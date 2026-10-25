"""Per-harness hook wire contracts. Unknown payload shapes never auto-approve.

| harness     | event                         | approve                                   | ask / fallback                   |
|-------------|-------------------------------|-------------------------------------------|----------------------------------|
| claude      | PermissionRequest             | decision.behavior=allow                   | {} (native dialog)               |
| codex       | PermissionRequest             | decision.behavior=allow                   | {} (native approval / reviewer)  |
| cursor      | beforeShellExecution          | permission=allow                          | permission=ask                   |
| antigravity | PreToolUse run_command        | decision=allow                            | force_ask (T1) / ask (fallback)  |
| grok        | PreToolUse                    | (cannot approve: allow = "not blocked")   | ask (T1) / defer                 |
"""

from __future__ import annotations

import re
from typing import Any

from .gate import Operation, Verdict

HARNESSES = ("claude", "codex", "cursor", "antigravity", "grok")
CAN_APPROVE = {"claude": True, "codex": True, "cursor": True, "antigravity": True, "grok": False}
CODEX_KEYS = {"command", "cmd", "description", "cwd", "workdir", "timeout", "timeout_ms", "run_in_background",
              "sandbox_permissions", "justification", "with_escalated_permissions", "yield_time_ms",
              "max_output_tokens", "shell", "login", "tty"}
CLAUDE_KEYS = {"command", "description", "timeout", "run_in_background", "dangerouslyDisableSandbox"}
PWSH = re.compile(r"(?:^|[\\/])(?:pwsh|powershell)(?:\.exe)?$", re.I)


def _command(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(v, str) for v in value) and value:
        if PWSH.search(value[0]) and len(value) >= 3 and value[-2].lower() in ("-command", "-c"):
            return value[-1]
        if value[0] in ("bash", "sh", "/bin/bash", "/bin/sh") and len(value) == 3 and value[1] in ("-c", "-lc"):
            return value[2]
        return " ".join(value)
    return None


def normalize(harness: str, event: dict[str, Any]) -> Operation | None:
    if harness not in HARNESSES or not isinstance(event, dict):
        return None
    if harness in ("claude", "codex"):
        if event.get("hook_event_name") != "PermissionRequest":
            return None
        args = event.get("tool_input")
        if not isinstance(args, dict):
            return None
        allowed = CLAUDE_KEYS if harness == "claude" else CODEX_KEYS
        if set(args) - allowed:
            return None  # new grant/execution parameters need explicit support
        if args.get("dangerouslyDisableSandbox") or args.get("prefix_rule"):
            return None
        if "cwd" in args and "workdir" in args and args["cwd"] != args["workdir"]:
            return None
        command = _command(args.get("command", args.get("cmd")))
        cwd = args.get("workdir") or args.get("cwd") or event.get("cwd")
        if command is None:
            return None
        return Operation(harness, "PermissionRequest", str(event.get("tool_name") or ""), command,
                         cwd if isinstance(cwd, str) else None, event.get("permission_mode"),
                         event.get("session_id"), {"escalation": args.get("sandbox_permissions")})
    if harness == "cursor":
        if event.get("hook_event_name", "beforeShellExecution") != "beforeShellExecution":
            return None
        command, cwd = event.get("command"), event.get("cwd")
        if not isinstance(command, str):
            return None
        return Operation(harness, "beforeShellExecution", "Shell", command, cwd if isinstance(cwd, str) else None,
                         None, event.get("conversation_id"))
    if harness == "antigravity":
        call = event.get("toolCall")
        call = call if isinstance(call, dict) else {}
        name, args = call.get("name"), call.get("args")
        args = args if isinstance(args, dict) else {}
        if name != "run_command":
            return None
        command = args.get("CommandLine")
        ws_paths = event.get("workspacePaths") or []
        ws = ws_paths[0] if isinstance(ws_paths, list) and ws_paths else None
        cwd = args.get("Cwd") or event.get("cwd") or ws or event.get("workspacePath") or event.get("workspace")
        if not isinstance(command, str):
            return None
        return Operation(harness, "PreToolUse", "run_command", command, cwd if isinstance(cwd, str) else None,
                         event.get("agentMode"), event.get("conversationId"),
                         {"bypass_sandbox": bool(args.get("BypassSandbox"))})
    if harness == "grok":
        if event.get("hook_event_name", "PreToolUse") != "PreToolUse":
            return None
        args = event.get("tool_input")
        args = args if isinstance(args, dict) else {}
        command = _command(args.get("command") or args.get("cmd"))
        if command is None:
            return None
        return Operation(harness, "PreToolUse", str(event.get("tool_name") or ""), command,
                         event.get("cwd") if isinstance(event.get("cwd"), str) else None,
                         event.get("permission_mode"), event.get("session_id"))
    return None


def encode(harness: str, v: Verdict, event: dict[str, Any] | None = None) -> dict[str, Any]:
    msg = f"jev-gate: {v.reason}" + (f" ({v.tier}:{v.rule})" if v.tier else "")
    if harness in ("claude", "codex"):
        if v.outcome == "approve":
            return {"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": "allow"}}}
        if v.outcome == "deny":
            return {"hookSpecificOutput": {"hookEventName": "PermissionRequest",
                                           "decision": {"behavior": "deny", "message": msg}}}
        return {}
    if harness == "cursor":
        permission = {"approve": "allow", "deny": "deny"}.get(v.outcome, "ask")
        return {"permission": permission, "user_message": msg, "agent_message": msg if permission == "deny" else ""}
    if harness == "antigravity":
        call = (event or {}).get("toolCall")
        if isinstance(call, dict) and call.get("name") == "ask_permission":
            return {"decision": "force_ask", "reason": "explicit permission grants stay manual"}
        decision = {"approve": "allow", "deny": "deny", "ask": "force_ask"}.get(v.outcome, "ask")
        return {"decision": decision, "reason": msg}
    if harness == "grok":
        decision = {"deny": "deny", "ask": "ask"}.get(v.outcome, "defer")
        return {"decision": decision, "reason": msg} if decision != "defer" else {"decision": "defer"}
    raise ValueError(f"unknown harness {harness}")


def fallback(harness: str, reason: str) -> dict[str, Any]:
    return encode(harness, Verdict(reason=reason))
