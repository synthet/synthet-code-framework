"""Permission gate: hook -> deterministic tiers -> Jev -> audit -> approve | native fallback.

This is the only part of jev-engineering that may approve an action. ``jev_assess_risk`` and the
PreToolUse hook stay advisory (deny / ask / defer).
"""

from .gate import Operation, Verdict, decide
from .grammar import Classification, Policy, classify

__all__ = ["Classification", "Operation", "Policy", "Verdict", "classify", "decide"]
