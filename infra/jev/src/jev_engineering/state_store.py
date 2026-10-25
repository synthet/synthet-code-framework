"""SQLite task, chunk, decision, and advisory file-lock store."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._init()

    def close(self) -> None:
        self._db.close()

    def _init(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY,
              goal TEXT NOT NULL,
              status TEXT NOT NULL,
              created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chunks (
              id TEXT PRIMARY KEY,
              task_id TEXT,
              source TEXT NOT NULL,
              provenance TEXT NOT NULL,
              text TEXT NOT NULL,
              created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS decisions (
              id TEXT PRIMARY KEY,
              task_id TEXT,
              kind TEXT NOT NULL,
              payload TEXT NOT NULL,
              created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS locks (
              path TEXT PRIMARY KEY,
              owner TEXT NOT NULL,
              expires REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS permission_audit (
              id TEXT PRIMARY KEY,
              created REAL NOT NULL,
              harness TEXT, event TEXT, tool TEXT, session TEXT, mode TEXT,
              cwd TEXT, repo TEXT, command TEXT, command_sha256 TEXT, event_sha256 TEXT,
              tier TEXT, rule TEXT, outcome TEXT NOT NULL, reason TEXT,
              scores TEXT, jev_called INTEGER, model TEXT, latency_ms REAL, policy_sha TEXT
            );
            CREATE INDEX IF NOT EXISTS permission_audit_created ON permission_audit (created);
            """
        )
        self._db.commit()

    PERMISSION_COLUMNS = (
        "created", "harness", "event", "tool", "session", "mode", "cwd", "repo", "command", "command_sha256",
        "event_sha256", "tier", "rule", "outcome", "reason", "scores", "jev_called", "model", "latency_ms",
        "policy_sha",
    )

    def record_permission(self, row: dict[str, Any]) -> str:
        """Append one permission-gate decision. Raises on failure: the gate must not approve unaudited."""
        audit_id = uuid.uuid4().hex
        cols = self.PERMISSION_COLUMNS
        self._db.execute(
            f"INSERT INTO permission_audit (id, {', '.join(cols)}) VALUES (?, {', '.join('?' * len(cols))})",
            (audit_id, *(row.get(c) for c in cols)),
        )
        self._db.commit()
        return audit_id

    def permission_rows(self, since: float = 0.0, limit: int = 10_000) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT * FROM permission_audit WHERE created >= ? ORDER BY created DESC LIMIT ?", (since, limit)
        ).fetchall()
        return [dict(row) for row in rows]

    def create_task(self, goal: str, task_id: str | None = None) -> str:
        task_id = task_id or uuid.uuid4().hex
        self._db.execute(
            "INSERT OR REPLACE INTO tasks (id, goal, status, created) VALUES (?, ?, ?, ?)",
            (task_id, goal, "open", time.time()),
        )
        self._db.commit()
        return task_id

    def add_chunk(self, *, source: str, text: str, provenance: str, task_id: str | None = None) -> str:
        chunk_id = uuid.uuid4().hex
        self._db.execute(
            "INSERT INTO chunks (id, task_id, source, provenance, text, created) VALUES (?, ?, ?, ?, ?, ?)",
            (chunk_id, task_id, source, provenance, text, time.time()),
        )
        self._db.commit()
        return chunk_id

    def list_chunks(self, task_id: str | None = None) -> list[dict[str, Any]]:
        if task_id is None:
            rows = self._db.execute("SELECT * FROM chunks ORDER BY created").fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM chunks WHERE task_id = ? ORDER BY created", (task_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def record(self, kind: str, payload: dict[str, Any], task_id: str | None = None) -> str:
        decision_id = uuid.uuid4().hex
        self._db.execute(
            "INSERT INTO decisions (id, task_id, kind, payload, created) VALUES (?, ?, ?, ?, ?)",
            (decision_id, task_id, kind, json.dumps(payload, sort_keys=True), time.time()),
        )
        self._db.commit()
        return decision_id

    def acquire_lock(self, path: str, owner: str, ttl_seconds: float = 300) -> bool:
        now = time.time()
        self._db.execute("DELETE FROM locks WHERE expires < ?", (now,))
        row = self._db.execute("SELECT owner FROM locks WHERE path = ?", (path,)).fetchone()
        if row is not None and row["owner"] != owner:
            self._db.commit()
            return False
        self._db.execute(
            "INSERT OR REPLACE INTO locks (path, owner, expires) VALUES (?, ?, ?)",
            (path, owner, now + ttl_seconds),
        )
        self._db.commit()
        return True

    def release_lock(self, path: str, owner: str) -> None:
        self._db.execute("DELETE FROM locks WHERE path = ? AND owner = ?", (path, owner))
        self._db.commit()
