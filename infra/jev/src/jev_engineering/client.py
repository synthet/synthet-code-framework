"""Jev client wrapper. Missing credentials and transport errors fall back closed."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
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


DEFAULT_SWARM_SCRIPT = r"D:\Projects\synthet-agent-swarm\agent-orchestrator\dist\index.js"
HARNESS_MAP = {
    "claude": "claude",
    "codex": "codex",
    "cursor": "cursor",
    "antigravity": "agy",
    "agy": "agy",
}


class SwarmBackend:
    """Tier-2 coin-flip adjudicator backed by synthet-agent-swarm decide CLI."""

    def __init__(
        self,
        *,
        swarm_script: str | None = None,
        timeout_sec: float = 4.5,
        harness: str | None = None,
    ) -> None:
        self.swarm_script = swarm_script or os.environ.get("JEV_SWARM_SCRIPT", DEFAULT_SWARM_SCRIPT)
        self.timeout_sec = timeout_sec
        self.harness = harness

    def system_one(
        self, *, state: Any, questions: dict[str, Any], model: str | None = None
    ) -> dict[str, Any]:
        script_path = Path(self.swarm_script)
        if not script_path.is_file():
            raise DecisionError("swarm_script_missing")
        timeout_ms = max(1000, int(self.timeout_sec * 1000))
        cmd = [
            "node",
            str(script_path),
            "decide",
            "--state",
            json.dumps(state),
            "--questions",
            json.dumps(questions),
            "--timeout-ms",
            str(timeout_ms),
        ]
        mapped_harness = HARNESS_MAP.get((self.harness or model or "").lower())
        if mapped_harness:
            cmd.extend(["--harness", mapped_harness])
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_sec + 1.0,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("swarm_timeout") from exc
        except OSError as exc:
            raise ConnectionError("swarm_exec_error") from exc

        raw_out = (proc.stdout or "").strip()
        if not raw_out:
            raise DecisionError("swarm_empty_output")
        try:
            data = json.loads(raw_out)
        except json.JSONDecodeError as exc:
            raise DecisionError("swarm_invalid_json") from exc
        if not data.get("ok") or not isinstance(data.get("answers"), dict):
            raise DecisionError(str(data.get("fallback_reason") or "swarm_failed"))
        swarm_harness = data.get("harness") or mapped_harness or "swarm"
        swarm_model = data.get("model") or "flash"
        return {
            "model": f"swarm:{swarm_harness}:{swarm_model}",
            "usage": None,
            "answers": data["answers"],
        }


def default_backend() -> Backend:
    if os.environ.get("JEV_MOCK") == "1":
        return MockBackend()
    try:
        from jev_mcp.client import JevClient
        from jev_mcp.dotenv_util import load_credential_env

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
    def __init__(self, backend: Backend | None = None, swarm_backend: Backend | None = None) -> None:
        self.backend = backend
        self.swarm_backend = swarm_backend
        self.calls = 0
        self.swarm_calls = 0

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

    def judge_coin_flip(
        self,
        state: Any,
        questions: dict[str, Any],
        *,
        harness: str | None = None,
        timeout_sec: float = 4.5,
        swarm_script: str | None = None,
    ) -> dict[str, Any]:
        if _state_is_sensitive(state):
            return _failed("sensitive_state", called=False)
        backend = self.swarm_backend
        if backend is None:
            if os.environ.get("JEV_SWARM_DISABLE") == "1":
                return _failed("swarm_disabled", called=False)
            backend = SwarmBackend(
                swarm_script=swarm_script,
                timeout_sec=timeout_sec,
                harness=harness,
            )
        try:
            result = backend.system_one(state=state, questions=questions, model=harness)
            self.swarm_calls += 1
        except DecisionError as exc:
            self.swarm_calls += 1
            return _failed(exc.reason, called=True)
        except TimeoutError:
            self.swarm_calls += 1
            return _failed("swarm_timeout", called=True)
        except (ConnectionError, OSError):
            self.swarm_calls += 1
            return _failed("swarm_network", called=True)
        except Exception:
            self.swarm_calls += 1
            return _failed("swarm_unavailable", called=True)
        return {
            "ok": True,
            "jev_called": True,
            "fallback_reason": None,
            "answers": result.get("answers") or {},
            "model": result.get("model") or "swarm:flash",
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
