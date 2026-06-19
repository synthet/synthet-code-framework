#!/usr/bin/env python3
"""Detect build/test/lint commands from a project directory.

Probes common config files to infer BUILD_CMD, TEST_CMD, and LINT_CMD.
Returns only keys that were confidently detected; callers should fall back
to stack defaults for any missing keys.

Usage (standalone):
    python scripts/detect_commands.py --target . --stack python
    python scripts/detect_commands.py --target ../my-app --stack node
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _makefile_targets(target: Path) -> set[str]:
    """Return the set of top-level Makefile target names."""
    makefile = target / "Makefile"
    if not makefile.is_file():
        return set()
    targets: set[str] = set()
    for line in makefile.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"^([a-zA-Z0-9_-]+)\s*:", line)
        if m:
            targets.add(m.group(1))
    return targets


def detect_python_commands(target: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    make_targets = _makefile_targets(target)

    # BUILD_CMD
    if (target / "pyproject.toml").is_file():
        result["BUILD_CMD"] = "pip install -e ."
    elif (target / "setup.py").is_file() or (target / "setup.cfg").is_file():
        result["BUILD_CMD"] = "pip install -e ."
    elif "install" in make_targets:
        result["BUILD_CMD"] = "make install"

    # TEST_CMD
    if "test" in make_targets:
        result["TEST_CMD"] = "make test"
    elif (target / "pytest.ini").is_file() or (target / "pyproject.toml").is_file():
        pyproject = target / "pyproject.toml"
        if pyproject.is_file() and "[tool.pytest" in pyproject.read_text(encoding="utf-8", errors="ignore"):
            result["TEST_CMD"] = "python -m pytest"
        elif (target / "pytest.ini").is_file():
            result["TEST_CMD"] = "python -m pytest"
    if "TEST_CMD" not in result and (target / "tests").is_dir():
        result["TEST_CMD"] = "python -m pytest"

    # LINT_CMD
    if "lint" in make_targets:
        result["LINT_CMD"] = "make lint"
    else:
        linters: list[str] = []
        pyproject_text = ""
        pyproject = target / "pyproject.toml"
        if pyproject.is_file():
            pyproject_text = pyproject.read_text(encoding="utf-8", errors="ignore")
        if (target / "ruff.toml").is_file() or "[tool.ruff]" in pyproject_text:
            linters.append("ruff check .")
        if (target / ".flake8").is_file() or "flake8" in pyproject_text:
            linters.append("flake8 .")
        if (target / "mypy.ini").is_file() or "[tool.mypy]" in pyproject_text:
            linters.append("mypy .")
        if linters:
            result["LINT_CMD"] = " && ".join(linters)

    return result


def detect_node_commands(target: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    pkg = target / "package.json"
    if not pkg.is_file():
        return result
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return result
    scripts = data.get("scripts") or {}

    if "build" in scripts:
        result["BUILD_CMD"] = "npm run build"
    if "test" in scripts:
        result["TEST_CMD"] = "npm test"
    if "lint" in scripts:
        result["LINT_CMD"] = "npm run lint"
    elif "typecheck" in scripts or "type-check" in scripts:
        result["LINT_CMD"] = "npm run " + ("typecheck" if "typecheck" in scripts else "type-check")

    # Detect TypeScript noEmit check as lint fallback
    dev_deps = {**(data.get("devDependencies") or {}), **(data.get("dependencies") or {})}
    if "typescript" in dev_deps and "LINT_CMD" not in result:
        existing = result.get("LINT_CMD", "")
        result["LINT_CMD"] = (existing + " && " if existing else "") + "npx tsc --noEmit"

    return result


def detect_go_commands(target: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not (target / "go.mod").is_file():
        return result

    make_targets = _makefile_targets(target)

    result["BUILD_CMD"] = "make build" if "build" in make_targets else "go build ./..."
    result["TEST_CMD"] = "make test" if "test" in make_targets else "go test ./..."
    result["LINT_CMD"] = "make lint" if "lint" in make_targets else "go vet ./... && gofmt -l ."

    return result


def detect_generic_commands(target: Path) -> dict[str, str]:
    make_targets = _makefile_targets(target)
    if not make_targets:
        return {}
    result: dict[str, str] = {}
    if "build" in make_targets:
        result["BUILD_CMD"] = "make build"
    if "test" in make_targets:
        result["TEST_CMD"] = "make test"
    if "lint" in make_targets:
        result["LINT_CMD"] = "make lint"
    return result


def detect_commands(target: Path, stack: str) -> dict[str, str]:
    """Return confidently detected BUILD_CMD/TEST_CMD/LINT_CMD for the target directory."""
    detectors = {
        "python": detect_python_commands,
        "node": detect_node_commands,
        "go": detect_go_commands,
    }
    detector = detectors.get(stack, detect_generic_commands)
    result = detector(target)
    # Augment with generic Makefile detection for any missing keys
    if stack != "generic":
        generic = detect_generic_commands(target)
        for key in ("BUILD_CMD", "TEST_CMD", "LINT_CMD"):
            if key not in result and key in generic:
                result[key] = generic[key]
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Detect build/test/lint commands for a project")
    ap.add_argument("--target", type=Path, default=Path("."), help="Project directory to probe")
    ap.add_argument("--stack", default="generic", help="python|node|go|generic")
    args = ap.parse_args()

    target = args.target.resolve()
    if not target.is_dir():
        print(f"ERROR: target {target} is not a directory", file=sys.stderr)
        return 1

    detected = detect_commands(target, args.stack)
    if not detected:
        print("No commands detected (no recognized config files found).")
        return 0

    for key, value in detected.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
