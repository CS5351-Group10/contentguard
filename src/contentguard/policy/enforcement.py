"""Sole protected-write API — the enforcement authority (REQ-INV-001/004).

Only ``EnforcementAuthority.commit`` writes protected state (case, queue, audit, replay).
A decision is accepted only if it carries the authority token minted by ``engine.py``;
a directly constructed decision (token ``None``) is a security violation and raises
:class:`ForbiddenAuthorityError` **before any write** — it is never downgraded to
``FAILED``. Expected persistence/validation failures roll back the whole transaction and
return ``FAILED`` with a diagnostic.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from typing import Any

from ..audit.contracts import AuditRecord
from ..audit.errors import AuditConflictError, AuditValidationError
from ..audit.repository import AuditRepository
from ..escalation.contracts import QueueEntry
from ..escalation.repository import QueueRepository
from .contracts import (
    CommitResult,
    CommitStatus,
    Outcome,
    PolicyDecision,
    ReplayKey,
    canonical_json,
    digest_of,
    is_frozen_dto,
)
from .errors import ForbiddenAuthorityError
from .store import SqliteStore

# The single opaque, non-serializable authority token a commit accepts. ``engine.py``
# stamps it on decisions it mints; nothing else can produce it (it is a private object,
# not a forgeable public string). Kept module-private so it is never importable as a
# public name — ``engine.py`` imports this private binding within the policy package.
_AUTHORITY_TOKEN = object()

_TERMINAL_OUTCOMES = frozenset({Outcome.APPROVE, Outcome.REJECT})
_QUEUE_OUTCOMES = frozenset({Outcome.HOLD, Outcome.ESCALATE})


class EnforcementAuthority:
    """The only writer of protected policy state, bound to one store."""

    def __init__(
        self,
        store: SqliteStore,
        *,
        audit_record_factory: Callable[[PolicyDecision], Mapping[str, Any]] | None = None,
    ) -> None:
        self._store = store
        self._audit_record_factory = audit_record_factory or _default_audit_mapping

    def commit(
        self,
        decision: PolicyDecision,
        *,
        expected_revision: int,
        replay_key: ReplayKey,
        review_identity_hash: str | None = None,
    ) -> CommitResult:
        # Step 1: authority-token check runs before any write and is never converted.
        if not is_frozen_dto(decision) or decision._authority_token is not _AUTHORITY_TOKEN:
            raise ForbiddenAuthorityError(
                "decision was not minted by the policy engine; refusing to commit"
            )

        # Step 2: canonical payload hash (excludes decided_at/decision_id/token).
        payload_hash = _payload_hash(decision)

        try:
            with self._store.transaction() as conn:
                # Step 3: replay lookup. When the caller supplies a review-request
                # identity (ADR-002 review replays), the stored identity must match
                # too: the projected decision payload alone cannot distinguish review
                # requests that collapse onto the same decision (rationale edits,
                # floor-overridden outcome changes). NULL stored identity vs a
                # supplied one (or vice versa) is a key collision across request
                # kinds — also a CONFLICT.
                replay = conn.execute(
                    "SELECT payload_hash, review_request_hash, result_json FROM commits "
                    "WHERE replay_actor = ? AND replay_key = ?",
                    (replay_key.actor_id, replay_key.idempotency_key),
                ).fetchone()
                if replay is not None:
                    stored_payload_hash, stored_identity_hash, stored_result_json = replay
                    if (
                        stored_identity_hash != review_identity_hash
                        or stored_payload_hash != payload_hash
                    ):
                        return CommitResult(
                            status=CommitStatus.CONFLICT,
                            decision_id=decision.decision_id,
                            audit_id=None,
                            case_revision=None,
                            message="replay key reused with a different payload",
                        )
                    return _commit_result_from_json(stored_result_json)

                # Step 4: bind the decision to the current case row.
                case_row = conn.execute(
                    "SELECT revision, content_hash, policy_snapshot_id, "
                    "policy_snapshot_digest FROM cases WHERE case_id = ?",
                    (decision.case_id,),
                ).fetchone()
                if case_row is None:
                    return _conflict(decision, "case not found")
                revision, content_hash, snap_id, snap_digest = case_row
                if (
                    decision.case_revision != expected_revision
                    or int(revision) != expected_revision
                    or content_hash != decision.content_hash
                    or snap_id != decision.policy_snapshot_id
                    or snap_digest != decision.policy_snapshot_digest
                ):
                    return _conflict(decision, "case revision/snapshot/hash mismatch")

                # Step 5: guarded case update; rowcount must be 1.
                new_revision = expected_revision + 1
                new_status = _status_for(decision.outcome)
                cur = conn.execute(
                    """
                    UPDATE cases SET revision = ?, status = ?, advisory_verdict = ?,
                        advisory_severity = ?, advisory_model_id = ?,
                        advisory_model_version = ?, analysis_failure_code = ?,
                        updated_at = ?
                    WHERE case_id = ? AND revision = ?
                    """,
                    (
                        new_revision,
                        new_status,
                        decision.advisory_verdict.value
                        if decision.advisory_verdict is not None
                        else None,
                        decision.advisory_severity.value
                        if decision.advisory_severity is not None
                        else None,
                        decision.advisory_model_id,
                        decision.advisory_model_version,
                        decision.analysis_failure_code.value
                        if decision.analysis_failure_code is not None
                        else None,
                        decision.decided_at.isoformat(),
                        decision.case_id,
                        expected_revision,
                    ),
                )
                if cur.rowcount != 1:
                    return _conflict(decision, "concurrent update lost the revision guard")

                # Step 6: queue enqueue (hold/escalate) or resolve (final outcome).
                if decision.outcome in _QUEUE_OUTCOMES:
                    QueueRepository.enqueue(
                        conn,
                        QueueEntry(
                            case_id=decision.case_id,
                            case_revision=new_revision,
                            outcome=decision.outcome.value,
                            reason_id=decision.reason_id,
                            enqueued_at=decision.decided_at.isoformat(),
                        ),
                    )
                elif decision.outcome in _TERMINAL_OUTCOMES:
                    QueueRepository.resolve(conn, decision.case_id, expected_revision)

                # Step 7: audit append (exactly one record per decision).
                mapping = self._audit_record_factory(decision)
                record = AuditRecord.from_mapping(mapping)
                audit_id = AuditRepository.append(conn, record)

                # Step 8: replay row.
                result = CommitResult(
                    status=CommitStatus.COMMITTED,
                    decision_id=decision.decision_id,
                    audit_id=audit_id,
                    case_revision=new_revision,
                    message="committed",
                )
                conn.execute(
                    """
                    INSERT INTO commits
                        (replay_actor, replay_key, payload_hash, review_request_hash,
                         decision_id, audit_id, result_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        replay_key.actor_id,
                        replay_key.idempotency_key,
                        payload_hash,
                        review_identity_hash,
                        decision.decision_id,
                        audit_id,
                        _commit_result_to_json(result),
                    ),
                )
                # Step 9: the ``with`` block commits on exit.
        except (AuditConflictError, AuditValidationError, ValueError, KeyError) as exc:
            return CommitResult(
                status=CommitStatus.FAILED,
                decision_id=decision.decision_id,
                audit_id=None,
                case_revision=None,
                message=f"commit failed: {exc}",
            )
        except sqlite3.Error as exc:
            return CommitResult(
                status=CommitStatus.FAILED,
                decision_id=decision.decision_id,
                audit_id=None,
                case_revision=None,
                message=f"persistence failed: {exc}",
            )
        return result


def _default_audit_mapping(decision: PolicyDecision) -> Mapping[str, Any]:
    return {
        "decision_id": decision.decision_id,
        "case_id": decision.case_id,
        "case_revision": decision.case_revision,
        "content_hash": decision.content_hash,
        "ai_verdict": (
            decision.advisory_verdict.value
            if decision.advisory_verdict is not None
            else None
        ),
        "analysis_failure_code": (
            decision.analysis_failure_code.value
            if decision.analysis_failure_code is not None
            else None
        ),
        "policy_reason_id": decision.reason_id,
        "policy_snapshot_id": decision.policy_snapshot_id,
        "policy_snapshot_digest": decision.policy_snapshot_digest,
        "outcome": decision.outcome.value,
        "actor_ids": decision.actor_ids,
        "decided_at": decision.decided_at.isoformat(),
    }


def _payload_hash(decision: PolicyDecision) -> str:
    return digest_of(
        {
            "case_id": decision.case_id,
            "case_revision": decision.case_revision,
            "outcome": decision.outcome.value,
            "reason_id": decision.reason_id,
            "policy_snapshot_id": decision.policy_snapshot_id,
            "policy_snapshot_digest": decision.policy_snapshot_digest,
            "content_hash": decision.content_hash,
            "advisory_verdict": (
                decision.advisory_verdict.value
                if decision.advisory_verdict is not None
                else None
            ),
            "advisory_severity": (
                decision.advisory_severity.value
                if decision.advisory_severity is not None
                else None
            ),
            "advisory_model_id": decision.advisory_model_id,
            "advisory_model_version": decision.advisory_model_version,
            "analysis_failure_code": (
                decision.analysis_failure_code.value
                if decision.analysis_failure_code is not None
                else None
            ),
            "actor_ids": sorted(decision.actor_ids),
        }
    )


def _status_for(outcome: Outcome) -> str:
    return {
        Outcome.APPROVE: "approved",
        Outcome.REJECT: "rejected",
        Outcome.HOLD: "held",
        Outcome.ESCALATE: "escalated",
    }[outcome]


def _conflict(decision: PolicyDecision, message: str) -> CommitResult:
    return CommitResult(
        status=CommitStatus.CONFLICT,
        decision_id=decision.decision_id,
        audit_id=None,
        case_revision=None,
        message=message,
    )


def _commit_result_to_json(result: CommitResult) -> str:
    return canonical_json(
        {
            "status": result.status.value,
            "decision_id": result.decision_id,
            "audit_id": result.audit_id,
            "case_revision": result.case_revision,
            "message": result.message,
        }
    )


def _commit_result_from_json(raw: str) -> CommitResult:
    import json

    data = json.loads(raw)
    return CommitResult(
        status=CommitStatus(data["status"]),
        decision_id=str(data["decision_id"]),
        audit_id=data["audit_id"],
        case_revision=data["case_revision"],
        message=str(data["message"]),
    )


__all__ = ["EnforcementAuthority"]
