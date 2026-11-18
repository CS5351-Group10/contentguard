"""Audit repository — append-only, transaction-enlisted (REQ-INV-004).

``append`` validates the record (defense in depth), inserts it, and returns the assigned
``audit_id``. ``audit_id`` is a UNIQUE column; ``decision_id`` is also UNIQUE. On a
duplicate ``decision_id`` the full record is compared: identical → return the existing
row's audit_id (replay); different → :class:`AuditConflictError`. The repository never
commits — the caller's transaction owns the boundary.
"""

from __future__ import annotations

import sqlite3
import uuid

from .contracts import AuditRecord
from .errors import AuditConflictError

_AUDIT_DDL = """
CREATE TABLE IF NOT EXISTS audit_records (
    audit_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL UNIQUE,
    case_id TEXT NOT NULL,
    case_revision INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    ai_verdict TEXT,
    analysis_failure_code TEXT,
    policy_reason_id TEXT NOT NULL,
    policy_snapshot_id TEXT NOT NULL,
    policy_snapshot_digest TEXT NOT NULL,
    outcome TEXT NOT NULL,
    actor_ids TEXT NOT NULL,
    decided_at TEXT NOT NULL
)
"""


class AuditRepository:
    """Append-only audit rows with immutable evidence lookup."""

    @staticmethod
    def ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute(_AUDIT_DDL)

    @staticmethod
    def append(conn: sqlite3.Connection, record: AuditRecord) -> str:
        """Validate, insert, and return the audit id (replay-safe on decision id)."""
        existing = conn.execute(
            "SELECT * FROM audit_records WHERE decision_id = ?", (record.decision_id,)
        ).fetchone()
        if existing is not None:
            stored = _record_from_row(existing)
            if stored == record:
                return str(existing[0])
            raise AuditConflictError(
                f"decision_id {record.decision_id!r} already exists with different content"
            )
        audit_id = f"audit-{uuid.uuid4().hex}"
        conn.execute(
            """
            INSERT INTO audit_records (
                audit_id, decision_id, case_id, case_revision, content_hash,
                ai_verdict, analysis_failure_code, policy_reason_id,
                policy_snapshot_id, policy_snapshot_digest, outcome, actor_ids, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                record.decision_id,
                record.case_id,
                record.case_revision,
                record.content_hash,
                record.ai_verdict,
                record.analysis_failure_code,
                record.policy_reason_id,
                record.policy_snapshot_id,
                record.policy_snapshot_digest,
                record.outcome,
                "\x1f".join(record.actor_ids),
                record.decided_at,
            ),
        )
        return audit_id

    @staticmethod
    def read(conn: sqlite3.Connection, audit_id: str) -> AuditRecord:
        row = conn.execute(
            "SELECT * FROM audit_records WHERE audit_id = ?", (audit_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"audit {audit_id!r} not found")
        return _record_from_row(row)

    @staticmethod
    def find_by_decision(conn: sqlite3.Connection, decision_id: str) -> AuditRecord | None:
        row = conn.execute(
            "SELECT * FROM audit_records WHERE decision_id = ?", (decision_id,)
        ).fetchone()
        return None if row is None else _record_from_row(row)


def _record_from_row(row: tuple[object, ...]) -> AuditRecord:
    # Columns: audit_id, decision_id, case_id, case_revision, content_hash, ai_verdict,
    # analysis_failure_code, policy_reason_id, policy_snapshot_id, policy_snapshot_digest,
    # outcome, actor_ids, decided_at.
    return AuditRecord(
        decision_id=str(row[1]),
        case_id=str(row[2]),
        case_revision=int(str(row[3])),
        content_hash=str(row[4]),
        ai_verdict=None if row[5] is None else str(row[5]),
        analysis_failure_code=None if row[6] is None else str(row[6]),
        policy_reason_id=str(row[7]),
        policy_snapshot_id=str(row[8]),
        policy_snapshot_digest=str(row[9]),
        outcome=str(row[10]),
        actor_ids=tuple(str(row[11]).split("\x1f")) if row[11] else (),
        decided_at=str(row[12]),
    )


__all__ = ["AuditRepository"]
