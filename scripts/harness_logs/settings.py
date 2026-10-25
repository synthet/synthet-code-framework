"""Normalize global and project permission settings of every harness into one rules table.

Read-only. Credential files (auth.json, oauth_creds.json, .credentials.json, .env) are never opened,
and setting values whose key names a secret are reported as ``<redacted>``.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any, Iterator

from .common import Homes, Rule, close_sqlite, log, open_sqlite_ro, read_json
from .events import codex_persisted_grants

SECRETISH = re.compile(r"token|secret|password|api[_-]?key|credential|auth", re.I)
CURSOR_IDE_KEY = "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser"
CURSOR_IDE_FLAGS = ("useYoloMode", "yoloEnableRunEverything", "yoloDeleteFileDisabled", "yoloDotFilesDisabled",
                    "yoloOutsideWorkspaceDisabled", "yoloMcpToolsDisabled", "autoAcceptWebSearchTool",
                    "playwrightProtection", "smartAllowlistEnabled", "autoApproveModeTransitions")


def _toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.debug("cannot parse %s: %s", path, exc)
        return {}


def _value(key: str, value: Any) -> str:
    return "<redacted>" if SECRETISH.search(key) else json.dumps(value, ensure_ascii=False)[:200]


def _perm_lists(harness: str, scope: str, path: Path, perms: dict, project: str | None) -> Iterator[Rule]:
    for action in ("allow", "ask", "deny"):
        for rule in perms.get(action) or []:
            yield Rule(harness, scope, str(path), action, str(rule), project)


# --------------------------------------------------------------------------- Claude Code

def claude_rules(path: Path, scope: str, project: str | None = None) -> Iterator[Rule]:
    data = read_json(path)
    if not isinstance(data, dict):
        return
    perms = data.get("permissions") or {}
    if perms.get("defaultMode"):
        yield Rule("claude", scope, str(path), "mode", f"defaultMode={perms['defaultMode']}", project)
    yield from _perm_lists("claude", scope, path, perms, project)
    for d in perms.get("additionalDirectories") or []:
        yield Rule("claude", scope, str(path), "trust", f"additionalDirectory={d}", project)
    for event, groups in (data.get("hooks") or {}).items():
        for g in groups if isinstance(groups, list) else []:
            for h in g.get("hooks") or []:
                cmd = h.get("command", "")
                yield Rule("claude", scope, str(path), "hook", f"{event}[{g.get('matcher', '*')}]: {cmd}"[:240], project)
    auto = data.get("autoMode") or {}
    for key in ("allow", "soft_deny"):
        for rule in auto.get(key) or []:
            yield Rule("claude", scope, str(path), "allow" if key == "allow" else "ask", f"autoMode.{key}: {rule}", project)
    for key in ("enableAllProjectMcpServers", "sandbox", "skipDangerousModePermissionPrompt"):
        if key in data:
            yield Rule("claude", scope, str(path), "setting", f"{key}={_value(key, data[key])}", project)


# --------------------------------------------------------------------------- Codex

def codex_rules(path: Path, scope: str, project: str | None = None) -> Iterator[Rule]:
    data = _toml(path)
    for key in ("approval_policy", "sandbox_mode", "approvals_reviewer"):
        if key in data:
            yield Rule("codex", scope, str(path), "mode", f"{key}={data[key]}", project)
    sandbox = data.get("sandbox_workspace_write") or {}
    if "network_access" in sandbox:
        yield Rule("codex", scope, str(path), "setting", f"sandbox_workspace_write.network_access={sandbox['network_access']}", project)
    if (data.get("windows") or {}).get("sandbox"):
        yield Rule("codex", scope, str(path), "setting", f"windows.sandbox={data['windows']['sandbox']}", project)
    for proj, cfg in (data.get("projects") or {}).items():
        if isinstance(cfg, dict) and cfg.get("trust_level"):
            yield Rule("codex", scope, str(path), "trust", f"{proj}: {cfg['trust_level']}", project)
    for server, cfg in (data.get("mcp_servers") or {}).items():
        if not isinstance(cfg, dict):
            continue
        if cfg.get("default_tools_approval_mode"):
            yield Rule("codex", scope, str(path), "allow" if cfg["default_tools_approval_mode"] == "approve" else "setting",
                       f"mcp:{server}:* approval_mode={cfg['default_tools_approval_mode']}", project)
        for tool, tcfg in (cfg.get("tools") or {}).items():
            if isinstance(tcfg, dict) and tcfg.get("approval_mode"):
                yield Rule("codex", scope, str(path), "allow" if tcfg["approval_mode"] == "approve" else "setting",
                           f"mcp:{server}:{tool} approval_mode={tcfg['approval_mode']}", project)
    for app, cfg in (data.get("apps") or {}).items():
        for tool, tcfg in ((cfg or {}).get("tools") or {}).items():
            if isinstance(tcfg, dict) and tcfg.get("approval_mode"):
                yield Rule("codex", scope, str(path), "allow" if tcfg["approval_mode"] == "approve" else "setting",
                           f"app:{tool} approval_mode={tcfg['approval_mode']}", project)


def codex_hooks(path: Path, scope: str) -> Iterator[Rule]:
    data = read_json(path)
    for event, groups in ((data or {}).get("hooks") or {}).items():
        for g in groups if isinstance(groups, list) else []:
            for h in g.get("hooks") or []:
                yield Rule("codex", scope, str(path), "hook", f"{event}[{g.get('matcher', '*')}]: {h.get('command', '')}"[:240])


# --------------------------------------------------------------------------- Cursor

def cursor_cli_rules(path: Path, scope: str, project: str | None = None) -> Iterator[Rule]:
    data = read_json(path)
    if not isinstance(data, dict):
        return
    if "approvalMode" in data:
        yield Rule("cursor", scope, str(path), "mode", f"approvalMode={data['approvalMode']}", project)
    if isinstance(data.get("sandbox"), dict):
        yield Rule("cursor", scope, str(path), "setting", f"sandbox={json.dumps(data['sandbox'])}", project)
    if "autoAcceptWebSearch" in data:
        yield Rule("cursor", scope, str(path), "setting", f"autoAcceptWebSearch={data['autoAcceptWebSearch']}", project)
    yield from _perm_lists("cursor", scope, path, data.get("permissions") or {}, project)


def cursor_hook_rules(path: Path, scope: str, project: str | None = None) -> Iterator[Rule]:
    data = read_json(path)
    for event, handlers in ((data or {}).get("hooks") or {}).items():
        for h in handlers if isinstance(handlers, list) else []:
            cmd = " ".join([h.get("command", "")] + [str(a) for a in h.get("args") or []])
            yield Rule("cursor", scope, str(path), "hook", f"{event}: {cmd} failClosed={h.get('failClosed', False)}"[:240], project)


def cursor_ide_rules(homes: Homes) -> Iterator[Rule]:
    db = homes.cursor_user / "globalStorage" / "state.vscdb"
    if not db.exists():
        return
    con, tmp = open_sqlite_ro(db)
    if con is None:
        return
    try:
        row = con.execute("select value from ItemTable where key=?", (CURSOR_IDE_KEY,)).fetchone()
    except Exception as exc:  # noqa: BLE001 - one unreadable store must not stop the inventory
        log.debug("cursor IDE read failed: %s", exc)
        row = None
    finally:
        close_sqlite(con, tmp)
    if not row:
        return
    state = (json.loads(row[0]) or {}).get("composerState") or {}
    where = f"{db}#{CURSOR_IDE_KEY}"
    for flag in CURSOR_IDE_FLAGS:
        if flag in state:
            yield Rule("cursor", "ide", where, "setting", f"{flag}={state[flag]}")
    for token in state.get("yoloCommandAllowlist") or []:
        yield Rule("cursor", "ide", where, "allow", f"Shell({token})")
    for token in state.get("yoloCommandDenylist") or []:
        yield Rule("cursor", "ide", where, "deny", f"Shell({token})")
    for tool in state.get("mcpAllowedTools") or []:
        yield Rule("cursor", "ide", where, "allow", f"mcp:{tool}")
    for domain in state.get("webFetchDomainAllowlist") or []:
        yield Rule("cursor", "ide", where, "allow", f"WebFetch({domain})")


# --------------------------------------------------------------------------- Antigravity / Gemini

def antigravity_rules(homes: Homes) -> Iterator[Rule]:
    cli = homes.gemini / "antigravity-cli" / "settings.json"
    data = read_json(cli)
    if isinstance(data, dict):
        for key in ("agentMode", "toolPermission", "artifactReviewPolicy", "enableTerminalSandbox", "allowNonWorkspaceAccess"):
            if key in data:
                yield Rule("antigravity", "global", str(cli), "mode" if key == "agentMode" else "setting", f"{key}={data[key]}")
        for ws in data.get("trustedWorkspaces") or []:
            yield Rule("antigravity", "global", str(cli), "trust", f"trustedWorkspace={ws}")
        yield from _perm_lists("antigravity", "global", cli, data.get("permissions") or {}, None)
    ide = homes.gemini / "config" / "config.json"
    data = read_json(ide)
    grants = ((data or {}).get("userSettings") or {}).get("globalPermissionGrants") or {}
    yield from _perm_lists("antigravity", "ide", ide, grants, None)
    hooks = read_json(homes.gemini / "config" / "hooks.json")
    for name, events in (hooks or {}).items():
        for event, groups in (events or {}).items() if isinstance(events, dict) else []:
            for g in groups if isinstance(groups, list) else []:
                for h in g.get("hooks") or []:
                    yield Rule("antigravity", "global", str(homes.gemini / "config" / "hooks.json"), "hook",
                               f"{name}/{event}[{g.get('matcher', '*')}]: {h.get('command', '')}"[:240])
    trusted = read_json(homes.gemini / "trustedFolders.json")
    for folder, level in (trusted or {}).items():
        yield Rule("gemini", "global", str(homes.gemini / "trustedFolders.json"), "trust", f"{folder}: {level}")


# --------------------------------------------------------------------------- Grok

def grok_rules(path: Path, scope: str, project: str | None = None) -> Iterator[Rule]:
    data = _toml(path)
    ui = data.get("ui") or {}
    if "permission_mode" in ui:
        yield Rule("grok", scope, str(path), "mode", f"permission_mode={ui['permission_mode']}", project)
    perm = data.get("permission") or {}
    yield from _perm_lists("grok", scope, path, perm, project)
    for r in perm.get("rules") or []:
        if isinstance(r, dict):
            yield Rule("grok", scope, str(path), str(r.get("action", "?")),
                       f"{r.get('tool', '*')}({r.get('pattern', '*')})", project)
    for event, groups in (data.get("hooks") or {}).items():
        for g in groups if isinstance(groups, list) else []:
            for h in g.get("hooks") or []:
                yield Rule("grok", scope, str(path), "hook", f"{event}[{g.get('matcher', '*')}]: {h.get('command', '')}"[:240], project)


def grok_trust(homes: Homes) -> Iterator[Rule]:
    path = homes.grok / "trusted_folders.toml"
    for folder, cfg in (_toml(path).get("folders") or {}).items():
        yield Rule("grok", "global", str(path), "trust", f"{folder}: trusted={(cfg or {}).get('trusted')}")


# --------------------------------------------------------------------------- inventory

PROJECT_FILES = (
    (".claude/settings.json", claude_rules, "project"),
    (".claude/settings.local.json", claude_rules, "project"),
    (".claude/settings.write.example.json", claude_rules, "template"),
    (".codex/config.toml", codex_rules, "project"),
    (".cursor/cli.json", cursor_cli_rules, "project"),
    (".cursor/hooks.json", cursor_hook_rules, "project"),
    (".grok/config.toml", grok_rules, "project"),
)


def global_rules(homes: Homes) -> Iterator[Rule]:
    for name in ("settings.json", "settings.local.json"):
        p = homes.claude / name
        if p.is_file():
            yield from claude_rules(p, "global")
    yield from codex_rules(homes.codex / "config.toml", "global")
    if (homes.codex / "hooks.json").is_file():
        yield from codex_hooks(homes.codex / "hooks.json", "global")
    for grant in codex_persisted_grants(homes):
        yield Rule("codex", "global", grant["file"], grant["decision"], "prefix:" + " ".join(grant["pattern"])[:400])
    if (homes.cursor / "cli-config.json").is_file():
        yield from cursor_cli_rules(homes.cursor / "cli-config.json", "global")
    if (homes.cursor / "hooks.json").is_file():
        yield from cursor_hook_rules(homes.cursor / "hooks.json", "global")
    yield from cursor_ide_rules(homes)
    yield from antigravity_rules(homes)
    if (homes.grok / "config.toml").is_file():
        yield from grok_rules(homes.grok / "config.toml", "global")
    yield from grok_trust(homes)


def project_rules(projects_root: Path) -> Iterator[Rule]:
    try:
        projects = sorted(p for p in projects_root.iterdir() if p.is_dir())
    except OSError:
        return
    for proj in projects:
        for rel, reader, scope in PROJECT_FILES:
            path = proj / rel
            if path.is_file():
                yield from reader(path, scope, proj.name)


def all_rules(homes: Homes, projects_root: Path | None) -> list[Rule]:
    rules = list(global_rules(homes))
    if projects_root is not None:
        rules += list(project_rules(projects_root))
    return rules
