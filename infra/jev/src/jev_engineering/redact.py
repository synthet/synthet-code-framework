"""Secret detection. Matching text is not sent to Jev."""

from __future__ import annotations

import re

SECRET_PATH_RE = re.compile(
    r"(^|[\\/])(\.env(?:\.[^\\/]+)?|secrets(?:[\\/]|$)|credentials(?:\.[a-z]+)?|"
    r"id_rsa|id_ed25519|.*\.pem|.*\.p12|.*\.key)$",
    re.IGNORECASE,
)
SECRET_TEXT_RE = re.compile(
    r"("
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|api[_-]?key\s*[:=]\s*\S+"
    r"|secret[_-]?key\s*[:=]\s*\S+"
    r"|AKIA[0-9A-Z]{16}"
    r"|github_pat_[A-Za-z0-9_]+"
    r"|xox[baprs]-[A-Za-z0-9-]+"
    r"|Bearer\s+[A-Za-z0-9._\-]{12,}"
    r")",
    re.IGNORECASE,
)


def path_is_secret(path: str) -> bool:
    name = path.replace("/", "\\").rstrip("\\")
    if re.search(r"(^|[\\/])\.env(\.|$)", name, re.IGNORECASE):
        return True
    if re.search(r"(^|[\\/])secrets([\\/]|$)", name, re.IGNORECASE):
        return True
    return SECRET_PATH_RE.search(name) is not None


def text_has_secret(text: str) -> bool:
    return SECRET_TEXT_RE.search(text or "") is not None


def is_sensitive(text: str = "", paths: list[str] | None = None) -> bool:
    if text_has_secret(text):
        return True
    return any(path_is_secret(path) for path in paths or [])


def redact(text: str) -> str:
    return SECRET_TEXT_RE.sub("[redacted]", text or "")
