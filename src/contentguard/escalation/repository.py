"""Minimal escalation queue repository — transaction-enlisted (REQ-INV-003/004).

S1 needs only enqueue/resolve/get/count so the policy kernel can prove an atomic
case+queue+audit commit. Intake, queue views, review APIs and duplicate-delivery
handling are S2-owned. The repository never commits; the caller's transaction owns the
boundary.
"""

from __future__ import annotations

import sqlite3

from .contracts import QueueEntry

_QUEUE_DDL = """
CREATE TABLE IF NOT EXISTS review_queue (
    case_id TEXT NOT NULL,
    case_revision INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    reason_id TEXT NOT NULL,
    enqueued_at TEXT NOT NULL,
    resolved_at TEXT,
    PRIMARY KEY (case_id, case_revision)
)
"""


class QueueRepository:
    """Transaction-enlisted hold/escalate queue operations."""

    @staticmethod
    def ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute(_QUEUE_DDL)

    @staticmethod
    def enqueue(conn: sqlite3.Connection, entry: QueueEntry) -> None:
        """Insert one queue entry; ``(case_id, case_revision)`` is unique."""
        conn.execute(
            """
            INSERT INTO review_queue (case_id, case_revision, outcome, reason_id, enqueued_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                entry.case_id,
                entry.case_revision,
                entry.outcome,
                entry.reason_id,
                entry.enqueued_at,
            ),
        )

    @staticmethod
    def resolve(conn: sqlite3.Connection, case_id: str, case_revision: int) -> None:
        """Mark the queue entry for (case_id, case_revision) resolved (no-op if absent)."""
        conn.execute(
            "UPDATE review_queue SET resolved_at = ? "
            "WHERE case_id = ? AND case_revision = ? AND resolved_at IS NULL",
            ("resolved", case_id, case_revision),
        )

    @staticmethod
    def get(conn: sqlite3.Connection, case_id: str) -> QueueEntry | None:
        row = conn.execute(
            "SELECT case_id, case_revision, outcome, reason_id, enqueued_at "
            "FROM review_queue WHERE case_id = ? AND resolved_at IS NULL "
            "ORDER BY case_revision DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        if row is None:
            return None
        return QueueEntry(
            case_id=str(row[0]),
            case_revision=int(str(row[1])),
            outcome=str(row[2]),
            reason_id=str(row[3]),
            enqueued_at=str(row[4]),
        )

    @staticmethod
    def count(conn: sqlite3.Connection) -> int:
        row = conn.execute(
            "SELECT COUNT(*) FROM review_queue WHERE resolved_at IS NULL"
        ).fetchone()
        return int(row[0])


__all__ = ["QueueRepository"]
