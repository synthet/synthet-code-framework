"""Read-only parsers for agent harness transcripts, histories, databases and permission settings.

Harnesses: Claude Code, Codex, Cursor (IDE + agent transcripts), Google Antigravity (IDE + agy CLI), Grok CLI.

    python -m scripts.harness_logs probe
    python -m scripts.harness_logs events  --since 30d [--harness claude,codex] [--format json]
    python -m scripts.harness_logs settings [--projects-root D:\\Projects] [--format json]
    python -m scripts.harness_logs catalog --since 30d --out catalog.json
    python -m scripts.harness_logs report  --since 30d --out permission-audit.md

Transcript-level conversation parsing for resuming work lives in the resume-task and export-chat
skills, which must stay single-file and self-contained.
"""

from .common import HARNESSES, Event, Homes, Rule

__all__ = ["HARNESSES", "Event", "Homes", "Rule"]
