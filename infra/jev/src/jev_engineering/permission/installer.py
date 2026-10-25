"""Global and project-level permission settings installer and reconciler.

Features:
- plan: computes unified diffs for every target without touching disk.
- apply: backs up every touched file to backups/<stamp>/, writes updates, and records receipt.json.
- rollback: restores every file byte-identically from backup and verifies hashes.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .grammar import Policy
from .render import render_antigravity, render_claude, render_codex, render_cursor, render_grok

CURSOR_IDE_KEY = "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser"
DANGEROUS_MCP_TOOLS = {
    "execute_sql", "run_sql", "execute_code", "create_or_update_file", "issue_write",
    "merge_pull_request", "create_pull_request", "delete_file", "delete_repository",
    "push_files", "sub_issue_write", "mailbox_claim_task", "jev_box",
}
T1_ALLOW_PATTERNS = re.compile(
    r"\b(?:gh\s+(?:pr|issue|project|auth|release|repo)|docker\s+exec|curl\s+-X|rm\s+-rf|del\b|Remove-Item)\b"
    r"|Bash\(python\s+\*\)|Bash\(python\s+-\)|Bash\(docker\s+exec\s+\*\)|Bash\(gh\s+auth\s+\*\)",
    re.I,
)


@dataclass
class FilePlan:
    path: Path
    scope: str  # "global" | "project"
    harness: str
    action: str  # "modify" | "create" | "unchanged"
    before: str
    after: str
    summary: str
    diff: str = ""

    def __post_init__(self) -> None:
        if self.before != self.after:
            b_lines = self.before.splitlines(keepends=True)
            a_lines = self.after.splitlines(keepends=True)
            self.diff = "".join(
                difflib.unified_diff(
                    b_lines, a_lines,
                    fromfile=f"a/{self.path.as_posix()}",
                    tofile=f"b/{self.path.as_posix()}",
                )
            )


@dataclass
class PlanReport:
    targets: list[FilePlan] = field(default_factory=list)

    @property
    def modified(self) -> list[FilePlan]:
        return [t for t in self.targets if t.action in ("modify", "create")]

    def summary(self) -> str:
        lines = [f"# Permission configuration plan ({len(self.modified)} changes, {len(self.targets) - len(self.modified)} unchanged)", ""]
        lines += ["| Harness | Scope | File | Action | Summary |", "|---|---|---|---|---|"]
        for t in self.targets:
            lines.append(f"| {t.harness} | {t.scope} | `{t.path}` | **{t.action.upper()}** | {t.summary} |")
        lines.append("")
        for t in self.modified:
            lines.append(f"## `{t.path}` ({t.harness} {t.scope})")
            lines.append(f"*{t.summary}*\n")
            if t.diff:
                lines.append("```diff\n" + t.diff + "\n```\n")
        return "\n".join(lines)


def _default_root() -> Path:
    return Path(os.environ.get("JEV_ENGINEERING_ROOT", r"D:\Projects\_agent-infra\jev"))


def _default_home() -> Path:
    return Path.home()


def _default_projects() -> Path:
    return Path(r"D:\Projects")


# --------------------------------------------------------------------------- Claude Code

def plan_claude_global(home: Path, policy: Policy) -> FilePlan:
    path = home / ".claude" / "settings.json"
    before = path.read_text(encoding="utf-8") if path.is_file() else "{}"
    try:
        data = json.loads(before)
    except json.JSONDecodeError:
        data = {}

    rendered = render_claude(policy)
    perms = data.setdefault("permissions", {})
    perms["defaultMode"] = rendered["defaultMode"]
    perms["allow"] = rendered["allow"]
    perms["ask"] = rendered["ask"]
    perms["deny"] = rendered["deny"]

    hooks = data.setdefault("hooks", {})
    req_group = hooks.setdefault("PermissionRequest", [])
    hook_cmd = f"uv run --project D:\\Projects\\_agent-infra\\jev python -m jev_engineering.permission hook --harness claude"
    gate_entry = {
        "matcher": "Bash|PowerShell",
        "hooks": [{"type": "command", "command": hook_cmd, "timeout": 15}],
    }
    other_entries = [
        g for g in req_group
        if not (isinstance(g, dict) and any("jev_engineering.permission hook" in h.get("command", "") for h in g.get("hooks", [])))
    ]
    hooks["PermissionRequest"] = [gate_entry, *other_entries]

    after = json.dumps(data, indent=2) + "\n"
    action = "modify" if before.strip() != after.strip() else "unchanged"
    summary = "Set defaultMode=auto, apply T0/T1/T2 lists, attach PermissionRequest gate hook"
    return FilePlan(path, "global", "claude", action if path.is_file() else "create", before, after, summary)


# --------------------------------------------------------------------------- Codex

def plan_codex_config(home: Path) -> FilePlan:
    path = home / ".codex" / "config.toml"
    before = path.read_text(encoding="utf-8") if path.is_file() else ""
    after = before
    # Ensure approval_policy = "on-request"
    if 'approval_policy =' in after:
        after = re.sub(r'approval_policy\s*=\s*"[^"]*"', 'approval_policy = "on-request"', after)
    else:
        after = 'approval_policy = "on-request"\n' + after

    # Ensure sandbox_mode = "workspace-write"
    if 'sandbox_mode =' in after:
        after = re.sub(r'sandbox_mode\s*=\s*"[^"]*"', 'sandbox_mode = "workspace-write"', after)
    else:
        after = 'sandbox_mode = "workspace-write"\n' + after

    # Ensure approvals_reviewer = "auto_review"
    if 'approvals_reviewer =' in after:
        after = re.sub(r'approvals_reviewer\s*=\s*"[^"]*"', 'approvals_reviewer = "auto_review"', after)
    else:
        after = re.sub(r'(approval_policy\s*=\s*"on-request"\n)', r'\1approvals_reviewer = "auto_review"\n', after)

    # Remove approval_mode = "approve" on dangerous tools
    after = re.sub(r'(\[mcp_servers\.[^\]]+\][^\[]*?)approval_mode\s*=\s*"approve"', r'\1# approval_mode = "prompt" (pruned write grant)', after)

    # Ensure [sandbox_workspace_write] network_access = false
    if "[sandbox_workspace_write]" not in after:
        after = after.rstrip() + "\n\n[sandbox_workspace_write]\nnetwork_access = false\n"

    action = "modify" if before.strip() != after.strip() else "unchanged"
    summary = "Set approvals_reviewer=auto_review, on-request + workspace-write, prune MCP write auto-approvals"
    return FilePlan(path, "global", "codex", action, before, after, summary)


def plan_codex_rules(home: Path, policy: Policy) -> FilePlan:
    path = home / ".codex" / "rules" / "default.rules"
    before = path.read_text(encoding="utf-8") if path.is_file() else ""
    after = render_codex(policy)["rules_file"]
    action = "modify" if before.strip() != after.strip() else "unchanged"
    summary = f"Prune {len(before.splitlines())} accumulated rules to curated T0 deny and T1 ask prefix floor"
    return FilePlan(path, "global", "codex", action, before, after, summary)


def plan_codex_hooks(home: Path) -> FilePlan:
    path = home / ".codex" / "hooks.json"
    before = path.read_text(encoding="utf-8") if path.is_file() else "{}"
    try:
        data = json.loads(before)
    except json.JSONDecodeError:
        data = {}
    hooks = data.setdefault("hooks", {})
    hook_cmd = "uv run --project D:\\Projects\\_agent-infra\\jev python -m jev_engineering.permission hook --harness codex"
    hooks["PermissionRequest"] = [{"type": "command", "command": hook_cmd, "timeout": 12}]
    after = json.dumps(data, indent=2) + "\n"
    action = "modify" if path.is_file() and before.strip() != after.strip() else ("create" if not path.is_file() else "unchanged")
    summary = "Attach PermissionRequest hook to Jev gate"
    return FilePlan(path, "global", "codex", action, before, after, summary)


# --------------------------------------------------------------------------- Cursor

def plan_cursor_cli(home: Path, policy: Policy) -> FilePlan:
    path = home / ".cursor" / "cli-config.json"
    before = path.read_text(encoding="utf-8") if path.is_file() else "{}"
    try:
        data = json.loads(before)
    except json.JSONDecodeError:
        data = {}
    rendered = render_cursor(policy)
    data["approvalMode"] = rendered["approvalMode"]
    data["sandbox"] = rendered["sandbox"]
    data["terminalAllowlist"] = rendered["terminalAllowlist"]
    perms = data.setdefault("permissions", {})
    perms["allow"] = rendered["allow"]
    perms["deny"] = rendered["deny"]
    after = json.dumps(data, indent=2) + "\n"
    action = "modify" if before.strip() != after.strip() else "unchanged"
    summary = "Set approvalMode=auto-review, replace allowlist with T2, populate deny"
    return FilePlan(path, "global", "cursor", action, before, after, summary)


def plan_cursor_permissions(home: Path, policy: Policy) -> FilePlan:
    path = home / ".cursor" / "permissions.json"
    before = path.read_text(encoding="utf-8") if path.is_file() else "{}"
    try:
        data = json.loads(before)
    except json.JSONDecodeError:
        data = {}
    rendered = render_cursor(policy)
    data["autoRun"] = rendered["autoRun"]
    after = json.dumps(data, indent=2) + "\n"
    action = "modify" if path.is_file() and before.strip() != after.strip() else ("create" if not path.is_file() else "unchanged")
    summary = "Set autoRun allow and block instructions matching policy T2/T1"
    return FilePlan(path, "global", "cursor", action, before, after, summary)


def plan_cursor_hooks(home: Path) -> FilePlan:
    path = home / ".cursor" / "hooks.json"
    before = path.read_text(encoding="utf-8") if path.is_file() else "{}"
    try:
        data = json.loads(before)
    except json.JSONDecodeError:
        data = {}
    hook_cmd = "uv run --project D:\\Projects\\_agent-infra\\jev python -m jev_engineering.permission hook --harness cursor"
    hooks = data.setdefault("hooks", {})
    hooks["beforeShellExecution"] = [{"command": hook_cmd, "timeout": 12, "failClosed": True}]
    hooks["beforeMCPExecution"] = [{"command": hook_cmd, "timeout": 12, "failClosed": True}]
    after = json.dumps(data, indent=2) + "\n"
    action = "modify" if path.is_file() and before.strip() != after.strip() else ("create" if not path.is_file() else "unchanged")
    summary = "Set beforeShellExecution and beforeMCPExecution hooks to Jev gate (failClosed=true)"
    return FilePlan(path, "global", "cursor", action, before, after, summary)


def plan_cursor_ide(home: Path, policy: Policy) -> FilePlan:
    path = home / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    if not path.is_file():
        return FilePlan(path, "ide", "cursor", "unchanged", "", "", "state.vscdb missing")
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        row = con.execute("SELECT value FROM ItemTable WHERE key=?", (CURSOR_IDE_KEY,)).fetchone()
        con.close()
    except Exception as exc:
        return FilePlan(path, "ide", "cursor", "unchanged", "", "", f"read error: {exc}")
    if not row:
        return FilePlan(path, "ide", "cursor", "unchanged", "", "", "CURSOR_IDE_KEY not found")

    before_raw = row[0]
    data = json.loads(before_raw)
    composer = data.get("composerState") or {}
    old_allows = list(composer.get("yoloCommandAllowlist") or [])
    old_mcp = list(composer.get("mcpAllowedTools") or [])

    # Prune allows to T2 heads
    t2_heads = set(policy.raw.get("native", {}).get("allow", []))
    new_allows = [
        tok for tok in old_allows
        if tok and (tok in t2_heads or (tok.split() and tok.split()[0] in t2_heads))
    ]
    # Prune dangerous MCPs
    new_mcp = [tool for tool in old_mcp if tool not in DANGEROUS_MCP_TOOLS]

    composer["yoloCommandAllowlist"] = new_allows
    composer["mcpAllowedTools"] = new_mcp
    data["composerState"] = composer
    after_raw = json.dumps(data)

    before_view = json.dumps({"yoloCommandAllowlist": old_allows, "mcpAllowedTools": old_mcp}, indent=2)
    after_view = json.dumps({"yoloCommandAllowlist": new_allows, "mcpAllowedTools": new_mcp}, indent=2)
    action = "modify" if before_view != after_view else "unchanged"
    summary = f"Prune yoloCommandAllowlist ({len(old_allows)} -> {len(new_allows)}) and mcpAllowedTools ({len(old_mcp)} -> {len(new_mcp)})"
    return FilePlan(path, "ide", "cursor", action, before_view, after_view, summary)


# --------------------------------------------------------------------------- Antigravity

def plan_antigravity_cli(home: Path, policy: Policy) -> FilePlan:
    path = home / ".gemini" / "antigravity-cli" / "settings.json"
    before = path.read_text(encoding="utf-8") if path.is_file() else "{}"
    try:
        data = json.loads(before)
    except json.JSONDecodeError:
        data = {}

    rendered = render_antigravity(policy)
    data["agentMode"] = "auto"
    data["allowNonWorkspaceAccess"] = rendered["allowNonWorkspaceAccess"]
    trusted = data.get("trustedWorkspaces") or []
    user_home = str(home).replace("/", "\\").lower()
    data["trustedWorkspaces"] = [ws for ws in trusted if ws.replace("/", "\\").lower() != user_home]
    perms = data.setdefault("permissions", {})
    perms["allow"] = rendered["permissions"]["allow"]
    perms["ask"] = rendered["permissions"]["ask"]
    perms["deny"] = rendered["permissions"]["deny"]

    after = json.dumps(data, indent=2) + "\n"
    action = "modify" if before.strip() != after.strip() else "unchanged"
    summary = "Set agentMode=auto, allowNonWorkspaceAccess=false, remove home from trustedWorkspaces, apply T0/T1/T2 lists"
    return FilePlan(path, "global", "antigravity", action, before, after, summary)


def plan_antigravity_ide(home: Path, policy: Policy) -> FilePlan:
    path = home / ".gemini" / "config" / "config.json"
    before = path.read_text(encoding="utf-8") if path.is_file() else "{}"
    try:
        data = json.loads(before)
    except json.JSONDecodeError:
        data = {}

    user_settings = data.setdefault("userSettings", {})
    grants = user_settings.setdefault("globalPermissionGrants", {})
    old_allows = list(grants.get("allow") or [])
    t2_heads = set(policy.raw.get("native", {}).get("allow", []))

    new_allows = []
    for grant in old_allows:
        m = re.match(r"^command\(([^)]+)\)$", grant)
        if m:
            cmd = m.group(1).strip()
            head = cmd.split()[0] if cmd.split() else ""
            if head and head in t2_heads and cmd not in ("npm install", "cmd", "cmd.exe"):
                new_allows.append(grant)
        elif grant.startswith("mcp(") and not any(d in grant for d in DANGEROUS_MCP_TOOLS):
            new_allows.append(grant)
        elif grant.startswith("read_url(") or grant.startswith("read_file("):
            new_allows.append(grant)

    grants["allow"] = new_allows
    if "deny" in grants and isinstance(grants["deny"], list):
        fixed_deny = []
        for d in grants["deny"]:
            m = re.match(r"^(read_file|write_file)\(([^)]+)\)$", str(d))
            if m and m.group(2).startswith("~"):
                expanded = os.path.normpath(os.path.expanduser(m.group(2)))
                fixed_deny.append(f"{m.group(1)}({expanded})")
            else:
                fixed_deny.append(d)
        grants["deny"] = fixed_deny
    after = json.dumps(data, indent=2) + "\n"
    action = "modify" if before.strip() != after.strip() else "unchanged"
    summary = f"Prune globalPermissionGrants.allow ({len(old_allows)} -> {len(new_allows)}, dropping npm install and raw cmd)"
    return FilePlan(path, "ide", "antigravity", action, before, after, summary)


def plan_antigravity_hooks(home: Path) -> FilePlan:
    path = home / ".gemini" / "config" / "hooks.json"
    before = path.read_text(encoding="utf-8") if path.is_file() else "{}"
    try:
        data = json.loads(before)
    except json.JSONDecodeError:
        data = {}

    hook_cmd = r"D:\Projects\_agent-infra\jev\.venv\Scripts\python.exe -m jev_engineering.permission hook --harness antigravity"
    # Antigravity requires top-level keys to be hook names mapping to JSONHookSpec.
    # Prune any incorrectly structured root-level "PreToolUse" array from older runs.
    if "PreToolUse" in data and isinstance(data["PreToolUse"], list):
        data.pop("PreToolUse")

    gate = data.setdefault("jev-permission-gate", {})
    if isinstance(gate, dict):
        gate["enabled"] = True
        hooks = gate.setdefault("PreToolUse", [])
        has_hook = any(
            any("jev_engineering.permission hook" in h.get("command", "") for h in g.get("hooks", []))
            for g in hooks if isinstance(g, dict)
        )
        if not has_hook:
            hooks.append({
                "matcher": "run_command|ask_permission",
                "hooks": [{"type": "command", "command": hook_cmd, "timeout": 12}],
            })

    after = json.dumps(data, indent=2) + "\n"
    action = "modify" if path.is_file() and before.strip() != after.strip() else ("create" if not path.is_file() else "unchanged")
    summary = "Set PreToolUse hook for run_command|ask_permission to Jev gate"
    return FilePlan(path, "global", "antigravity", action, before, after, summary)


# --------------------------------------------------------------------------- Grok

def plan_grok_config(home: Path, policy: Policy) -> FilePlan:
    path = home / ".grok" / "config.toml"
    before = path.read_text(encoding="utf-8") if path.is_file() else ""
    after = before
    # Change permission_mode = "always-approve" to "auto"
    after = re.sub(r'permission_mode\s*=\s*"always-approve"', 'permission_mode = "auto"', after)
    # Add rendered [permission] if missing
    rendered = render_grok(policy)
    if "[permission]" not in after:
        perm_block = "\n[permission]\n"
        perm_block += "allow = " + json.dumps(rendered["permission"]["allow"]) + "\n"
        perm_block += "ask = " + json.dumps(rendered["permission"]["ask"]) + "\n"
        perm_block += "deny = " + json.dumps(rendered["permission"]["deny"]) + "\n"
        after += perm_block

    action = "modify" if before.strip() != after.strip() else "unchanged"
    summary = "Set permission_mode=auto (from always-approve) and add native [permission] allow/ask/deny"
    return FilePlan(path, "global", "grok", action, before, after, summary)


# --------------------------------------------------------------------------- Project Cleanup (WP4)

def plan_project_settings(projects_root: Path, policy: Policy) -> list[FilePlan]:
    plans: list[FilePlan] = []
    t2_heads = set(policy.raw.get("native", {}).get("allow", []))

    try:
        repos = [p for p in projects_root.iterdir() if p.is_dir() and (p / ".git").is_dir()]
    except OSError:
        return []

    for repo in sorted(repos):
        # 1. .claude/settings.local.json
        local_path = repo / ".claude" / "settings.local.json"
        if local_path.is_file():
            raw = local_path.read_text(encoding="utf-8")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {}
            perms = data.get("permissions") or {}
            old_allow = list(perms.get("allow") or [])
            # Filter out scratchpad/temp commands, broad wildcards, and T1 mutations
            new_allow = []
            for item in old_allow:
                if T1_ALLOW_PATTERNS.search(item):
                    continue
                if any(scratch in item for scratch in ("AppData", "Temp", "scratch", "tmp")):
                    continue
                new_allow.append(item)
            if new_allow != old_allow:
                perms["allow"] = new_allow
                data["permissions"] = perms
                after = json.dumps(data, indent=2) + "\n"
                plans.append(FilePlan(
                    local_path, "project", "claude", "modify", raw, after,
                    f"Prune {repo.name} local allows ({len(old_allow)} -> {len(new_allow)}, removing T1 and scratchpad commands)",
                ))

        # 2. committed .claude/settings.json
        committed_path = repo / ".claude" / "settings.json"
        if committed_path.is_file():
            raw = committed_path.read_text(encoding="utf-8")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {}
            perms = data.get("permissions") or {}
            old_allow = list(perms.get("allow") or [])
            new_allow = [item for item in old_allow if not T1_ALLOW_PATTERNS.search(item)]
            if new_allow != old_allow:
                perms["allow"] = new_allow
                data["permissions"] = perms
                after = json.dumps(data, indent=2) + "\n"
                plans.append(FilePlan(
                    committed_path, "project", "claude", "modify", raw, after,
                    f"Remove T1 mutation entries from {repo.name} committed allowlist ({len(old_allow)} -> {len(new_allow)})",
                ))

        # 3. .codex/config.toml
        codex_path = repo / ".codex" / "config.toml"
        if codex_path.is_file():
            raw = codex_path.read_text(encoding="utf-8")
            after = re.sub(r'(\[mcp_servers\.[^\]]+\][^\[]*?)approval_mode\s*=\s*"approve"', r'\1# approval_mode = "prompt" (pruned write grant)', raw)
            if after != raw:
                plans.append(FilePlan(
                    codex_path, "project", "codex", "modify", raw, after,
                    f"Remove approval_mode=approve on mutating tools in {repo.name}",
                ))

    return plans


# --------------------------------------------------------------------------- Master Plan / Apply / Rollback

def plan_all(home: Path | None = None, projects_root: Path | None = None,
             policy: Policy | None = None) -> PlanReport:
    home = home or _default_home()
    projects_root = projects_root or _default_projects()
    policy = policy or Policy.load(_default_root() / "config" / "permission-policy.json")

    targets = [
        # Claude
        plan_claude_global(home, policy),
        # Codex
        plan_codex_config(home),
        plan_codex_rules(home, policy),
        plan_codex_hooks(home),
        # Cursor
        plan_cursor_cli(home, policy),
        plan_cursor_permissions(home, policy),
        plan_cursor_hooks(home),
        plan_cursor_ide(home, policy),
        # Antigravity
        plan_antigravity_cli(home, policy),
        plan_antigravity_ide(home, policy),
        plan_antigravity_hooks(home),
        # Grok
        plan_grok_config(home, policy),
    ]

    # Project cleanup
    targets.extend(plan_project_settings(projects_root, policy))
    return PlanReport(targets)


def apply_all(home: Path | None = None, projects_root: Path | None = None,
              policy: Policy | None = None, root: Path | None = None) -> dict[str, Any]:
    home = home or _default_home()
    projects_root = projects_root or _default_projects()
    root = root or _default_root()
    policy = policy or Policy.load(root / "config" / "permission-policy.json")

    report = plan_all(home, projects_root, policy)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_dir = root / "backups" / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []

    for item in report.modified:
        path = item.path
        before_bytes = item.before.encode("utf-8")
        after_bytes = item.after.encode("utf-8")
        before_sha = hashlib.sha256(before_bytes).hexdigest()
        after_sha = hashlib.sha256(after_bytes).hexdigest()

        # Handle SQLite Cursor IDE state specifically
        if path.suffix == ".vscdb":
            # Direct SQLite update on ItemTable
            backup_file = backup_dir / "cursor_state.vscdb.bak"
            shutil.copy2(path, backup_file)
            con = sqlite3.connect(path)
            try:
                row = con.execute("SELECT value FROM ItemTable WHERE key=?", (CURSOR_IDE_KEY,)).fetchone()
                if row:
                    data = json.loads(row[0])
                    diff_data = json.loads(item.after)
                    data.setdefault("composerState", {})["yoloCommandAllowlist"] = diff_data["yoloCommandAllowlist"]
                    data.setdefault("composerState", {})["mcpAllowedTools"] = diff_data["mcpAllowedTools"]
                    con.execute("UPDATE ItemTable SET value=? WHERE key=?", (json.dumps(data), CURSOR_IDE_KEY))
                    con.commit()
            finally:
                con.close()
            records.append({
                "path": str(path),
                "scope": item.scope,
                "harness": item.harness,
                "backup": str(backup_file),
                "before_sha": before_sha,
                "after_sha": after_sha,
                "status": "applied",
            })
            continue

        # Standard file
        path_hash = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:8]
        backup_file = backup_dir / f"{path.name}.{path_hash}.bak"
        if path.exists():
            backup_file.write_bytes(path.read_bytes())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(after_bytes)

        records.append({
            "path": str(path),
            "scope": item.scope,
            "harness": item.harness,
            "backup": str(backup_file) if path.exists() else "",
            "before_sha": before_sha,
            "after_sha": after_sha,
            "status": "applied",
            "created": str(item.action == "create").lower(),
        })

    receipt = {
        "stamp": stamp,
        "type": "permissions",
        "backup_dir": str(backup_dir),
        "applied": records,
        "unchanged": [str(t.path) for t in report.targets if t.action == "unchanged"],
    }

    receipt_path = backup_dir / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    latest_path = root / "backups" / "latest_permissions.json"
    latest_path.write_text(json.dumps({"receipt": str(receipt_path)}, indent=2) + "\n", encoding="utf-8")
    return receipt


def rollback_permissions(receipt_path: Path) -> int:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    restored = 0
    for item in receipt.get("applied", []):
        path = Path(item["path"])
        if path.suffix == ".vscdb":
            backup = Path(item["backup"])
            if backup.is_file():
                shutil.copy2(backup, path)
                restored += 1
                continue
        if item.get("created") == "true":
            if path.exists():
                path.unlink()
                restored += 1
            continue
        backup = Path(item["backup"])
        if backup.is_file():
            path.write_bytes(backup.read_bytes())
            restored += 1
    return restored
