"""Capability snippets and conditional instruction packs."""

from __future__ import annotations

from typing import Any

CAPABILITIES: dict[str, dict[str, Any]] = {
    "search": {
        "snippet": "Search repository text and filenames.",
        "schema": {"query": "string", "glob": "string?"},
    },
    "read_file": {
        "snippet": "Read a repository file by path.",
        "schema": {"path": "string"},
    },
    "edit": {
        "snippet": "Replace a unique snippet in one repository file.",
        "schema": {"path": "string", "old": "string", "new": "string"},
    },
    "test": {
        "snippet": "Run the project's focused test command.",
        "schema": {"command": "string"},
    },
    "git_diff": {
        "snippet": "Show the current unstaged diff.",
        "schema": {"path": "string?"},
    },
}

PACKS = {
    "python": "Use the repository test runner and match its Python style.",
    "rust": "Use cargo test for the package you touched.",
    "typescript": "Use the repository package manager and its lint script.",
    "secrets": "Do not read, print, or transmit credential files.",
}


def catalog(*, include_schema: bool = False, names: list[str] | None = None) -> list[dict[str, Any]]:
    selected = names or list(CAPABILITIES)
    rows = []
    for name in selected:
        item = CAPABILITIES.get(name)
        if item is None:
            continue
        row: dict[str, Any] = {"name": name, "snippet": item["snippet"]}
        if include_schema:
            row["schema"] = item["schema"]
        rows.append(row)
    return rows


def select_instructions(task: str, paths: list[str] | None = None) -> list[dict[str, str]]:
    blob = f"{task}\n" + "\n".join(paths or [])
    lowered = blob.lower()
    chosen: list[dict[str, str]] = []
    if ".py" in lowered or "python" in lowered or "pytest" in lowered:
        chosen.append({"id": "python", "text": PACKS["python"]})
    if ".rs" in lowered or "cargo" in lowered or "rust" in lowered:
        chosen.append({"id": "rust", "text": PACKS["rust"]})
    if ".ts" in lowered or ".tsx" in lowered or "typescript" in lowered:
        chosen.append({"id": "typescript", "text": PACKS["typescript"]})
    if any(token in lowered for token in (".env", "secret", "credential", ".pem")):
        chosen.append({"id": "secrets", "text": PACKS["secrets"]})
    return chosen
