#!/usr/bin/env python3
"""Cross-PC messages through a two-way synced folder (Resilio Sync, Syncthing, OneDrive, an SMB share).

The share holds one-way folders named ``<from>-to-<to>``. Only the sender writes in its own outgoing
folders. The share's own ``AGENTS.md`` is the protocol authority, and this script reads its host table.

This script only ever ADDS files. It never deletes, moves or renames anything in the share, because
every change syncs to every PC.

Commands:
  whoami                      share root, this host, peers, incoming/outgoing folders
  status [--since DAYS]       threads per peer (topic + its -reply/-result/... follow-ups); whose turn it is
  new   --to PEER --topic T   package <T>-<date>/README.md (--note: one <T>-<date>.md). --print shows the
                              template only; --from-file DRAFT writes a checked local draft (atomic send)
  reply --to PEER --re NAME   <topic>-<kind>.md (--kind reply|result|status|ack); --body-file DRAFT = atomic reply
  watch [--once]              print NEW:/CHANGED: lines for incoming files; --once exits on the first event
  check PATH...               flag secrets and unfilled placeholders before you send
  manifest                    print SHA256SUMS for this skill copy (writes nothing)
  verify                      running + installed copies vs the share's newest v<N>/SHA256SUMS; exit 1 on drift

Share root: --root, env CROSS_PC_SHARE, ~/.config/cross-pc-mail.json {"root": "..."}, then common
Resilio/Syncthing locations. Host id: --host, env CROSS_PC_HOST, then COMPUTERNAME/HOSTNAME lowercased.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import socket
import sys
import time
from pathlib import Path

VERSION = "3"  # equals the share's private/guides/cross-pc-messages/v<N>/; bump on any change
SKILL_DIR = Path(__file__).resolve().parents[1]
RELEASES = Path("private/guides/cross-pc-messages")  # relative to the share root
# Global skill trees, as installed by the framework's agent_setup.py.
INSTALL_TREES = ("~/.claude/skills", "~/.agents/skills", "~/.gemini/config/skills", "~/.gemini/antigravity-cli/skills")
PAIR = re.compile(r"^([a-z0-9][a-z0-9-]*?)-to-([a-z0-9][a-z0-9-]*)$")
HOST_ROW = re.compile(r"^\|\s*`([a-z0-9][a-z0-9-]*)`\s*\|\s*([^|]+?)\s*\|")
TOPIC = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REPLY_KINDS = ("reply", "result", "status", "ack")
# "Replies to:" links: <from>-to-<to>/<item>, where <item> ends at /, ), `, ], whitespace or end of line.
REPLY_LINK = re.compile(r"([a-z0-9][a-z0-9-]*-to-[a-z0-9][a-z0-9-]*)/([^/)\]`\s]+)(?=[/)\]`\s]|$)")
FYI_LINE = re.compile(r"(?im)^\s*-\s*\*\*Reply needed:\*\*\s*no\b")  # a header line, not a quote in prose
PLACEHOLDERS = [
    # The exact placeholders HEADER writes, so quoting a fragment in prose is not a finding.
    ("placeholder", re.compile(r"<one sentence: why this message exists>|<what the receiver must not do")),
    ("empty-list-item", re.compile(r"^\s*(?:\d+\.|-)\s*$")),
]
CANDIDATES = ("~/Resilio Sync", "C:/Resilio Sync", "D:/Resilio Sync", "~/Sync", "~/Syncthing")
CONFIG = Path("~/.config/cross-pc-mail.json")

SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("api-key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}")),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}")),
    ("hf-token", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    ("bearer-token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}")),
    ("assignment", re.compile(
        r"(?i)\b[\w.-]*(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[\"']?(?!<)[A-Za-z0-9+/_=.-]{12,}")),
]


def norm(path: str | os.PathLike) -> Path:
    """Accept Windows, POSIX and Git Bash (/c/...) spellings."""
    s = str(path)
    m = re.match(r"^/([a-zA-Z])/(.*)$", s)
    if m and os.name == "nt":
        s = f"{m.group(1).upper()}:/{m.group(2)}"
    return Path(os.path.expanduser(s))


def is_share(root: Path) -> bool:
    return root.is_dir() and any(PAIR.match(p.name) for p in root.iterdir() if p.is_dir())


def find_root(arg: str | None) -> Path:
    tried = []
    sources = [arg, os.environ.get("CROSS_PC_SHARE")]
    cfg = norm(CONFIG)
    if cfg.is_file():
        try:
            sources.append(json.loads(cfg.read_text(encoding="utf-8")).get("root"))
        except (OSError, ValueError):
            pass
    sources += list(CANDIDATES)
    for s in sources:
        if not s:
            continue
        p = norm(s)
        tried.append(str(p))
        if is_share(p):
            return p.resolve()
    sys.exit("No share found (a folder with <from>-to-<to> subfolders). Tried: " + "; ".join(tried)
             + ". Set CROSS_PC_SHARE or pass --root.")


def hosts(root: Path) -> dict[str, str]:
    """Host table from the share's AGENTS.md, plus any host named only by a folder pair."""
    found: dict[str, str] = {}
    agents = root / "AGENTS.md"
    if agents.is_file():
        for line in agents.read_text(encoding="utf-8", errors="replace").splitlines():
            m = HOST_ROW.match(line)
            if m:
                found[m.group(1)] = m.group(2)
    for p in root.iterdir():
        m = PAIR.match(p.name) if p.is_dir() else None
        if m:
            for h in m.groups():
                found.setdefault(h, "")
    return found


def find_host(arg: str | None, known: dict[str, str]) -> str:
    raw = arg or os.environ.get("CROSS_PC_HOST") or os.environ.get("COMPUTERNAME") or socket.gethostname()
    want = raw.strip().lower()
    if want in known:
        return want
    for hid, machine in known.items():  # match the Machine column, e.g. "STRIX (desktop, ...)"
        if machine.lower().split(" (")[0].strip() == want:
            return hid
    sys.exit(f"Host {raw!r} is not in the share's host table {sorted(known)}. Pass --host or set CROSS_PC_HOST.")


def context(args) -> dict:
    root = find_root(args.root)
    known = hosts(root)
    me = find_host(args.host, known)
    pairs = [PAIR.match(p.name) for p in sorted(root.iterdir()) if p.is_dir()]
    pairs = [m for m in pairs if m]
    return {
        "root": root, "host": me, "hosts": known,
        "outgoing": {m.group(2): root / m.group(0) for m in pairs if m.group(1) == me},
        "incoming": {m.group(1): root / m.group(0) for m in pairs if m.group(2) == me},
    }


def ignored(p: Path) -> bool:
    return p.name.endswith(".!sync") or p.name == "desktop.ini" or any(part == ".sync" for part in p.parts)


def items(folder: Path) -> list[Path]:
    """Top-level messages: package folders (they have a README.md) and single notes."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir()
                  if not ignored(p) and ((p.is_dir() and (p / "README.md").is_file()) or p.suffix == ".md"))


def written(p: Path) -> float:
    """When a message was written: a package's newest file (folder mtimes move when the sync tool touches them)."""
    if p.is_dir():
        times = [f.stat().st_mtime for f in p.rglob("*") if f.is_file() and not ignored(f)]
        if times:
            return max(times)
    return p.stat().st_mtime


def stem(p: Path) -> str:
    return p.name[:-3] if p.name.endswith(".md") else p.name


# -- commands -----------------------------------------------------------------------------------

def cmd_whoami(args) -> int:
    c = context(args)
    out = {"version": VERSION, "sha256": sha256(Path(__file__)),
           "root": str(c["root"]), "host": c["host"], "machine": c["hosts"].get(c["host"], ""),
           "peers": sorted(set(c["outgoing"]) | set(c["incoming"])),
           "outgoing": {k: str(v) for k, v in c["outgoing"].items()},
           "incoming": {k: str(v) for k, v in c["incoming"].items()}}
    if args.json:
        print(json.dumps(out, indent=1))
    else:
        print(f"cross_pc_mail v{VERSION} sha256 {out['sha256'][:12]}")
        print(f"share: {out['root']}\nhost:  {out['host']} {out['machine']}")
        for k in out["peers"]:
            print(f"  {k}: out {c['outgoing'].get(k, '-')}\n  {'':{len(k)}}  in  {c['incoming'].get(k, '-')}")
    return 0


def threads(c: dict, since_days: float | None) -> list[dict]:
    """Group each peer's messages (both directions) into threads by topic prefix.

    ``<topic>-reply.md``, ``<topic>-result.md`` and any other ``<topic>-<suffix>`` belong to ``<topic>``.
    The thread's state comes from its newest message: from the peer means it's your turn.
    A message whose "Replies to:" line links ``<other-folder>/<item>`` also counts in ``<item>``'s thread,
    so one reply can answer several topics. ``- **Reply needed:** no`` on the newest message makes it ``fyi``.
    """
    cutoff = time.time() - since_days * 86400 if since_days else None
    out = []
    for peer in sorted(set(c["incoming"]) | set(c["outgoing"])):
        inbox, outbox = c["incoming"].get(peer), c["outgoing"].get(peer)
        msgs = [("in", p) for p in items(inbox)] if inbox else []
        msgs += [("out", p) for p in items(outbox)] if outbox else []
        stems = sorted({stem(p) for _, p in msgs}, key=len)

        def root_of(s: str) -> str | None:
            return next((r for r in stems if s == r or s.startswith(r + "-")), None)

        groups: dict[str, list] = {}
        for d, p in msgs:
            head = header(p)
            entry = (written(p), d, p.name, bool(FYI_LINE.search(head)))
            roots = {root_of(stem(p))}
            other = (inbox if d == "out" else outbox)
            if other is not None:
                roots |= {root_of(stem(Path(name))) for pair, name in REPLY_LINK.findall(replies_field(head))
                          if pair == other.name}
            for r in roots - {None}:
                groups.setdefault(r, []).append(entry)
        for root, ms in groups.items():
            ms.sort()
            last_t, last_d, last_name, fyi = ms[-1]
            if cutoff and last_t < cutoff:
                continue
            state = "fyi" if fyi else ("your turn" if last_d == "in" else f"waiting on {peer}")
            out.append({"peer": peer, "thread": root, "messages": len(ms), "last": last_name,
                        "last_from": peer if last_d == "in" else c["host"],
                        "modified": dt.datetime.fromtimestamp(last_t).strftime("%Y-%m-%d %H:%M"),
                        "state": state})
    return sorted(out, key=lambda t: t["modified"], reverse=True)


def replies_field(head: str) -> str:
    """The "Replies to:" line plus its indented continuation lines (a second link often wraps)."""
    out, inside = [], False
    for line in head.splitlines():
        if "replies to:" in line.lower():
            out.append(line)
            inside = True
        elif inside and line[:1].isspace() and not line.lstrip().startswith("- **"):
            out.append(line)
        else:
            inside = False
    return "\n".join(out)


def header(p: Path, lines: int = 40) -> str:
    """The first lines of a message (a package's README.md), where the header lives."""
    f = p / "README.md" if p.is_dir() else p
    try:
        with f.open(encoding="utf-8", errors="replace") as fh:
            return "".join(next(fh, "") for _ in range(lines))
    except OSError:
        return ""


def cmd_status(args) -> int:
    c = context(args)
    rows = threads(c, args.since)
    if args.json:
        print(json.dumps(rows, indent=1))
        return 0
    if not rows:
        print(f"No threads changed in the last {args.since:g} days (use --since 0 for all).")
    for r in rows:
        print(f"{r['modified']}  {r['peer']:<10} {r['state']:<18} {r['thread']}  "
              f"({r['messages']} msg, last {r['last']} from {r['last_from']})")
    return 0


def outbox(c: dict, peer: str) -> Path:
    if peer not in c["hosts"] or peer == c["host"]:
        sys.exit(f"Unknown peer {peer!r}; known: {sorted(h for h in c['hosts'] if h != c['host'])}")
    box = c["outgoing"].get(peer)
    if box is None:
        sys.exit(f"No folder {c['host']}-to-{peer} in the share. Ask the user, then add it and update AGENTS.md.")
    return box


HEADER = """# {title}

- **From:** {sender}
- **For:** {receiver}
- **Purpose:** <one sentence: why this message exists>
- **Reply in:** `{reply}`
- **Don't:** <what the receiver must not do, e.g. run scripts unreviewed, put secrets in a message folder>
"""


def drafted(path, title: bool) -> str:
    """A draft's text, refusing a blank one, or one without a `# ` title line when `title` is set.

    An unquoted shell heredoc runs the backticks in Markdown and can leave the draft empty; a blank note
    would still sync to every PC."""
    text = norm(path).read_text(encoding="utf-8")
    if not text.strip():
        sys.exit(f"{path} is empty. Write the draft with an editor or a quoted heredoc (<<'EOF'). Nothing was written to the share.")
    if title and not any(line.startswith("# ") for line in text.splitlines()):
        sys.exit(f"{path} has no '# ' title line; start from `new --print`. Nothing was written to the share.")
    return text


def cmd_new(args) -> int:
    c = context(args)
    if not TOPIC.match(args.topic):
        sys.exit("Topic must be lowercase words joined by hyphens, e.g. gpu-runner-setup.")
    box = outbox(c, args.to)
    name = f"{args.topic}-{args.date or dt.date.today().isoformat()}"
    target = box / (f"{name}.md" if args.note else name)
    if target.exists() and not args.print:
        sys.exit(f"Refusing to overwrite {target}. Pick another topic or edit your own file.")
    template = HEADER.format(title=f"{c['host'].upper()} → {args.to.upper()}: {args.title or args.topic}",
                             sender=f"agent on {c['host']}", receiver=f"agent on {args.to}",
                             reply=f"{args.to}-to-{c['host']}/{name}-reply.md")
    template += "\n## What to do\n\n1. \n\n## What not to do\n\n- \n"
    if args.print:
        print(template, end="")
        print(f"(would be written to {target})", file=sys.stderr)
        return 0
    text = template
    if args.from_file:  # atomic send: the drafted text lands in the share only if it's clean
        text = drafted(args.from_file, title=True)
        findings = scan(text.splitlines())
        if findings:
            for n, kind in findings:
                print(f"{args.from_file}:{n}: {kind}")
            sys.exit(FIX_HINT.format(n=len(findings)) + ". Nothing was written to the share.")
    if args.note:
        target.write_text(text, encoding="utf-8")
    else:
        target.mkdir()
        (target / "README.md").write_text(text, encoding="utf-8")
        target = target / "README.md"
    print(target)
    if not args.from_file:
        print("Fill in every <...> placeholder and list item, then run `check` until it prints clean.", file=sys.stderr)
    return 0


def cmd_reply(args) -> int:
    c = context(args)
    box = outbox(c, args.to)
    inbox = c["incoming"].get(args.to)
    original = inbox / args.re if inbox else None
    if original is None or not original.exists():
        sys.exit(f"{args.to}-to-{c['host']}/{args.re} not found; pass the incoming item's name as listed by status.")
    base = stem(original)
    for kind in REPLY_KINDS:  # a reply to a reply keeps the thread's topic, so names don't grow
        if base.endswith(f"-{kind}"):
            base = base[: -len(kind) - 1]
            break
    target = box / f"{base}-{args.kind}.md"
    if target.exists():
        sys.exit(f"Refusing to overwrite {target}. Edit your own file, or pick another --kind for a second message.")
    link = f"../{inbox.name}/{original.name}" + ("/README.md" if original.is_dir() else "")
    text = HEADER.format(title=f"{c['host'].upper()} → {args.to.upper()}: {args.kind} to {base}",
                         sender=f"agent on {c['host']}", receiver=f"agent on {args.to}",
                         reply=f"{args.to}-to-{c['host']}/{base}-<kind>.md")
    text = text.replace("- **Purpose:**", f"- **Replies to:** [`{inbox.name}/{original.name}`]({link})\n- **Purpose:**")
    if args.body_file:  # atomic reply: generated header + drafted body, written only if clean
        body = drafted(args.body_file, title=False)
        head = [line for line in text.splitlines() if "**Purpose:**" not in line and "**Don't:**" not in line]
        text = "\n".join(head) + "\n\n" + body
        findings = scan(text.splitlines())
        if findings:
            for n, kind in findings:
                print(f"{target.name} (draft):{n}: {kind}")
            sys.exit(FIX_HINT.format(n=len(findings)) + ". Nothing was written to the share.")
    else:
        text += "\n## Answer\n\n"
        print("Fill in Purpose, Don't and the answer, then run `check` until it prints clean.", file=sys.stderr)
    target.write_text(text, encoding="utf-8")
    print(target)
    return 0


def snapshot(folders) -> dict[str, tuple[int, int]]:
    snap = {}
    for f in folders:
        for p in f.rglob("*"):
            if p.is_file() and not ignored(p.relative_to(f.parent)):
                st = p.stat()
                snap[str(p)] = (st.st_mtime_ns, st.st_size)
    return snap


def cmd_watch(args) -> int:
    c = context(args)
    folders = list(c["incoming"].values()) + (list(c["outgoing"].values()) if args.all else [])
    if not folders:
        sys.exit("Nothing to watch: no incoming folders for this host.")
    root = c["root"]
    prev = snapshot(folders)
    while True:
        time.sleep(args.interval)
        cur = snapshot(folders)
        events = [f"NEW: {Path(p).relative_to(root).as_posix()}" for p in cur if p not in prev]
        events += [f"CHANGED: {Path(p).relative_to(root).as_posix()}" for p in cur if p in prev and cur[p] != prev[p]]
        for e in sorted(events):
            print(e, flush=True)
        prev = cur
        if events and args.once:
            return 0


def cmd_check(args) -> int:
    hits = 0
    for raw in args.paths:
        base = norm(raw)
        files = [p for p in base.rglob("*") if p.is_file()] if base.is_dir() else [base]
        for f in files:
            try:
                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError as e:
                print(f"{f}: unreadable ({e})")
                hits += 1
                continue
            for n, kind in scan(lines, f.suffix.lower() in (".md", ".txt", "")):
                print(f"{f}:{n}: {kind}")  # never echo the matched text
                hits += 1
    print("clean" if not hits else FIX_HINT.format(n=hits))
    return 1 if hits else 0


TEXT_SUFFIXES = {".md", ".py", ".json", ".txt", ".toml", ".yaml", ".yml", ".ps1", ".sh", ".js"}


def sha256(p: Path) -> str:
    """Content hash. Text files hash with CRLF normalized to LF, so a copy from a Windows checkout
    (core.autocrlf=true) and one from an LF tree of the same commit hash the same."""
    data = p.read_bytes()
    if p.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def skill_files(skill_dir: Path) -> dict[str, str]:
    """relative path -> sha256 for every file of an installed skill copy (caches excluded)."""
    return {f.relative_to(skill_dir).as_posix(): sha256(f) for f in sorted(skill_dir.rglob("*"))
            if f.is_file() and "__pycache__" not in f.parts and f.suffix not in (".pyc", ".pyo")}


def cmd_manifest(args) -> int:
    """Print SHA256SUMS for a skill copy (default: this one). Writes nothing.

    Build a release manifest from an INSTALLED copy: the installer rewrites Markdown, so a repo copy never matches.
    """
    d = norm(args.dir) if args.dir else SKILL_DIR
    if not (d / "SKILL.md").is_file():
        sys.exit(f"{d} is not a skill directory (no SKILL.md).")
    for rel, digest in skill_files(d).items():
        print(f"{digest}  {rel}")
    return 0


def installed_dirs() -> list[Path]:
    """Existing installed copies of this skill, one per global skill tree."""
    return [norm(t) / SKILL_DIR.name for t in INSTALL_TREES if (norm(t) / SKILL_DIR.name).is_dir()]


def cmd_verify(args) -> int:
    root = find_root(args.root)
    releases = root / RELEASES
    versions = sorted((int(p.name[1:]), p) for p in releases.glob("v*") if p.name[1:].isdigit()) if releases.is_dir() else []
    if not versions:
        sys.exit(f"No release manifest in {releases} (expected v<N>/SHA256SUMS).")
    n, rel_dir = versions[-1]
    if not (rel_dir / "SHA256SUMS").is_file():
        sys.exit(f"{rel_dir} has no SHA256SUMS yet.")
    want = {}
    for line in (rel_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, rel = line.split(None, 1)
            want[rel.strip()] = digest
    installed = installed_dirs()
    copies = [(str(d), d, False) for d in installed]
    if SKILL_DIR not in {d.resolve() for d in installed}:
        copies.insert(0, (f"source {SKILL_DIR}", SKILL_DIR, True))  # not installed: Markdown differs by design
    drift = False
    if VERSION != str(n):
        print(f"running script says v{VERSION}, newest release is v{n}")
        drift = True
    if not installed:
        print("no installed copy in " + ", ".join(INSTALL_TREES))
        drift = True
    for label, d, source in copies:
        have = skill_files(d)
        keys = [r for r in want if not (source and r.endswith(".md"))]
        bad = sorted(r for r in keys if have.get(r) != want[r])
        bad += sorted(r for r in have if r not in want and not (source and r.endswith(".md")))
        scope = " (non-Markdown files)" if source else ""
        print(f"{'same' if not bad else 'DRIFT'} v{n}{scope}  {label}" + ("" if not bad else "  " + ", ".join(bad)))
        drift |= bool(bad)
    return 1 if drift else 0


FIX_HINT = "{n} finding(s): fill in placeholders; move any secret to private storage and point to it instead"


def scan(lines: list[str], text_file: bool = True) -> list[tuple[int, str]]:
    found = []
    for n, line in enumerate(lines, 1):
        for kind, pat in SECRET_PATTERNS + (PLACEHOLDERS if text_file else []):
            if pat.search(line):
                found.append((n, kind))
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", help="share root (default: CROSS_PC_SHARE, config file, common locations)")
    ap.add_argument("--host", help="this host's id (default: CROSS_PC_HOST, then COMPUTERNAME)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("whoami")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("status")
    p.add_argument("--json", action="store_true")
    p.add_argument("--since", type=float, default=14.0, help="only threads changed in the last N days (0 = all)")
    p = sub.add_parser("new")
    p.add_argument("--to", required=True)
    p.add_argument("--topic", required=True)
    p.add_argument("--title")
    p.add_argument("--date", help="YYYY-MM-DD (default today)")
    p.add_argument("--note", action="store_true", help="single .md file instead of a package folder")
    p.add_argument("--print", action="store_true", help="print the header template to stdout; write nothing")
    p.add_argument("--from-file", help="use this local draft as the message; refused if `check` would flag it")
    p = sub.add_parser("reply")
    p.add_argument("--to", required=True)
    p.add_argument("--re", required=True, help="incoming item name, e.g. setup-2026-11-14 or note-2026-11-14.md")
    p.add_argument("--kind", choices=REPLY_KINDS, default="reply")
    p.add_argument("--body-file", help="local draft of the answer; the reply is written only if `check` passes")
    p = sub.add_parser("watch")
    p.add_argument("--once", action="store_true", help="exit after the first batch of events")
    p.add_argument("--all", action="store_true", help="also watch your outgoing folders")
    p.add_argument("--interval", type=float, default=20.0)
    p = sub.add_parser("check")
    p.add_argument("paths", nargs="+")
    p = sub.add_parser("manifest", help="print SHA256SUMS for a skill copy (writes nothing)")
    p.add_argument("dir", nargs="?", help="skill directory, normally an installed copy (default: this one)")
    sub.add_parser("verify", help="compare running and installed copies with the share's newest v<N>/SHA256SUMS")
    args = ap.parse_args(argv)
    return {"whoami": cmd_whoami, "status": cmd_status, "new": cmd_new, "reply": cmd_reply,
            "watch": cmd_watch, "check": cmd_check, "manifest": cmd_manifest, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
