"""SQLite case store and transaction boundary (REQ-INV-004).

``policy`` owns the ``cases``, ``policy_snapshots`` and ``commits`` tables; the audit and
escalation tables are created by their repositories' ``ensure_schema`` (transaction-
enlisted, never independent commits). ``transaction`` opens a fresh connection with
``BEGIN IMMEDIATE`` and rolls back on any exception so a partial write is impossible.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from ..audit.repository import AuditRepository
from ..escalation.repository import QueueRepository
from .snapshot import PolicySnapshot, SnapshotStore

_CASES_DDL = """
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL,
    status TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    policy_snapshot_id TEXT NOT NULL,
    policy_snapshot_digest TEXT NOT NULL,
    content_text TEXT,
    advisory_verdict TEXT,
    advisory_severity TEXT,
    advisory_model_id TEXT,
    advisory_model_version TEXT,
    analysis_failure_code TEXT,
    updated_at TEXT NOT NULL
)
"""

_SNAPSHOTS_DDL = """
CREATE TABLE IF NOT EXISTS policy_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL,
    digest TEXT NOT NULL,
    document_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 0,
    activated_at TEXT NOT NULL
)
"""

_SNAPSHOTS_INDEX_DDL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS one_active_snapshot "
    "ON policy_snapshots(active) WHERE active = 1"
)

_COMMITS_DDL = """
CREATE TABLE IF NOT EXISTS commits (
    replay_actor TEXT NOT NULL,
    replay_key TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    review_request_hash TEXT,
    decision_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    result_json TEXT NOT NULL,
    PRIMARY KEY (replay_actor, replay_key)
)
"""


def _migrate_commits_schema(conn: sqlite3.Connection) -> None:
    """Idempotent column additions for databases created before the ADR-002
    review-transition fix round.

    ``review_request_hash`` carries the immutable review-request identity bound to
    review commits; evaluate-path rows keep NULL.
    """
    columns = {row[1] for row in conn.execute("PRAGMA table_info(commits)").fetchall()}
    if "review_request_hash" not in columns:
        conn.execute("ALTER TABLE commits ADD COLUMN review_request_hash TEXT")


class SqliteStore:
    """File-backed SQLite store owning the policy tables and the transaction boundary."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)

    @property
    def db_path(self) -> str:
        return self._db_path

    def initialize(self) -> None:
        """Create policy, audit and escalation tables (idempotent)."""
        with self.transaction() as conn:
            conn.execute(_CASES_DDL)
            conn.execute(_SNAPSHOTS_DDL)
            conn.execute(_SNAPSHOTS_INDEX_DDL)
            conn.execute(_COMMITS_DDL)
            _migrate_commits_schema(conn)
            AuditRepository.ensure_schema(conn)
            QueueRepository.ensure_schema(conn)

    @contextmanager
    def read_connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a read-only-ish connection, closed on exit."""
        conn = sqlite3.connect(self._db_path, isolation_level=None)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection inside ``BEGIN IMMEDIATE``; commit or roll back atomically."""
        conn = sqlite3.connect(self._db_path, isolation_level=None)
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
        finally:
            conn.close()

    # --- convenience wrappers delegating to SnapshotStore -----------------

    @staticmethod
    def activate_snapshot(conn: sqlite3.Connection, snapshot: PolicySnapshot) -> None:
        SnapshotStore.activate(conn, snapshot)

    @staticmethod
    def load_snapshot(conn: sqlite3.Connection, snapshot_id: str) -> PolicySnapshot:
        return SnapshotStore.load(conn, snapshot_id)


__all__ = ["SqliteStore"]
