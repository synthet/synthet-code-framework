"""Centralized permission gate management CLI.

Usage:
    python -m scripts.manage_permissions plan
    python -m scripts.manage_permissions apply
    python -m scripts.manage_permissions rollback [receipt.json]
    python -m scripts.manage_permissions audit [--since 7d]
    python -m scripts.manage_permissions catalog [--since 30d] [--out file.json]
    python -m scripts.manage_permissions classify [--cwd DIR] -- CMD
    python -m scripts.manage_permissions sync-infra [--direction to-runtime|from-runtime] [--check]
    python -m scripts.manage_permissions bootstrap [--target DIR]
    python -m scripts.manage_permissions verify
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INFRA_REPO_ROOT = REPO_ROOT / "infra" / "jev"
JEV_ROOT = Path(os.environ.get("JEV_ENGINEERING_ROOT", r"D:\Projects\_agent-infra\jev"))

TRACKED_ROOT_FILES = ("pyproject.toml", "README.md", "AGENTS.md", "env.example", ".gitignore")
TRACKED_DIRS = ("config", "scripts", "instructions", "evals", "src", "tests")
IGNORE_NAMES = {"__pycache__", ".pytest_cache", ".venv", "data", "backups", ".env", "uv.lock"}
IGNORE_SUFFIXES = {".pyc", ".pyo", ".pyd"}


def _should_skip(rel_path: Path) -> bool:
    for part in rel_path.parts:
        if part in IGNORE_NAMES or part.endswith(".egg-info"):
            return True
    return rel_path.suffix.lower() in IGNORE_SUFFIXES


def _collect_tracked_files(base: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    if not base.is_dir():
        return files
    for fname in TRACKED_ROOT_FILES:
        f = base / fname
        if f.is_file():
            files[fname] = f
    for dname in TRACKED_DIRS:
        d = base / dname
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*")):
            if f.is_file():
                rel = f.relative_to(base)
                if not _should_skip(rel):
                    files[rel.as_posix()] = f
    return files


def _sha256_normalized(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def sync_infra(direction: str = "to-runtime", *, check_only: bool = False, target_root: Path | None = None) -> int:
    runtime_root = target_root or JEV_ROOT
    src_root = INFRA_REPO_ROOT if direction == "to-runtime" else runtime_root
    dst_root = runtime_root if direction == "to-runtime" else INFRA_REPO_ROOT

    src_files = _collect_tracked_files(src_root)
    dst_files = _collect_tracked_files(dst_root)
    all_keys = sorted(set(src_files) | set(dst_files))

    drifted: list[str] = []
    copied = 0
    for rel_key in all_keys:
        s_path = src_files.get(rel_key)
        d_path = dst_files.get(rel_key)
        if s_path is None:
            drifted.append(f"extra-in-dest: {rel_key}")
            if not check_only and d_path and d_path.is_file():
                d_path.unlink()
            continue
        if d_path is None or _sha256_normalized(s_path) != _sha256_normalized(d_path):
            drifted.append(f"modified: {rel_key}" if d_path else f"missing-in-dest: {rel_key}")
            if not check_only:
                out_path = dst_root / Path(rel_key)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s_path, out_path)
                copied += 1

    if check_only:
        if drifted:
            print(f"[sync-infra] Parity check FAILED ({len(drifted)} differences between {INFRA_REPO_ROOT} and {runtime_root}):")
            for item in drifted:
                print(f"  - {item}")
            return 1
        print(f"[sync-infra] Parity check OK ({len(all_keys)} tracked files identical between {INFRA_REPO_ROOT} and {runtime_root}).")
        return 0

    print(f"[sync-infra] Synced {copied} changed file(s) ({len(all_keys)} total tracked) {src_root} -> {dst_root}.")
    return 0


def bootstrap_infra(target_root: Path | None = None) -> int:
    runtime_root = target_root or JEV_ROOT
    if not INFRA_REPO_ROOT.is_dir():
        print(f"[bootstrap] Missing canonical source tree at {INFRA_REPO_ROOT}", file=sys.stderr)
        return 1
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "data").mkdir(parents=True, exist_ok=True)
    (runtime_root / "backups").mkdir(parents=True, exist_ok=True)
    rc = sync_infra("to-runtime", check_only=False, target_root=runtime_root)
    if rc != 0:
        return rc
    cmd = ["uv", "sync", "--project", str(runtime_root), "--extra", "dev"]
    print(f"[bootstrap] Running: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(runtime_root)).returncode


def _run_py(module: str, args: list[str], *, cwd: Path | None = None) -> int:
    cmd = ["uv", "run", "--project", str(JEV_ROOT), "python", "-m", module, *args]
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{REPO_ROOT}{os.pathsep}{JEV_ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"
    return subprocess.run(cmd, cwd=str(cwd or REPO_ROOT), env=env).returncode


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="manage_permissions", description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    # plan
    sub.add_parser("plan", help="Dry-run diff of global and project permission configurations")

    # apply
    sub.add_parser("apply", help="Apply permission configurations with automatic backups and receipt")

    # rollback
    rb = sub.add_parser("rollback", help="Restore permission configurations from a receipt backup")
    rb.add_argument("receipt", nargs="?", default=None, help="Path to receipt.json")

    # audit
    aud = sub.add_parser("audit", help="Show summary of audited permission decisions")
    aud.add_argument("--since", default="7d", help="Lookback window (e.g. 7d, 24h)")
    aud.add_argument("--format", choices=("md", "jsonl"), default="md")

    # catalog
    cat = sub.add_parser("catalog", help="Mine command catalog from harness transcripts")
    cat.add_argument("--since", default="30d", help="Lookback window (e.g. 30d)")
    cat.add_argument("--out", type=Path, default=None, help="Output JSON path")

    # classify
    cls_p = sub.add_parser("classify", help="Classify a command against current policy tiers")
    cls_p.add_argument("--cwd", type=Path, default=None)
    cls_p.add_argument("command", nargs=argparse.REMAINDER)

    # sync-infra
    si = sub.add_parser("sync-infra", help="Sync stateless infra/jev tree with D:\\Projects\\_agent-infra\\jev")
    si.add_argument("--direction", choices=("to-runtime", "from-runtime"), default="to-runtime")
    si.add_argument("--check", action="store_true", help="Verify SHA-256 parity without modifying files")
    si.add_argument("--target", type=Path, default=None, help="Override runtime target directory")

    # bootstrap
    bs = sub.add_parser("bootstrap", help="Bootstrap D:\\Projects\\_agent-infra\\jev from infra/jev and run uv sync")
    bs.add_argument("--target", type=Path, default=None, help="Override runtime target directory")

    # verify
    sub.add_parser("verify", help="Run full permission test suite, rule checks, and infra/jev parity check")

    args = parser.parse_args(argv)

    if args.action == "plan":
        return _run_py("jev_engineering.install_config", ["permissions", "plan"])
    if args.action == "apply":
        return _run_py("jev_engineering.install_config", ["permissions", "apply"])
    if args.action == "rollback":
        cmd_args = ["permissions", "rollback"]
        if args.receipt:
            cmd_args.append(args.receipt)
        return _run_py("jev_engineering.install_config", cmd_args)
    if args.action == "audit":
        return _run_py("jev_engineering.permission", ["audit", "--since", args.since, "--format", args.format])
    if args.action == "catalog":
        cmd_args = ["catalog", "--since", args.since]
        if args.out:
            cmd_args.extend(["--out", str(args.out)])
        return _run_py("scripts.harness_logs", cmd_args)
    if args.action == "classify":
        cmd_args = ["classify"]
        if args.cwd:
            cmd_args.extend(["--cwd", str(args.cwd)])
        cmd_args.extend(args.command)
        return _run_py("jev_engineering.permission", cmd_args)
    if args.action == "sync-infra":
        return sync_infra(args.direction, check_only=args.check, target_root=args.target)
    if args.action == "bootstrap":
        return bootstrap_infra(target_root=args.target)
    if args.action == "verify":
        parity_rc = sync_infra("to-runtime", check_only=True)
        test_paths = [
            str(JEV_ROOT / "tests" / "test_permission_gate.py"),
            str(JEV_ROOT / "tests" / "test_permission_installer.py"),
            str(REPO_ROOT / "tests" / "test_harness_logs.py"),
        ]
        cmd = ["uv", "run", "--project", str(JEV_ROOT), "pytest", *test_paths]
        test_rc = subprocess.run(cmd, cwd=str(REPO_ROOT)).returncode
        return parity_rc or test_rc

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
