"""Command line: ``python -m scripts.harness_logs {probe|events|grants|settings|catalog|report}``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from .catalog import build_catalog
from .common import HARNESSES, UTC, Homes, parse_time
from .events import codex_persisted_grants, iter_events, summary_by_harness
from .report import build_report, rules_summary
from .settings import all_rules

REPO_ROOT = Path(__file__).resolve().parents[2]


def _since(value: str) -> datetime:
    if value.endswith("d") and value[:-1].isdigit():
        return datetime.now(UTC) - timedelta(days=int(value[:-1]))
    parsed = parse_time(value)
    if parsed is None:
        raise argparse.ArgumentTypeError("use Nd (days) or an ISO date")
    return parsed


def _write(text: str, out: Path | None) -> None:
    if out is None:
        sys.stdout.write(text)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    sys.stdout.write(json.dumps({"written": str(out), "bytes": len(text.encode("utf-8"))}) + "\n")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="harness_logs", description=__doc__)
    p.add_argument("command", choices=("probe", "events", "grants", "settings", "catalog", "report"))
    p.add_argument("--harness", default=",".join(HARNESSES), help="comma list (default: all)")
    p.add_argument("--since", type=_since, default="30d", help="Nd or ISO date (default 30d)")
    p.add_argument("--projects-root", type=Path, default=REPO_ROOT.parent,
                   help="folder whose child repos are scanned for project settings (default: this repo's parent)")
    p.add_argument("--home", type=Path, default=None, help="profile to read instead of the current user's")
    p.add_argument("--format", choices=("jsonl", "json", "md"), default=None)
    p.add_argument("--out", type=Path, default=None, help="write to this file instead of stdout")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.WARNING, format="%(levelname)s %(message)s")
    since = a.since if isinstance(a.since, datetime) else _since(a.since)
    harnesses = [h.strip() for h in a.harness.split(",") if h.strip() in HARNESSES]
    homes = Homes.detect(a.home)

    if a.command == "probe":
        info = {name: str(getattr(homes, attr)) for name, attr in
                (("claude", "claude"), ("codex", "codex"), ("cursor", "cursor"), ("cursor-ide", "cursor_user"),
                 ("antigravity/gemini", "gemini"), ("grok", "grok"))}
        info = {k: {"path": v, "exists": Path(v).exists()} for k, v in info.items()}
        _write(json.dumps(info, indent=2) + "\n", a.out)
        return 0
    if a.command == "grants":
        grants = list(codex_persisted_grants(homes))
        _write("".join(json.dumps(g) + "\n" for g in grants), a.out)
        return 0
    if a.command == "settings":
        rules = [r for r in all_rules(homes, a.projects_root) if r.harness in harnesses or r.harness == "gemini"]
        if a.format == "json":
            _write(json.dumps(rules_summary(rules), indent=2) + "\n", a.out)
        else:
            _write("".join(json.dumps(r.as_dict(), ensure_ascii=False) + "\n" for r in rules), a.out)
        return 0

    events = list(iter_events(homes, since, harnesses))
    if a.command == "events":
        if a.format == "json":
            _write(json.dumps(summary_by_harness(events), indent=2) + "\n", a.out)
        else:
            _write("".join(json.dumps(e.as_dict(), ensure_ascii=False) + "\n" for e in events), a.out)
        return 0
    catalog = build_catalog(events)
    if a.command == "catalog":
        _write(json.dumps(catalog, indent=1, ensure_ascii=False) + "\n", a.out)
        return 0
    rules = all_rules(homes, a.projects_root)
    report = build_report(events, rules, catalog, since=since, generated=datetime.now(UTC),
                          projects_root=str(a.projects_root))
    _write(report, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
