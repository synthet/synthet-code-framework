"""Query-aware visibility. Secret chunks stay hidden and are not scored remotely."""

from __future__ import annotations

import re
from typing import Any

from .redact import is_sensitive
from .routing import excerpt, visibility_for

_WORDS = re.compile(r"[a-z0-9_]+", re.IGNORECASE)


def lexical_score(query: str, text: str) -> int:
    query_words = set(_WORDS.findall(query.lower()))
    if not query_words:
        return 0
    text_words = set(_WORDS.findall(text.lower()))
    overlap = len(query_words & text_words) / len(query_words)
    if overlap >= 0.6:
        return 3
    if overlap >= 0.3:
        return 2
    if overlap > 0:
        return 1
    return 0


def project_chunk(chunk: dict[str, Any], score: int, *, source: str) -> dict[str, Any]:
    level = visibility_for(score)
    text = str(chunk.get("text") or "")
    if is_sensitive(text, [str(chunk.get("source") or "")]):
        level = "hide"
        score = 0
        source = "deterministic"
    return {
        "id": chunk.get("id"),
        "source_path": chunk.get("source"),
        "provenance": chunk.get("provenance"),
        "score": score,
        "visibility": level,
        "excerpt": excerpt(text, level),
        "selector": source,
    }
