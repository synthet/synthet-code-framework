"""``python -m jev_engineering.permission`` entry points.

    hook --harness H            read one hook event on stdin, print the harness-native decision
    classify --cwd DIR -- CMD   show the tier of a command (no Jev call)
    classify-catalog FILE       tier table for a harness_logs catalog (policy review)
    audit [--since 7d]          summarize audited decisions
    render --harness H          native allow/ask/deny rules generated from the policy
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ..client import Backend, DecisionClient
from .adapters import CAN_APPROVE, HARNESSES, encode, fallback, normalize
from .gate import Verdict, audit_row, decide, enrolled_repos, policy_path
from .grammar import Policy, classify

HOOK_DEADLINE_SECONDS = 8.0
MAX_INPUT = 262_144


def _root() -> Path:
    return Path(os.environ.get("JEV_ENGINEERING_ROOT", r"D:\Projects\_agent-infra\jev"))


def run_hook(harness: str, raw: str, *, root: Path | None = None, policy_file: Path | None = None,
             backend: Backend | None = None) -> dict[str, Any]:
    """One decision, audited. Any failure returns the harness's native fallback."""
    from ..state_store import StateStore

    started = time.perf_counter()
    root = root or _root()
    raw_sha = hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        return fallback(harness, "invalid-json")
    policy = None
    try:
        policy = Policy.load(policy_file or policy_path())
        op = normalize(harness, event)
        verdict = decide(op, policy, DecisionClient(backend), approve_allowed=CAN_APPROVE[harness])
    except Exception as exc:  # noqa: BLE001 - errors must fall back, never approve
        op, verdict = None, Verdict(reason=f"gate-error:{type(exc).__name__}")
    try:
        store = StateStore(root / "data" / "state.db")
        try:
            store.record_permission(audit_row(op, verdict, policy, latency_ms=(time.perf_counter() - started) * 1000,
                                              raw_sha=raw_sha))
        finally:
            store.close()
    except Exception:  # noqa: BLE001 - unaudited decisions may not approve
        if verdict.outcome == "approve":
            verdict = Verdict(tier=verdict.tier, rule=verdict.rule, reason="audit-failed")
    return encode(harness, verdict, event)


def hook_main(harness: str) -> int:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raw = sys.stdin.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        out = fallback(harness, "oversized-input")
    else:
        os.environ.setdefault("JEV_TIMEOUT_SECONDS", "5")
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(run_hook, harness, raw)
        try:
            out = future.result(timeout=HOOK_DEADLINE_SECONDS)
        except Exception:  # noqa: BLE001 - timeout or crash: native fallback
            out = fallback(harness, "deadline-exceeded")
        pool.shutdown(wait=False, cancel_futures=True)
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()
    os._exit(0)  # do not wait for a hung worker thread


def _since(value: str) -> float:
    if value.endswith("d") and value[:-1].isdigit():
        return time.time() - int(value[:-1]) * 86400
    if value.endswith("h") and value[:-1].isdigit():
        return time.time() - int(value[:-1]) * 3600
    return 0.0


def classify_catalog(catalog: list[dict[str, Any]], policy: Policy, cwd: Path | None) -> list[dict[str, Any]]:
    roots = enrolled_repos(policy) + policy.scratch_dirs
    rows = []
    for row in catalog:
        head = row["head"]
        if head.startswith("tool:"):
            tier, rule = "n/a", "non-shell tool (native rules)"
        else:
            verdicts = [classify(ex, policy, cwd=cwd, allowed_roots=roots) for ex in row.get("examples") or [head]]
            worst = min(verdicts, key=lambda c: {"T0": 0, "T1": 1, "T4": 2, "T3": 3, "T2": 4}[c.tier])
            h = head
            if "cmd /c" in h:
                h = h.replace(" (inline)", " dir")
            elif "pwsh -Command" in h or "powershell -Command" in h:
                h = h.replace(" (inline)", " 'Get-ChildItem'")
            else:
                h = h.replace(" (inline)", " -c x")
            h = h.replace("<script>", "scripts/x.py")
            head_only = classify(h, policy, cwd=cwd, allowed_roots=roots)
            tier, rule = head_only.tier, head_only.rule
            if worst.tier != tier:
                rule += f" (examples: {worst.tier} {worst.rule})"
        rows.append({**row, "tier": tier, "rule": rule})
    return rows


def _md_catalog(rows: list[dict[str, Any]], top: int) -> str:
    by_tier: dict[str, list[dict[str, Any]]] = defaultdict(list)
    merged: dict[str, dict[str, Any]] = {}
    for r in rows:
        m = merged.setdefault(r["head"], {**r, "total": 0, "harnesses": Counter()})
        m["total"] += r["total"]
        m["harnesses"][r.get("harness", "?")] += r["total"]
    for m in merged.values():
        by_tier[m["tier"]].append(m)
    out = ["# Permission tiers vs. observed commands", "",
           "Each row is a command head mined from transcripts (harness_logs catalog), classified by the policy.", ""]
    totals = {t: sum(m["total"] for m in ms) for t, ms in by_tier.items()}
    out += ["| Tier | Meaning | Heads | Calls |", "|---|---|---|---|"]
    meaning = {"T0": "deny", "T1": "ask you", "T2": "approve, no Jev", "T3": "Jev decides", "T4": "unknown: native prompt",
               "n/a": "non-shell tool"}
    for t in ("T0", "T1", "T2", "T3", "T4", "n/a"):
        if t in by_tier:
            out.append(f"| {t} | {meaning[t]} | {len(by_tier[t])} | {totals[t]} |")
    for t in ("T0", "T1", "T3", "T4", "T2"):
        ms = sorted(by_tier.get(t, []), key=lambda m: -m["total"])[:top]
        if not ms:
            continue
        out += ["", f"## {t} — {meaning[t]}", "", "| Head | Calls | Harnesses | Rule |", "|---|---|---|---|"]
        for m in ms:
            hs = ", ".join(f"{h} {n}" for h, n in m["harnesses"].most_common())
            out.append(f"| `{m['head']}` | {m['total']} | {hs} | {m['rule']} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="jev_engineering.permission")
    sub = p.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hook")
    h.add_argument("--harness", choices=HARNESSES, required=True)
    c = sub.add_parser("classify")
    c.add_argument("--cwd", type=Path, default=None)
    c.add_argument("command", nargs=argparse.REMAINDER)
    cc = sub.add_parser("classify-catalog")
    cc.add_argument("catalog", type=Path)
    cc.add_argument("--cwd", type=Path, default=None)
    cc.add_argument("--top", type=int, default=40)
    cc.add_argument("--format", choices=("md", "json"), default="md")
    a = sub.add_parser("audit")
    a.add_argument("--since", default="7d")
    a.add_argument("--format", choices=("md", "jsonl"), default="md")
    r = sub.add_parser("render")
    r.add_argument("--harness", choices=HARNESSES, required=True)
    args = p.parse_args(argv)

    if args.cmd == "hook":
        return hook_main(args.harness)
    policy = Policy.load(policy_path())
    if args.cmd == "classify":
        command = " ".join(args.command[1:] if args.command[:1] == ["--"] else args.command)
        roots = enrolled_repos(policy) + policy.scratch_dirs
        print(json.dumps(classify(command, policy, cwd=args.cwd, allowed_roots=roots).as_dict(), indent=2))
        return 0
    if args.cmd == "classify-catalog":
        rows = classify_catalog(json.loads(args.catalog.read_text(encoding="utf-8")), policy,
                                args.cwd or (enrolled_repos(policy) or [None])[0])
        sys.stdout.write(json.dumps(rows, indent=1) + "\n" if args.format == "json" else _md_catalog(rows, args.top))
        return 0
    if args.cmd == "audit":
        from ..state_store import StateStore

        store = StateStore(_root() / "data" / "state.db")
        rows = store.permission_rows(_since(args.since))
        store.close()
        if args.format == "jsonl":
            sys.stdout.write("".join(json.dumps(r) + "\n" for r in rows))
            return 0
        counts = Counter((r["harness"], r["outcome"], r["tier"]) for r in rows)
        lines = [f"# Permission gate audit ({len(rows)} decisions since {args.since})", "",
                 "| Harness | Outcome | Tier | Count |", "|---|---|---|---|"]
        lines += [f"| {h} | {o} | {t} | {n} |" for (h, o, t), n in sorted(counts.items(), key=lambda kv: -kv[1])]
        lines += ["", "| When | Harness | Outcome | Tier | Rule | Reason | Command |", "|---|---|---|---|---|---|---|"]
        for row in rows[:50]:
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(row["created"]))
            cmd = (row["command"] or "").replace("|", "\\|").replace("\n", " ")[:90]
            lines.append(f"| {when} | {row['harness']} | {row['outcome']} | {row['tier']} | {row['rule']} | {row['reason']} | `{cmd}` |")
        print("\n".join(lines))
        return 0
    if args.cmd == "render":
        from .render import render

        print(json.dumps(render(args.harness, policy), indent=2))
        return 0
    return 2
