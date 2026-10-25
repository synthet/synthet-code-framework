"""Markdown permission audit: what was asked, denied and auto-accepted per harness, persisted
grants, and a review of global/project permission settings.

``risk_flag`` is a heuristic for the report only. The authoritative tier classifier is the
permission gate's grammar (``_agent-infra/jev``), which reviews the catalog separately.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Iterable

from .common import Event, Rule

RISK = (
    ("interpreter wildcard", re.compile(
        r"^(?:Bash|Shell|command)?\(?\s*(?:python3?|py|node|npx|pwsh|powershell|cmd|bash|sh|wsl|uv run|deno|ruby|perl)"
        r"(?:\.exe)?(?:\s+-(?:Command|c|e|ExecutionPolicy\s+Bypass)\b|\s+/c\b)?\s*(?::\*|\*|-\s*\)|\))\)?$", re.I)),
    ("broad tool wildcard", re.compile(r"^(?:command|Bash|Shell)\((?:git|gh|npm|docker|cargo|pnpm|agy|uv)(?::\*| \*)?\)$", re.I)),
    ("destructive", re.compile(r"\b(?:rm|rmdir|rd|del|Remove-Item|Stop-Process|taskkill|Optimize-VHD|format|reg\s+delete|"
                               r"git\s+(?:push|reset|clean|rebase|filter-branch)|docker\s+(?:rm|exec|system\s+prune|compose\s+down))\b", re.I)),
    ("remote write", re.compile(r"\bgh\s+(?:auth|repo|release|pr\s+(?:merge|create)|api)\b|merge_pull_request|create_or_update_file|"
                                r"issue_write|push_files|delete_(?:file|repository)|update_pull_request|create_issue", re.I)),
    ("install / network", re.compile(r"\b(?:pip|npm|pnpm|uv)\s+(?:install|add)\b|\bcurl\b|Invoke-WebRequest|\bwget\b|Start-Process", re.I)),
    ("database / code exec", re.compile(r"execute_sql|run_sql|execute_code|execute-query|execute-batch|browser_evaluate", re.I)),
    ("unrestricted mode", re.compile(r"(?:defaultMode|permission_mode|approvalMode|approval_policy)=(?:bypassPermissions|always-approve|unrestricted|never)\b|"
                                     r"yoloEnableRunEverything=True|useYoloMode=True|allowNonWorkspaceAccess=True|sandbox.*disabled", re.I)),
    ("broad trust", re.compile(r"trustedWorkspace=[A-Z]:\\Users\\[^\\]+$|TRUST_PARENT|AppData\\Local\\Temp", re.I)),
)
ONE_OFF = re.compile(r"scratch|AppData\\Local\\Temp|/tmp/|[0-9a-f]{8}-[0-9a-f]{4}-|\.png\"|<<|\n|.{220,}", re.I)


def risk_flag(rule: Rule) -> str | None:
    if rule.action not in ("allow", "mode", "setting", "trust"):
        return None
    for label, rx in RISK:
        if rx.search(rule.rule):
            return label
    return None


def _table(headers: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |")
    return out + [""]


def _code(text: str, limit: int = 90) -> str:
    text = text.replace("`", "'").replace("\n", " ")
    return "`" + (text if len(text) <= limit else text[: limit - 1] + "…") + "`"


def build_report(events: list[Event], rules: list[Rule], catalog: list[dict], *, since: datetime,
                 generated: datetime, projects_root: str | None) -> str:
    md = [f"# Agent permission audit — {generated:%Y-%m-%d}", "",
          f"Window: {since:%Y-%m-%d} → {generated:%Y-%m-%d %H:%M} UTC. Projects root: `{projects_root}`.",
          "Sources are local transcripts and settings files, read-only. Commands are redacted and truncated.", ""]

    # ---- events
    md += ["## 1. Tool calls by outcome", "",
           "`allowed` means the call ran; transcripts do not record whether a prompt was shown first, "
           "except where noted (`escalation_requested`, `auto_allowed`).", ""]
    by = defaultdict(Counter)
    modes = defaultdict(Counter)
    for ev in events:
        if ev.kind == "tool_call":
            by[ev.harness][ev.outcome] += 1
            modes[ev.harness][ev.mode or "?"] += 1
    outcomes = ["allowed", "auto_allowed", "escalation_requested", "user_rejected", "rule_denied", "auto_denied", "hook_blocked", "unknown"]
    md += _table(["Harness", "Total", *outcomes],
                 [[h, sum(c.values()), *[c.get(o, 0) for o in outcomes]] for h, c in sorted(by.items())])
    md += ["Permission mode in effect (tool calls per mode):", ""]
    md += _table(["Harness", "Modes"], [[h, ", ".join(f"{m} {n}" for m, n in c.most_common(6))] for h, c in sorted(modes.items())])

    denials = [ev for ev in events if ev.outcome in ("user_rejected", "rule_denied", "auto_denied", "hook_blocked")]
    md += [f"## 2. Asked and refused ({len(denials)})", ""]
    if denials:
        md += _table(["When", "Harness", "Outcome", "Tool", "Reason", "Command"],
                     [[(ev.ts or "")[:16], ev.harness, ev.outcome, ev.tool, ev.detail[:70], _code(ev.command, 80)]
                      for ev in sorted(denials, key=lambda e: e.ts or "", reverse=True)[:60]])
    esc = Counter((ev.harness, " ".join(ev.command.split()[:3]) or ev.tool)
                  for ev in events if ev.outcome == "escalation_requested")
    md += [f"## 3. Escalations requested and granted ({sum(esc.values())})", "",
           "Calls that asked to run outside the sandbox (Codex `require_escalated`, Antigravity `BypassSandbox`) and then ran.", ""]
    md += _table(["Harness", "Command start", "Count"], [[h, _code(c, 60), n] for (h, c), n in esc.most_common(25)])

    # ---- persisted grants and settings
    md += ["## 4. Persisted grants (accepted \"always allow\" and configured allow rules)", ""]
    counts = defaultdict(Counter)
    for r in rules:
        counts[(r.harness, r.scope)][r.action] += 1
    md += _table(["Harness", "Scope", "allow", "ask", "deny", "hook", "trust", "mode/setting"],
                 [[h, s, c["allow"], c["ask"], c["deny"], c["hook"], c["trust"], c["mode"] + c["setting"]]
                  for (h, s), c in sorted(counts.items())])
    one_off = Counter((r.harness, r.file) for r in rules if r.action == "allow" and ONE_OFF.search(r.rule))
    if one_off:
        md += ["One-off allow entries (exact scripts, scratch paths, heredocs) that accumulated from prompts:", ""]
        md += _table(["Harness", "File", "One-off entries"], [[h, _code(f, 100), n] for (h, f), n in one_off.most_common(15)])

    md += ["## 5. Settings review: modes and risky rules", ""]
    mode_rows = [[r.harness, r.scope, r.project or "", _code(r.rule, 80), risk_flag(r) or ""]
                 for r in rules if r.action == "mode"]
    md += _table(["Harness", "Scope", "Project", "Mode", "Flag"], mode_rows)
    flagged = [(risk_flag(r), r) for r in rules]
    flagged = [(f, r) for f, r in flagged if f and r.action != "mode"]
    by_flag = Counter((r.harness, r.scope, f) for f, r in flagged)
    md += ["Risky entries by harness, scope and kind (heuristic):", ""]
    md += _table(["Harness", "Scope", "Kind", "Count"], [[h, s, f, n] for (h, s, f), n in sorted(by_flag.items())])
    md += ["Examples (up to 4 per harness/scope/kind):", ""]
    shown = Counter()
    ex_rows = []
    for f, r in flagged:
        key = (r.harness, r.scope, f)
        if shown[key] < 4:
            shown[key] += 1
            ex_rows.append([r.harness, r.scope, r.project or "", f, _code(r.rule, 90)])
    md += _table(["Harness", "Scope", "Project", "Kind", "Rule"], ex_rows)

    # ---- project contradictions: project allow that the global ask/deny of the same harness covers
    glob_block = defaultdict(list)
    for r in rules:
        if r.scope == "global" and r.action in ("ask", "deny"):
            glob_block[r.harness].append(r.rule)
    contra = []
    for r in rules:
        if r.scope == "project" and r.action == "allow":
            core = re.sub(r"[:*\s)]+$", "", r.rule)
            for g in glob_block.get(r.harness, []):
                gcore = re.sub(r"[:*\s)]+$", "", g)
                if gcore and (core.startswith(gcore) or gcore.startswith(core)):
                    contra.append([r.harness, r.project, _code(r.rule, 60), _code(g, 60)])
                    break
    md += [f"## 6. Project allows that contradict a global ask/deny ({len(contra)})", ""]
    md += _table(["Harness", "Project", "Project allow", "Global rule"], contra[:50]) if contra else ["None found.", ""]

    # ---- catalog
    md += ["## 7. Most frequent command heads (all harnesses)", "",
           "Compound commands count once per distinct head. Use this table to review tiers.", ""]
    from .catalog import merge_harnesses
    md += _table(["Head", "Total", "Harnesses", "Outcomes"],
                 [[_code(r["head"], 50), r["total"], ", ".join(f"{h} {n}" for h, n in r["harnesses"].items()),
                   ", ".join(f"{o} {n}" for o, n in r["outcomes"].items())] for r in merge_harnesses(catalog)[:80]])
    return "\n".join(md).rstrip() + "\n"


def rules_summary(rules: Iterable[Rule]) -> dict:
    out: dict = defaultdict(Counter)
    for r in rules:
        out[f"{r.harness}/{r.scope}"][r.action] += 1
    return {k: dict(v) for k, v in out.items()}
