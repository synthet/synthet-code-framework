"""Orchestrates policy, Jev, state, and metrics."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .catalog import catalog, select_instructions
from .client import Backend, DecisionClient
from .context import lexical_score, project_chunk
from .metrics import log_decision
from .policy import screen
from .redact import is_sensitive
from .routing import (
    EFFORT,
    RISK_QUESTIONS,
    TASK_QUESTIONS,
    TIERS,
    rank,
    rebuild_prefers_stay,
    step_up,
)
from .state_store import StateStore

DENY_NOUL = 0.70
ASK_NOUL = 0.35


def default_root() -> Path:
    import os

    return Path(os.environ.get("JEV_ENGINEERING_ROOT", r"D:\Projects\_agent-infra\jev"))


class Engineering:
    def __init__(
        self,
        backend: Backend | None = None,
        store: StateStore | None = None,
        metrics_path: Path | None = None,
        root: Path | None = None,
    ) -> None:
        self.root = root or default_root()
        self.client = DecisionClient(backend)
        self.store = store or StateStore(self.root / "data" / "state.db")
        self.metrics_path = metrics_path or (self.root / "data" / "metrics.jsonl")

    def decide(self, task: str, *, task_id: str | None = None, has_defaults: bool = False) -> dict[str, Any]:
        started = time.perf_counter()
        task_id = self.store.create_task(task, task_id)
        judgment = self.client.judge({"task": task}, TASK_QUESTIONS)
        result = self._classification(task, judgment, has_defaults=has_defaults)
        result["task_id"] = task_id
        result["instructions"] = select_instructions(task)
        self.store.record("decide", _public(result), task_id)
        self._metric("jev_decide", result, started)
        return result

    def route_task(
        self,
        task: str,
        *,
        current_model: str = "opus",
        context_tokens: int = 0,
        output_tokens: int = 0,
        read_tokens: int = 0,
        has_defaults: bool = False,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        if is_sensitive(task):
            result = self._route_shell(current_model, reason="sensitive_content", jev_called=False)
            result["external_route"] = False
            self._metric("jev_route_task", result, started)
            return result
        judgment = self.client.judge({"task": task}, TASK_QUESTIONS)
        classified = self._classification(task, judgment, has_defaults=has_defaults)
        if not judgment["ok"]:
            result = self._route_shell(
                current_model,
                reason="fallback",
                jev_called=judgment["jev_called"],
                fallback_reason=judgment["fallback_reason"],
            )
            result["needs_clarification"] = False
            self.store.record("route", _public(result), task_id)
            self._metric("jev_route_task", result, started)
            return result
        complexity = _clamp(classified["complexity"])
        recommended = TIERS[complexity]
        confidence = float(classified["confidence"] or 0)
        stepped = False
        choice_used = confidence >= 0.6
        if not choice_used:
            recommended = step_up(recommended)
            stepped = recommended != TIERS[complexity]
        reason = "complexity"
        if (
            context_tokens > 0
            and rank(recommended) < rank(current_model)
            and rebuild_prefers_stay(
                current_model, recommended, context_tokens, output_tokens, read_tokens
            )
        ):
            recommended = current_model
            reason = "context_rebuild_cost"
            stepped = False
        result = {
            "ok": True,
            "decision": "route",
            "model": recommended,
            "effort": EFFORT[recommended],
            "reason": reason,
            "source": "jev",
            "boundary": "task",
            "stable": True,
            "stepped_up": stepped,
            "choice_used": choice_used,
            "needs_clarification": classified["needs_clarification"],
            "task_type": classified["task_type"],
            "complexity": complexity,
            "ambiguity": classified["ambiguity"],
            "jev_called": True,
            "fallback_reason": None,
            "allows_action": False,
            "external_route": True,
            "jev_model": judgment["model"],
            "first_option_accepted": False if not choice_used else classified["task_type"] == "lookup",
        }
        self.store.record("route", _public(result), task_id)
        self._metric("jev_route_task", result, started)
        return result

    def select_context(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        *,
        live: bool = True,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        safe: list[dict[str, Any]] = []
        hidden: list[dict[str, Any]] = []
        for chunk in chunks:
            if is_sensitive(str(chunk.get("text") or ""), [str(chunk.get("source") or "")]):
                hidden.append(project_chunk(chunk, 0, source="deterministic"))
            else:
                safe.append(chunk)
        jev_called = False
        fallback_reason = None
        scores: dict[str, int] = {}
        if live and safe:
            questions = {
                f"chunk_{index}": {
                    "type": "score",
                    "instructions": (
                        "How relevant is this evidence chunk to the query? "
                        "Score only this chunk."
                    ),
                    "criteria": [
                        "Irrelevant to the query",
                        "Weak context, a short pointer is enough",
                        "Useful background, keep a longer excerpt",
                        "Directly required, keep the full chunk",
                    ],
                }
                for index, _chunk in enumerate(safe[:8])
            }
            state = {
                "query": query,
                "chunks": [
                    {"id": chunk.get("id"), "source": chunk.get("source"), "text": chunk.get("text")}
                    for chunk in safe[:8]
                ],
            }
            judgment = self.client.judge(state, questions)
            jev_called = judgment["jev_called"]
            fallback_reason = judgment["fallback_reason"]
            if judgment["ok"]:
                for index, chunk in enumerate(safe[:8]):
                    answer = judgment["answers"].get(f"chunk_{index}") or {}
                    scores[str(chunk.get("id"))] = _clamp(answer.get("score", 0))
        projected = list(hidden)
        for chunk in safe:
            chunk_id = str(chunk.get("id"))
            if chunk_id in scores:
                projected.append(project_chunk(chunk, scores[chunk_id], source="jev"))
            else:
                projected.append(
                    project_chunk(chunk, lexical_score(query, str(chunk.get("text") or "")), source="lexical")
                )
        result: dict[str, Any] = {
            "ok": True,
            "decision": "context",
            "chunks": projected,
            "jev_called": jev_called,
            "fallback_reason": fallback_reason,
            "source": "jev" if scores else "lexical",
            "allows_action": False,
        }
        if len(projected) == 1:
            result["visibility"] = projected[0]["visibility"]
        self.store.record("context", _public(result), task_id)
        self._metric("jev_select_context", result, started)
        return result

    def assess_risk(
        self,
        *,
        command: str = "",
        paths: list[str] | None = None,
        extra: str = "",
        tool_name: str = "",
        live: bool = False,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        hit = screen(command, paths, extra)
        if hit["decision"] != "defer":
            hit["tool_name"] = tool_name
            self.store.record("risk", _public(hit), task_id)
            self._metric("jev_assess_risk", hit, started)
            return hit
        if not live:
            hit["tool_name"] = tool_name
            self._metric("jev_assess_risk", hit, started)
            return hit
        judgment = self.client.judge(
            {"tool_name": tool_name, "command": command, "paths": paths or [], "extra": extra},
            RISK_QUESTIONS,
        )
        if not judgment["ok"]:
            result = {
                "decision": "defer",
                "source": "fallback",
                "reason": "jev_unavailable",
                "jev_called": judgment["jev_called"],
                "fallback_reason": judgment["fallback_reason"],
                "allows_action": False,
                "tool_name": tool_name,
            }
            self._metric("jev_assess_risk", result, started)
            return result
        noul = float((judgment["answers"].get("destructive") or {}).get("noul") or 0)
        if noul >= DENY_NOUL:
            decision, reason = "deny", "jev_high_risk"
        elif noul >= ASK_NOUL:
            decision, reason = "ask", "jev_review"
        else:
            decision, reason = "defer", "jev_low_risk"
        result = {
            "decision": decision,
            "source": "jev",
            "reason": reason,
            "noul": noul,
            "jev_called": True,
            "fallback_reason": None,
            "allows_action": False,
            "tool_name": tool_name,
            "jev_model": judgment["model"],
        }
        self.store.record("risk", _public(result), task_id)
        self._metric("jev_assess_risk", result, started)
        return result

    def capabilities(self, *, include_schema: bool = False, names: list[str] | None = None) -> dict[str, Any]:
        return {"tools": catalog(include_schema=include_schema, names=names), "allows_action": False}

    def _classification(self, task: str, judgment: dict[str, Any], *, has_defaults: bool) -> dict[str, Any]:
        if not judgment["ok"]:
            return {
                "ok": False,
                "decision": "defer",
                "source": "fallback",
                "task_type": None,
                "complexity": None,
                "ambiguity": None,
                "confidence": None,
                "needs_clarification": False,
                "jev_called": judgment["jev_called"],
                "fallback_reason": judgment["fallback_reason"],
                "allows_action": False,
                "choice_used": False,
            }
        answers = judgment["answers"]
        task_type = (answers.get("task_type") or {}).get("choice")
        confidence = (answers.get("task_type") or {}).get("confidence")
        complexity = _clamp((answers.get("complexity") or {}).get("score", 0))
        ambiguity = _clamp((answers.get("ambiguity") or {}).get("score", 0))
        done = float((answers.get("spec_has_done_criteria") or {}).get("noul") or 0)
        clarify = (ambiguity >= 2 or done < 0.5) and not has_defaults
        return {
            "ok": True,
            "decision": "classify",
            "source": "jev",
            "task_type": task_type,
            "complexity": complexity,
            "ambiguity": ambiguity,
            "confidence": confidence,
            "done_criteria": done,
            "needs_clarification": clarify,
            "jev_called": True,
            "fallback_reason": None,
            "allows_action": False,
            "choice_used": confidence is not None and float(confidence) >= 0.6,
            "jev_model": judgment["model"],
        }

    def _route_shell(
        self,
        current_model: str,
        *,
        reason: str,
        jev_called: bool,
        fallback_reason: str | None = None,
    ) -> dict[str, Any]:
        model = current_model if current_model in EFFORT else "opus"
        return {
            "ok": fallback_reason is None,
            "decision": "route",
            "model": model,
            "effort": EFFORT[model],
            "reason": reason,
            "source": "fallback" if fallback_reason else "deterministic",
            "boundary": "task",
            "stable": True,
            "stepped_up": False,
            "choice_used": False,
            "needs_clarification": False,
            "jev_called": jev_called,
            "fallback_reason": fallback_reason,
            "allows_action": False,
            "external_route": False,
            "first_option_accepted": False,
        }

    def _metric(self, tool: str, result: dict[str, Any], started: float) -> None:
        log_decision(
            self.metrics_path,
            {
                "tool": tool,
                "decision": result.get("decision") or result.get("visibility"),
                "source": result.get("source"),
                "reason": result.get("reason"),
                "model": result.get("model"),
                "effort": result.get("effort"),
                "fallback_reason": result.get("fallback_reason"),
                "jev_called": result.get("jev_called"),
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "visibility": result.get("visibility"),
                "stepped_up": result.get("stepped_up"),
                "needs_clarification": result.get("needs_clarification"),
            },
        )


def _clamp(value: Any) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(0, min(3, number))


def _public(result: dict[str, Any]) -> dict[str, Any]:
    hidden = {"instructions"}
    return {key: value for key, value in result.items() if key not in hidden}
