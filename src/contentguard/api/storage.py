"""API-owned durable intake and authorized lookup storage (ADR-001; REQ-FUN-001/003).

Intake bookkeeping is not a moderation decision.  The tables here persist replay,
worker reservations, grants, and operational events without writing policy-owned
case, queue, or decision-audit state.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .schemas import AuditView, CaseView, ProcessingResult, QueueView

_SCHEMA = """
CREATE TABLE IF NOT EXISTS intake_intents (
    handoff_id TEXT PRIMARY KEY,
    actor_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    content_text TEXT NOT NULL,
    state TEXT NOT NULL,
    result_json TEXT,
    effective_flags TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(actor_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS intake_reservations (
    handoff_id TEXT PRIMARY KEY,
    lease_until TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    state TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(handoff_id) REFERENCES intake_intents(handoff_id)
);
CREATE TABLE IF NOT EXISTS api_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    actor_id TEXT,
    case_id TEXT,
    handoff_id TEXT,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS case_grants (
    case_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    granted_at TEXT NOT NULL,
    granted_by TEXT NOT NULL,
    PRIMARY KEY(case_id, actor_id)
);
"""


class IdempotencyConflict(ValueError):
    """An actor reused an idempotency key with a different payload hash."""


class StorageUnavailable(RuntimeError):
    """A durable-state query failed; absence of evidence was not established.

    Routes must map this to an unavailable (503) response — never to a 404, which
    would fabricate a legitimate-absence claim from a broken query (REQ-FUN-001,
    REQ-INV-004).
    """


def _absence_or_unavailable(exc: sqlite3.OperationalError, *, query: str) -> bool:
    """Return True when the error means the queried domain does not exist at all.

    An intake-only deployment legitimately has no policy tables, so a missing
    table is a truthful absence; any other operational failure is unavailable.
    """
    if "no such table" in str(exc).lower():
        return True
    raise StorageUnavailable(f"{query} query failed: {exc}") from exc


@dataclass(frozen=True)
class IntakeIntent:
    """Durable, non-authoritative accepted-intake state (REQ-FUN-001)."""

    handoff_id: str
    actor_id: str
    idempotency_key: str
    payload_hash: str
    content_text: str
    state: str
    result: ProcessingResult | None
    effective_flags: dict[str, bool]


class IntakeRepository:
    """SQLite repository for idempotent intake and recovery state."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(_SCHEMA)

    def connect(self) -> sqlite3.Connection:
        """Open one short-lived SQLite connection with foreign keys enabled."""

        conn = sqlite3.connect(self.database_path, timeout=5)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_intent(
        self,
        *,
        actor_id: str,
        idempotency_key: str,
        payload_hash: str,
        content_text: str,
        effective_flags: dict[str, bool],
    ) -> tuple[IntakeIntent, bool]:
        """Insert a unique logical intake or return its identical replay."""

        now = _now_iso()
        handoff_id = f"handoff-{uuid.uuid4().hex}"
        flags_json = _canonical_json(effective_flags)
        try:
            with self.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO intake_intents
                      (handoff_id, actor_id, idempotency_key, payload_hash, content_text,
                       state, result_json, effective_flags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?, ?, ?)
                    """,
                    (
                        handoff_id,
                        actor_id,
                        idempotency_key,
                        payload_hash,
                        content_text,
                        flags_json,
                        now,
                        now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO intake_reservations
                      (handoff_id, lease_until, attempt_count, state, updated_at)
                    VALUES (?, NULL, 0, 'pending', ?)
                    """,
                    (handoff_id, now),
                )
        except sqlite3.IntegrityError:
            existing = self.find_by_replay(actor_id, idempotency_key)
            if existing is None:
                raise
            if existing.payload_hash != payload_hash:
                raise IdempotencyConflict from None
            return existing, False
        created = self.get_intent(handoff_id)
        if created is None:  # pragma: no cover - SQLite committed insert contract
            raise sqlite3.DatabaseError("created intake intent disappeared")
        return created, True

    def find_by_replay(self, actor_id: str, idempotency_key: str) -> IntakeIntent | None:
        """Resolve actor+key replay identity without starting another worker."""

        with self.connect() as conn:
            row = conn.execute(
                "SELECT handoff_id, actor_id, idempotency_key, payload_hash, content_text, "
                "state, result_json, effective_flags FROM intake_intents "
                "WHERE actor_id = ? AND idempotency_key = ?",
                (actor_id, idempotency_key),
            ).fetchone()
        return None if row is None else _intent_from_row(row)

    def get_intent(self, handoff_id: str) -> IntakeIntent | None:
        """Read one durable intake intent for reconciliation."""

        with self.connect() as conn:
            row = conn.execute(
                "SELECT handoff_id, actor_id, idempotency_key, payload_hash, content_text, "
                "state, result_json, effective_flags FROM intake_intents "
                "WHERE handoff_id = ?",
                (handoff_id,),
            ).fetchone()
        return None if row is None else _intent_from_row(row)

    def list_recoverable_pending(
        self, *, before: datetime, limit: int
    ) -> tuple[IntakeIntent, ...]:
        """List pending intents with an expired/released reservation for recovery."""

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT i.handoff_id, i.actor_id, i.idempotency_key, i.payload_hash,
                       i.content_text, i.state, i.result_json, i.effective_flags
                FROM intake_intents i
                JOIN intake_reservations r ON r.handoff_id = i.handoff_id
                WHERE i.state = 'pending'
                  AND r.state IN ('pending', 'processing')
                  AND (r.lease_until IS NULL OR r.lease_until < ?)
                ORDER BY i.updated_at, i.handoff_id
                LIMIT ?
                """,
                (before.isoformat(), limit),
            ).fetchall()
        return tuple(_intent_from_row(row) for row in rows)

    def acquire_lease(self, handoff_id: str, lease_seconds: int) -> bool:
        """Atomically acquire an expired/released reservation and increment attempts."""

        now = datetime.now(UTC)
        now_iso = now.isoformat()
        lease_until = (now + timedelta(seconds=lease_seconds)).isoformat()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE intake_reservations
                SET lease_until = ?, attempt_count = attempt_count + 1,
                    state = 'processing', updated_at = ?
                WHERE handoff_id = ?
                  AND (lease_until IS NULL OR lease_until < ?)
                """,
                (lease_until, now_iso, handoff_id, now_iso),
            )
        return cursor.rowcount == 1

    def release_pending(self, handoff_id: str) -> None:
        """Release a transiently failed attempt so replay/recovery may probe once."""

        now = _now_iso()
        with self.connect() as conn:
            conn.execute(
                "UPDATE intake_reservations SET lease_until = NULL, state = 'pending', "
                "updated_at = ? WHERE handoff_id = ?",
                (now, handoff_id),
            )
            conn.execute(
                "UPDATE intake_intents SET state = 'pending', updated_at = ? "
                "WHERE handoff_id = ?",
                (now, handoff_id),
            )

    def save_result(self, handoff_id: str, result: ProcessingResult) -> None:
        """Persist a confirmed/failed processing result for truthful replay."""

        state = "terminal" if result.status == "committed" else result.status
        now = _now_iso()
        result_json = _canonical_json(
            {
                "status": result.status,
                "case_id": result.case_id,
                "case_revision": result.case_revision,
                "decision_id": result.decision_id,
                "audit_id": result.audit_id,
                "outcome": result.outcome,
                "message": result.message,
            }
        )
        with self.connect() as conn:
            conn.execute(
                "UPDATE intake_intents SET state = ?, result_json = ?, updated_at = ? "
                "WHERE handoff_id = ?",
                (state, result_json, now, handoff_id),
            )
            conn.execute(
                "UPDATE intake_reservations SET lease_until = NULL, state = ?, "
                "updated_at = ? WHERE handoff_id = ?",
                (state, now, handoff_id),
            )

    def record_event(
        self,
        event_type: str,
        *,
        actor_id: str | None,
        case_id: str | None = None,
        handoff_id: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        """Append an operational API event without claiming a moderation decision."""

        with self.connect() as conn:
            conn.execute(
                "INSERT INTO api_events "
                "(event_type, actor_id, case_id, handoff_id, details_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event_type,
                    actor_id,
                    case_id,
                    handoff_id,
                    _canonical_json(details or {}),
                    _now_iso(),
                ),
            )

    def has_case_grant(self, case_id: str, actor_id: str) -> bool:
        """Return whether a moderator has an explicit grant for this case."""

        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM case_grants WHERE case_id = ? AND actor_id = ?",
                (case_id, actor_id),
            ).fetchone()
        return row is not None

    def get_case(self, case_id: str) -> CaseView | None:
        """Read policy-owned case state and API-owned submission ownership."""

        with self.connect() as conn:
            try:
                row = conn.execute(
                    """
                    SELECT c.case_id, i.actor_id, c.revision, c.status, c.content_hash,
                           c.policy_snapshot_id, c.policy_snapshot_digest, c.content_text,
                           json_extract(i.result_json, '$.audit_id')
                    FROM cases c
                    LEFT JOIN intake_intents i
                      ON json_extract(i.result_json, '$.case_id') = c.case_id
                    WHERE c.case_id = ?
                    ORDER BY i.updated_at DESC LIMIT 1
                    """,
                    (case_id,),
                ).fetchone()
            except sqlite3.OperationalError as exc:
                if _absence_or_unavailable(exc, query="case"):
                    return None
        if row is None:
            return None
        return CaseView(
            case_id=str(row[0]),
            owner_id="" if row[1] is None else str(row[1]),
            revision=int(row[2]),
            status=str(row[3]),
            content_hash=str(row[4]),
            policy_snapshot_id=str(row[5]),
            policy_snapshot_digest=str(row[6]),
            content_text=None if row[7] is None else str(row[7]),
            audit_id=None if row[8] is None else str(row[8]),
        )

    def get_audit(self, audit_id: str) -> AuditView | None:
        """Read immutable policy decision evidence with API-owned owner attribution."""

        with self.connect() as conn:
            try:
                row = conn.execute(
                    """
                    SELECT a.audit_id, a.decision_id, a.case_id, a.case_revision,
                           i.actor_id, a.outcome, a.policy_reason_id,
                           a.policy_snapshot_id, a.policy_snapshot_digest
                    FROM audit_records a
                    LEFT JOIN intake_intents i
                      ON json_extract(i.result_json, '$.case_id') = a.case_id
                    WHERE a.audit_id = ?
                    ORDER BY i.updated_at DESC LIMIT 1
                    """,
                    (audit_id,),
                ).fetchone()
            except sqlite3.OperationalError as exc:
                if _absence_or_unavailable(exc, query="audit"):
                    return None
        if row is None:
            return None
        return AuditView(
            audit_id=str(row[0]),
            decision_id=str(row[1]),
            case_id=str(row[2]),
            case_revision=int(row[3]),
            owner_id="" if row[4] is None else str(row[4]),
            outcome=str(row[5]),
            policy_reason_id=str(row[6]),
            policy_snapshot_id=str(row[7]),
            policy_snapshot_digest=str(row[8]),
        )

    def list_open_queue(self) -> tuple[QueueView, ...]:
        """Read unresolved queue entries; authorization filtering remains in API."""

        with self.connect() as conn:
            try:
                rows = conn.execute(
                    """
                    SELECT q.case_id, q.case_revision, q.outcome, q.reason_id,
                           COALESCE(c.advisory_severity, 'unknown'), q.enqueued_at
                    FROM review_queue q
                    LEFT JOIN cases c ON c.case_id = q.case_id
                    WHERE q.resolved_at IS NULL
                    ORDER BY q.enqueued_at, q.case_id
                    """
                ).fetchall()
            except sqlite3.OperationalError as exc:
                if _absence_or_unavailable(exc, query="queue"):
                    return ()
        return tuple(
            QueueView(
                case_id=str(row[0]),
                case_revision=int(row[1]),
                outcome=str(row[2]),
                reason_id=str(row[3]),
                severity=str(row[4]),
                enqueued_at=str(row[5]),
            )
            for row in rows
        )


def _intent_from_row(row: tuple[object, ...]) -> IntakeIntent:
    raw_result = None if row[6] is None else json.loads(str(row[6]))
    result = None if raw_result is None else ProcessingResult(**raw_result)
    return IntakeIntent(
        handoff_id=str(row[0]),
        actor_id=str(row[1]),
        idempotency_key=str(row[2]),
        payload_hash=str(row[3]),
        content_text=str(row[4]),
        state=str(row[5]),
        result=result,
        effective_flags=json.loads(str(row[7])),
    )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


__all__ = ["IdempotencyConflict", "IntakeIntent", "IntakeRepository"]
