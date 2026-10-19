"""Deterministic permission screen. Jev cannot override a deny or ask."""

from __future__ import annotations

import re
from typing import Any

from .redact import is_sensitive, path_is_secret

DENY_PATTERNS = (
    re.compile(r"\brm\s+(-[^\s]*f[^\s]*|--force)\b", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"git\s+push\b[^\n]*--force", re.IGNORECASE),
    re.compile(r"git\s+push\b[^\n]*\s-f\b", re.IGNORECASE),
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\bdrop\s+table\b", re.IGNORECASE),
    re.compile(r"\bkubectl\s+delete\b", re.IGNORECASE),
    re.compile(r"\bterraform\s+destroy\b", re.IGNORECASE),
    re.compile(r"\bchmod\s+777\b", re.IGNORECASE),
    re.compile(r"\bmkfs(\.\w+)?\b", re.IGNORECASE),
    re.compile(r"curl[^\n]*\|\s*(ba)?sh\b", re.IGNORECASE),
    re.compile(r"wget[^\n]*\|\s*(ba)?sh\b", re.IGNORECASE),
)

ASK_PATTERNS = (
    re.compile(r"\bgit\s+push\b", re.IGNORECASE),
    re.compile(r"\bnpm\s+publish\b", re.IGNORECASE),
    re.compile(r"\balembic\s+upgrade\b", re.IGNORECASE),
    re.compile(r"\bmigrate\b", re.IGNORECASE),
    re.compile(r"\bdeploy\b", re.IGNORECASE),
    re.compile(r"\bkubectl\s+apply\b", re.IGNORECASE),
    re.compile(r"\bterraform\s+apply\b", re.IGNORECASE),
    re.compile(r"\bdocker\s+system\s+prune\b", re.IGNORECASE),
)


def screen(command: str = "", paths: list[str] | None = None, extra: str = "") -> dict[str, Any]:
    """Return deny, ask, or defer. Never allow."""
    paths = paths or []
    blob = "\n".join([command or "", extra or "", *paths])
    secret_mention = re.search(
        r"(?:^|[\s'\"`\\/(])\.env(?:\b|\.)|id_rsa|\.pem\b|(?:^|[\s'\"`\\/])secrets(?:[\\/]|\b)",
        blob,
        re.IGNORECASE,
    )
    if secret_mention or any(path_is_secret(path) for path in paths) or is_sensitive(blob):
        return _hit("deny", "sensitive_path_or_secret", blob)
    for pattern in DENY_PATTERNS:
        if pattern.search(blob):
            return _hit("deny", "destructive_command", blob)
    for pattern in ASK_PATTERNS:
        if pattern.search(blob):
            return _hit("ask", "consequential_command", blob)
    return {
        "decision": "defer",
        "source": "deterministic",
        "reason": "no_deterministic_hit",
        "jev_called": False,
        "fallback_reason": None,
        "allows_action": False,
    }


def _hit(decision: str, reason: str, blob: str) -> dict[str, Any]:
    return {
        "decision": decision,
        "source": "deterministic",
        "reason": reason,
        "jev_called": False,
        "fallback_reason": None,
        "allows_action": False,
        "sensitive": is_sensitive(blob),
    }
