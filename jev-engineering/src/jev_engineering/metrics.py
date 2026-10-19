"""Redacted decision metrics. Raw prompts and secrets are not stored."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

FIELDS = (
    "ts",
    "tool",
    "decision",
    "source",
    "reason",
    "model",
    "effort",
    "fallback_reason",
    "jev_called",
    "mock",
    "latency_ms",
    "visibility",
    "tier",
    "stepped_up",
    "needs_clarification",
)


def log_decision(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = {key: record.get(key) for key in FIELDS if key in record}
    safe.setdefault("ts", time.time())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe, sort_keys=True) + "\n")
