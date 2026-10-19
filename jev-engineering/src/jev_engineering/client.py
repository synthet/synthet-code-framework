"""Jev client wrapper. Missing credentials and transport errors fall back closed."""

from __future__ import annotations

import os
from typing import Any, Protocol

from . import PINNED_MODEL
from .redact import is_sensitive


class DecisionError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Backend(Protocol):
    def system_one(
        self, *, state: Any, questions: dict[str, Any], model: str | None = None
    ) -> dict[str, Any]: ...


class MockBackend:
    """Offline answers for smoke checks. Evaluation cases use FixtureBackend."""

    def system_one(
        self, *, state: Any, questions: dict[str, Any], model: str | None = None
    ) -> dict[str, Any]:
        text = _flatten(state).lower()
        answers: dict[str, Any] = {}
        for qid, spec in questions.items():
            qtype = spec.get("type")
            if qtype == "choice":
                criteria = spec.get("criteria") or {}
                keys = list(criteria) if isinstance(criteria, dict) else list(criteria)
                choice = _mock_choice(text, keys)
                answers[qid] = {
                    "type": "choice",
                    "choice": choice,
                    "confidence": 0.2 if "low-confidence" in text else 0.91,
                    "probabilities": {},
                }
            elif qtype == "score":
                levels = list(spec.get("criteria") or [""])
                score = 0
                if any(word in text for word in ("refactor", "feature", "debug")):
                    score = min(1, len(levels) - 1)
                if "hard" in text:
                    score = len(levels) - 1
                answers[qid] = {
                    "type": "score",
                    "score": score,
                    "confidence": 0.9,
                    "legend": {},
                    "probabilities": {},
                }
            elif qtype == "noul":
                if "done" in qid:
                    noul = 0.2 if any(word in text for word in ("unclear", "fix it")) else 0.85
                else:
                    noul = 0.9 if any(word in text for word in ("destroy", "exfiltrate", "rm -rf")) else 0.1
                answers[qid] = {"type": "noul", "noul": noul}
            else:
                raise DecisionError("invalid_input")
        return {"model": f"{model or PINNED_MODEL}-mock", "usage": None, "answers": answers}


class FixtureBackend:
    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.calls = 0

    def system_one(
        self, *, state: Any, questions: dict[str, Any], model: str | None = None
    ) -> dict[str, Any]:
        self.calls += 1
        missing = [qid for qid in questions if qid not in self.answers]
        if missing:
            raise DecisionError("invalid_fixture")
        return {"model": model or PINNED_MODEL, "usage": {"input_tokens": 1, "output_tokens": 0}, "answers": self.answers}


class FailingBackend:
    def __init__(self, reason: str) -> None:
        self.reason = reason
        self.calls = 0

    def system_one(
        self, *, state: Any, questions: dict[str, Any], model: str | None = None
    ) -> dict[str, Any]:
        self.calls += 1
        if self.reason == "network":
            raise ConnectionError("network")
        if self.reason == "timeout":
            raise TimeoutError("timeout")
        raise DecisionError(self.reason)


def default_backend() -> Backend:
    if os.environ.get("JEV_MOCK") == "1":
        return MockBackend()
    try:
        from jev_mcp.client import JevClient
        from jev_mcp.dotenv_util import load_credential_env
        from pathlib import Path

        root = Path(os.environ.get("JEV_MCP_HOME", r"D:\Projects\jev-mcp"))
        load_credential_env(project_root=root)
        env_file = os.environ.get("JEV_ENV_FILE")
        if env_file:
            load_credential_env(project_root=Path(env_file).parent)
        if not (os.environ.get("JEV_TOKEN") or os.environ.get("TYPESAFE_API_KEY")):
            raise DecisionError("missing_credential")
        return JevClient(model=PINNED_MODEL)
    except DecisionError:
        raise
    except Exception as exc:  # noqa: BLE001 — surface a closed fallback, not the raw error
        message = str(exc).lower()
        if "missing_credential" in message or "api key" in message:
            raise DecisionError("missing_credential") from exc
        raise DecisionError("unavailable") from exc


class DecisionClient:
    def __init__(self, backend: Backend | None = None) -> None:
        self.backend = backend
        self.calls = 0

    def judge(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        if _state_is_sensitive(state):
            return {
                "ok": False,
                "jev_called": False,
                "fallback_reason": "sensitive_state",
                "answers": {},
                "model": None,
            }
        backend = self.backend
        if backend is None:
            try:
                backend = default_backend()
            except DecisionError as exc:
                return _failed(exc.reason, called=False)
        try:
            result = backend.system_one(state=state, questions=questions, model=PINNED_MODEL)
            self.calls += 1
        except DecisionError as exc:
            self.calls += 1
            return _failed(exc.reason, called=True)
        except TimeoutError:
            self.calls += 1
            return _failed("timeout", called=True)
        except (ConnectionError, OSError):
            self.calls += 1
            return _failed("network", called=True)
        except Exception:
            self.calls += 1
            return _failed("unavailable", called=True)
        return {
            "ok": True,
            "jev_called": True,
            "fallback_reason": None,
            "answers": result.get("answers") or {},
            "model": result.get("model") or PINNED_MODEL,
            "usage": result.get("usage"),
        }


def _failed(reason: str, *, called: bool) -> dict[str, Any]:
    return {
        "ok": False,
        "jev_called": called,
        "fallback_reason": reason,
        "answers": {},
        "model": None,
    }


def _flatten(state: Any) -> str:
    if isinstance(state, str):
        return state
    if isinstance(state, dict):
        return " ".join(_flatten(value) for value in state.values())
    if isinstance(state, list):
        return " ".join(_flatten(value) for value in state)
    return str(state)


def _state_is_sensitive(state: Any) -> bool:
    paths = []
    if isinstance(state, dict):
        raw_paths = state.get("paths") or []
        if isinstance(raw_paths, list):
            paths = [str(path) for path in raw_paths]
    return is_sensitive(_flatten(state), paths)


def _mock_choice(text: str, keys: list[str]) -> str:
    for key in keys:
        if key.replace("_", " ") in text or key in text:
            return key
    if "other" in keys:
        return "other"
    return keys[0] if keys else "other"
