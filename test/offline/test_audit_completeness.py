"""Audit completeness & atomic commit (REQ-INV-004) — real SQLite, no mocks.

Verifies REQ-INV-004: every committed decision writes exactly one audit record, and the
case state + queue + audit are written in a single transaction that rolls back entirely
on any failure. A controlled policy error yields FAILED with no partial state.

Slice B covers the non-review paths (normal, typed-failure, replay, schema/validation
rejection, duplicate decision id, final state, one-revision-one-winner). Human-reviewed
and held-review transitions are CP4 (routing slice) and are intentionally absent here.

Broader intake/concurrency/duplicate-delivery behaviour is S2-owned and not tested here.
All persistence is real SQLite (``tmp_path`` file DB); triggers inject write failures —
nothing is mocked.
"""

from __future__ import annotations

import pytest
from conftest import (
    CONTENT_HASH,
    make_case,
    make_snapshot,
    make_snapshot_v2,
)

from contentguard.audit.contracts import AuditRecord
from contentguard.audit.errors import AuditConflictError, AuditValidationError
from contentguard.audit.repository import AuditRepository
from contentguard.escalation.contracts import QueueEntry
from contentguard.escalation.repository import QueueRepository
from contentguard.policy.contracts import (
    ActorRef,
    AdvisoryResult,
    AnalysisFailure,
    CaseSnapshot,
    CaseStatus,
    CommitStatus,
    FailureCode,
    Outcome,
    ReplayKey,
    ReviewRequest,
    Severity,
    Verdict,
)
from contentguard.policy.engine import PolicyEngine
from contentguard.policy.errors import (
    ForbiddenAuthorityError,
    StaleReviewError,
    UnauthorizedReviewError,
)
from contentguard.policy.snapshot import PolicySnapshot
from contentguard.policy.store import SqliteStore


def _advisory(
    *, verdict: Verdict, severity: Severity, model_id: str = "model-x"
) -> AdvisoryResult:
    return AdvisoryResult.from_payload(
        {
            "role": "initial_review",
            "verdict": verdict.value,
            "severity": severity.value,
            "rationale": "model rationale",
            "citations": ("clause-001",),
            "prompt_version": "prompt-v1",
            "model_id": model_id,
            "model_version": "2026-11",
            "usage": {"input_tokens": 10, "output_tokens": 5, "usage_unknown": False},
        }
    )


@pytest.fixture()
def store(tmp_path: object) -> SqliteStore:
    """A fresh file-backed SQLite store with schemas created."""
    db_path = f"{tmp_path}/cases.db"
    sqlite_store = SqliteStore(db_path)
    sqlite_store.initialize()
    return sqlite_store


def _seed_case(
    store: SqliteStore,
    case: CaseSnapshot,
    *,
    activate_snapshot: PolicySnapshot | None = None,
) -> None:
    """Activate the pinned snapshot (once) and insert the case row."""
    snapshot = activate_snapshot or make_snapshot()
    with store.transaction() as conn:
        # Activate idempotently: if this snapshot id already exists, skip.
        existing = conn.execute(
            "SELECT 1 FROM policy_snapshots WHERE snapshot_id = ?", (snapshot.snapshot_id,)
        ).fetchone()
        if existing is None:
            store.activate_snapshot(conn, snapshot)
    with store.transaction() as conn:
        conn.execute(
            """
            INSERT INTO cases (
                case_id, revision, status, content_hash, policy_snapshot_id,
                policy_snapshot_digest, content_text, advisory_verdict,
                advisory_severity, advisory_model_id, advisory_model_version,
                analysis_failure_code, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case.case_id,
                case.revision,
                case.status.value,
                case.content_hash,
                case.policy_snapshot_id,
                case.policy_snapshot_digest,
                "benign text",
                case.advisory_verdict.value if case.advisory_verdict else None,
                case.advisory_severity.value if case.advisory_severity else None,
                case.advisory_model_id,
                case.advisory_model_version,
                case.analysis_failure_code.value if case.analysis_failure_code else None,
                "2026-11-18T00:00:00+00:00",
            ),
        )


def _audit_count(store: SqliteStore) -> int:
    with store.read_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM audit_records").fetchone()
    return int(row[0])


def _case_row(store: SqliteStore, case_id: str) -> tuple[int, str]:
    with store.read_connection() as conn:
        row = conn.execute(
            "SELECT revision, status FROM cases WHERE case_id = ?", (case_id,)
        ).fetchone()
    return int(row[0]), str(row[1])


def _queue_rows(store: SqliteStore) -> list[tuple[str, int]]:
    with store.read_connection() as conn:
        rows = conn.execute(
            "SELECT case_id, case_revision FROM review_queue"
        ).fetchall()
    return [(str(r[0]), int(r[1])) for r in rows]


def test_one_record_per_decision_normal(store: SqliteStore) -> None:
    """Verifies REQ-INV-004: a normal decision writes exactly one complete audit row.

    The row carries the policy actor, the AI model actor, and the decision's own reason
    and snapshot identifiers.
    """
    case = make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW))
    _seed_case(store, case)
    engine = PolicyEngine(make_snapshot())
    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="submitter-1", idempotency_key="idem-1"),
    )
    assert result.status is CommitStatus.COMMITTED
    assert result.audit_id is not None
    assert _audit_count(store) == 1
    with store.read_connection() as conn:
        record = AuditRepository.read(conn, result.audit_id)
    assert record.outcome == Outcome.APPROVE.value
    assert record.ai_verdict == Verdict.ALLOW.value
    assert record.analysis_failure_code is None
    assert "policy" in record.actor_ids
    assert "ai:model-x" in record.actor_ids
    assert record.policy_snapshot_id == case.policy_snapshot_id
    assert record.policy_snapshot_digest == case.policy_snapshot_digest
    assert record.content_hash == CONTENT_HASH
    # Case revision advanced exactly once; status reflects the outcome.
    revision, status = _case_row(store, case.case_id)
    assert revision == case.revision + 1
    assert status == CaseStatus.APPROVED.value


def test_one_record_per_decision_typed_failure(store: SqliteStore) -> None:
    """Verifies REQ-INV-004: a typed-failure decision writes one audit row with
    ``ai_verdict=None`` and the failure code set, and holds the case into the queue."""
    case = make_case(advisory=None)
    _seed_case(store, case)
    engine = PolicyEngine(make_snapshot())
    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=_make_failure(),
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="submitter-1", idempotency_key="idem-fail"),
    )
    assert result.status is CommitStatus.COMMITTED
    assert result.audit_id is not None
    with store.read_connection() as conn:
        record = AuditRepository.read(conn, result.audit_id)
    assert record.ai_verdict is None
    assert record.analysis_failure_code == FailureCode.TIMEOUT.value
    assert record.outcome == Outcome.HOLD.value
    _revision, status = _case_row(store, case.case_id)
    assert status == CaseStatus.HELD.value
    assert _queue_rows(store) == [(case.case_id, case.revision + 1)]


def _make_failure() -> AnalysisFailure:
    return AnalysisFailure(code=FailureCode.TIMEOUT, detail="provider timed out")


def test_audit_write_failure_rolls_back(store: SqliteStore) -> None:
    """Verifies REQ-INV-004 (negative): a failing audit insert rolls back the whole
    transaction — case revision/status unchanged, queue empty, no audit row."""
    case = make_case(advisory=_advisory(verdict=Verdict.VIOLATE, severity=Severity.HIGH))
    _seed_case(store, case)
    with store.transaction() as conn:
        conn.execute(
            """
            CREATE TRIGGER fail_audit BEFORE INSERT ON audit_records
            BEGIN SELECT RAISE(ABORT, 'audit down'); END;
            """
        )
    engine = PolicyEngine(make_snapshot())
    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="submitter-1", idempotency_key="idem-audit-fail"),
    )
    assert result.status is CommitStatus.FAILED
    revision, status = _case_row(store, case.case_id)
    assert revision == case.revision
    assert status == case.status.value
    assert _queue_rows(store) == []
    assert _audit_count(store) == 0


def test_queue_write_failure_rolls_back(store: SqliteStore) -> None:
    """Verifies REQ-INV-004 (negative): a failing queue insert rolls back everything —
    no audit row and the case is unchanged."""
    case = make_case(advisory=None)
    _seed_case(store, case)
    with store.transaction() as conn:
        conn.execute(
            """
            CREATE TRIGGER fail_queue BEFORE INSERT ON review_queue
            BEGIN SELECT RAISE(ABORT, 'queue down'); END;
            """
        )
    engine = PolicyEngine(make_snapshot())
    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=_make_failure(),
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="submitter-1", idempotency_key="idem-queue-fail"),
    )
    assert result.status is CommitStatus.FAILED
    revision, status = _case_row(store, case.case_id)
    assert revision == case.revision
    assert status == case.status.value
    assert _queue_rows(store) == []
    assert _audit_count(store) == 0


def test_replay_one_audit_record(store: SqliteStore) -> None:
    """Verifies REQ-INV-004: repeating one logical commit (same replay key + payload)
    returns the same audit id and creates exactly one audit row; a same-key/different
    payload is a conflict."""
    case = make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW))
    _seed_case(store, case)
    engine = PolicyEngine(make_snapshot())
    key = ReplayKey(actor_id="submitter-1", idempotency_key="idem-replay")

    first = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=key,
    )
    second = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=key,
    )
    assert first.status is CommitStatus.COMMITTED
    assert second.status is CommitStatus.COMMITTED
    assert first.audit_id == second.audit_id
    assert _audit_count(store) == 1


def test_replay_same_key_different_payload_conflicts(store: SqliteStore) -> None:
    """Verifies REQ-INV-004 (negative): the same replay key with a different payload
    returns CONFLICT and never the old result."""
    case = make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW))
    _seed_case(store, case)
    engine = PolicyEngine(make_snapshot())
    key = ReplayKey(actor_id="submitter-1", idempotency_key="idem-conflict")

    engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=key,
    )
    conflict = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW, model_id="model-y"),
        expected_revision=case.revision,
        replay_key=key,
    )
    assert conflict.status is CommitStatus.CONFLICT
    assert _audit_count(store) == 1


def test_replay_survives_newer_active_snapshot(store: SqliteStore) -> None:
    """Verifies REQ-INV-004 (replay ordering): a case committed under pinned v1 keeps
    returning its stored result when the same replay key + payload is retried **after** a
    newer snapshot (v2) is globally activated. The replay must be recognised by payload
    hash against the case's pinned snapshot, not re-decided against the now-active v2
    (which would misclassify a legitimate retry as CONFLICT). A same-key/different-payload
    retry under the newer active snapshot is still CONFLICT."""
    case = make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW))
    _seed_case(store, case)
    engine = PolicyEngine(make_snapshot())
    key = ReplayKey(actor_id="submitter-1", idempotency_key="idem-replay-v2")

    first = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=key,
    )
    assert first.status is CommitStatus.COMMITTED

    with store.transaction() as conn:
        store.activate_snapshot(conn, make_snapshot_v2())

    retry = PolicyEngine(make_snapshot_v2()).evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=key,
    )
    assert retry.status is CommitStatus.COMMITTED
    assert retry.audit_id == first.audit_id
    assert _audit_count(store) == 1

    conflict = PolicyEngine(make_snapshot_v2()).evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW, model_id="model-y"),
        expected_revision=case.revision,
        replay_key=key,
    )
    assert conflict.status is CommitStatus.CONFLICT
    assert _audit_count(store) == 1


@pytest.mark.parametrize(
    "missing_key",
    sorted(
        {
            "decision_id",
            "case_id",
            "case_revision",
            "content_hash",
            "ai_verdict",
            "analysis_failure_code",
            "policy_reason_id",
            "policy_snapshot_id",
            "policy_snapshot_digest",
            "outcome",
            "actor_ids",
            "decided_at",
        }
    ),
)
def test_audit_schema_rejects_missing_field(missing_key: str) -> None:
    """Verifies REQ-INV-004 (negative): ``AuditRecord.from_mapping`` rejects a payload
    missing any required field with ``AuditValidationError``."""
    payload = _valid_audit_mapping()
    del payload[missing_key]
    with pytest.raises(AuditValidationError):
        AuditRecord.from_mapping(payload)


def test_audit_schema_rejects_unknown_field() -> None:
    """Verifies REQ-INV-004 (negative): an unknown key is rejected."""
    payload = _valid_audit_mapping()
    payload["extra"] = "x"
    with pytest.raises(AuditValidationError):
        AuditRecord.from_mapping(payload)


def test_audit_schema_rejects_both_verdict_and_failure() -> None:
    """Verifies REQ-INV-004 (negative): a fabricated verdict alongside a failure code is
    rejected — exactly one of the two must be present."""
    payload = _valid_audit_mapping()
    payload["analysis_failure_code"] = "timeout"
    with pytest.raises(AuditValidationError):
        AuditRecord.from_mapping(payload)


def test_duplicate_decision_id_different_payload_conflicts(store: SqliteStore) -> None:
    """Verifies REQ-INV-004 (negative): re-appending a record with an existing decision
    id but different fields raises ``AuditConflictError``; an identical record is a
    replay (returns the existing row), not a second row."""
    record = AuditRecord.from_mapping(_valid_audit_mapping())
    with store.transaction() as conn:
        first_id = AuditRepository.append(conn, record)
    with store.transaction() as conn:
        replay_id = AuditRepository.append(conn, record)
    assert replay_id == first_id
    assert _audit_count(store) == 1

    changed = _valid_audit_mapping()
    changed["outcome"] = "reject"
    with pytest.raises(AuditConflictError), store.transaction() as conn:
        AuditRepository.append(conn, AuditRecord.from_mapping(changed))
    assert _audit_count(store) == 1


def test_final_case_cannot_be_rewritten(store: SqliteStore) -> None:
    """Verifies REQ-INV-004 / REQ-INV-003: a case already in a final state rejects a new
    evaluation/commit (no second audit row)."""
    case = make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW))
    _seed_case(store, case)
    engine = PolicyEngine(make_snapshot())
    first = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="submitter-1", idempotency_key="idem-final-1"),
    )
    assert first.status is CommitStatus.COMMITTED
    # The case is now APPROVED; re-evaluating the stale snapshot must fail (final state).
    final_case = CaseSnapshot(
        case_id=case.case_id,
        revision=case.revision + 1,
        status=CaseStatus.APPROVED,
        content_hash=case.content_hash,
        policy_snapshot_id=case.policy_snapshot_id,
        policy_snapshot_digest=case.policy_snapshot_digest,
        advisory_verdict=Verdict.ALLOW,
        advisory_severity=Severity.LOW,
        advisory_model_id="model-x",
        advisory_model_version="2026-11",
    )
    second = engine.evaluate_and_commit(
        store=store,
        case=final_case,
        content_text="benign text",
        advisory=None,
        expected_revision=final_case.revision,
        replay_key=ReplayKey(actor_id="submitter-1", idempotency_key="idem-final-2"),
    )
    assert second.status is CommitStatus.FAILED
    assert _audit_count(store) == 1


def test_one_revision_one_winner(store: SqliteStore) -> None:
    """Verifies REQ-INV-004: two different decisions commit against the same expected
    revision; the first wins, the second returns CONFLICT, and only one audit row
    exists. (Sequential SQLite transactions; broader worker concurrency stays S2.)"""
    case = make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW))
    _seed_case(store, case)
    engine = PolicyEngine(make_snapshot())

    winner = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="submitter-1", idempotency_key="idem-winner"),
    )
    loser = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="submitter-2", idempotency_key="idem-loser"),
    )
    assert winner.status is CommitStatus.COMMITTED
    assert loser.status is CommitStatus.CONFLICT
    assert _audit_count(store) == 1


def test_commit_binds_case_snapshot_and_hash(store: SqliteStore) -> None:
    """Verifies REQ-INV-004 (negative): a decision whose content hash does not match the
    case row is a CONFLICT with no state change."""
    case = make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW))
    _seed_case(store, case)
    engine = PolicyEngine(make_snapshot())
    mismatched = CaseSnapshot(
        case_id=case.case_id,
        revision=case.revision,
        status=case.status,
        content_hash="c" * 64,  # differs from the stored row
        policy_snapshot_id=case.policy_snapshot_id,
        policy_snapshot_digest=case.policy_snapshot_digest,
        advisory_verdict=Verdict.ALLOW,
        advisory_severity=Severity.LOW,
        advisory_model_id="model-x",
        advisory_model_version="2026-11",
    )
    result = engine.evaluate_and_commit(
        store=store,
        case=mismatched,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="submitter-1", idempotency_key="idem-hash"),
    )
    assert result.status is CommitStatus.CONFLICT
    assert _audit_count(store) == 0


def test_forged_decision_raises_forbidden_authority(store: SqliteStore) -> None:
    """Verifies REQ-INV-001 (negative): a directly constructed decision with no engine
    token raises ``ForbiddenAuthorityError`` (not FAILED) and performs no writes."""
    from datetime import UTC, datetime

    from contentguard.policy.contracts import PolicyDecision
    from contentguard.policy.enforcement import EnforcementAuthority

    case = make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW))
    _seed_case(store, case)
    authority = EnforcementAuthority(store)
    forged = PolicyDecision(
        decision_id="forged-decision-id",
        case_id=case.case_id,
        case_revision=case.revision,
        outcome=Outcome.APPROVE,
        reason_id="RULE-ALLOW-LOW",
        reason_text="Allowed.",
        severity=Severity.LOW,
        advisory_verdict=Verdict.ALLOW,
        advisory_severity=Severity.LOW,
        advisory_model_id="model-x",
        advisory_model_version="2026-11",
        analysis_failure_code=None,
        policy_snapshot_id=case.policy_snapshot_id,
        policy_snapshot_digest=case.policy_snapshot_digest,
        content_hash=case.content_hash,
        requires_human_review=False,
        actor_ids=("policy", "ai:model-x"),
        decided_at=datetime(2026, 11, 18, tzinfo=UTC),
        _authority_token=None,
    )
    with pytest.raises(ForbiddenAuthorityError):
        authority.commit(
            forged,
            expected_revision=case.revision,
            replay_key=ReplayKey(actor_id="submitter-1", idempotency_key="idem-forged"),
        )
    assert _audit_count(store) == 0


def _valid_audit_mapping() -> dict[str, object]:
    return {
        "decision_id": "dec-1",
        "case_id": "case-1",
        "case_revision": 1,
        "content_hash": CONTENT_HASH,
        "ai_verdict": "allow",
        "analysis_failure_code": None,
        "policy_reason_id": "RULE-ALLOW-LOW",
        "policy_snapshot_id": "POL-SNAP-V1",
        "policy_snapshot_digest": "a" * 64,
        "outcome": "approve",
        "actor_ids": ("policy", "ai:model-x"),
        "decided_at": "2026-11-18T00:00:00+00:00",
    }


# --- Slice C (CP4): human-reviewed decisions & queue resolution -------------------


def _review(
    *,
    outcome: Outcome,
    case: CaseSnapshot,
    snapshot: PolicySnapshot,
    reviewer_role: str = "moderator",
    rationale: str = "manual moderator decision",
    case_id: str | None = None,
    revision: int | None = None,
    content_hash: str | None = None,
) -> ReviewRequest:
    return ReviewRequest(
        reviewer=ActorRef(actor_id="moderator-1", role=reviewer_role),
        case_id=case_id if case_id is not None else case.case_id,
        expected_revision=revision if revision is not None else case.revision,
        requested_outcome=outcome,
        rationale=rationale,
        policy_snapshot_id=snapshot.snapshot_id,
        policy_snapshot_digest=snapshot.digest,
        content_hash=content_hash if content_hash is not None else case.content_hash,
    )


def _seed_reviewable_case(
    store: SqliteStore,
    case: CaseSnapshot,
    *,
    snapshot: PolicySnapshot,
    queue_outcome: str,
    reason_id: str,
) -> None:
    """Activate the snapshot, insert the held/escalated case row, and enqueue it."""
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT 1 FROM policy_snapshots WHERE snapshot_id = ?", (snapshot.snapshot_id,)
        ).fetchone()
        if existing is None:
            store.activate_snapshot(conn, snapshot)
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO cases (case_id, revision, status, content_hash, "
            "policy_snapshot_id, policy_snapshot_digest, content_text, advisory_verdict, "
            "advisory_severity, advisory_model_id, advisory_model_version, "
            "analysis_failure_code, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                case.case_id, case.revision, case.status.value, case.content_hash,
                case.policy_snapshot_id, case.policy_snapshot_digest, "seed",
                case.advisory_verdict.value if case.advisory_verdict else None,
                case.advisory_severity.value if case.advisory_severity else None,
                case.advisory_model_id, case.advisory_model_version,
                case.analysis_failure_code.value if case.analysis_failure_code else None,
                "2026-11-18T00:00:00+00:00",
            ),
        )
        QueueRepository.enqueue(
            conn,
            QueueEntry(
                case_id=case.case_id,
                case_revision=case.revision,
                outcome=queue_outcome,
                reason_id=reason_id,
                enqueued_at="2026-11-18T00:00:00+00:00",
            ),
        )


def test_human_reviewed_decision_one_audit(store: SqliteStore) -> None:
    """Verifies REQ-INV-004: a human-reviewed decision writes exactly one audit row with
    reason ``RULE-HUMAN-REVIEW`` and actors ``policy`` + ``ai:<model>`` + ``reviewer:<id>``
    and resolves the queue entry."""
    snapshot = make_snapshot()
    case = make_case(
        advisory=_advisory(verdict=Verdict.REVIEW, severity=Severity.MEDIUM),
        snapshot=snapshot,
        status=CaseStatus.HELD,
    )
    _seed_reviewable_case(
        store, case, snapshot=snapshot, queue_outcome="hold", reason_id="RULE-REVIEW"
    )
    engine = PolicyEngine(snapshot)
    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        review=_review(outcome=Outcome.APPROVE, case=case, snapshot=snapshot),
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="moderator-1", idempotency_key="idem-hr-1"),
    )
    assert result.status is CommitStatus.COMMITTED
    assert result.audit_id is not None
    assert _audit_count(store) == 1
    with store.read_connection() as conn:
        record = AuditRepository.read(conn, result.audit_id)
        unresolved = QueueRepository.count(conn)
    assert record.outcome == Outcome.APPROVE.value
    assert record.policy_reason_id == "RULE-HUMAN-REVIEW"
    assert "policy" in record.actor_ids
    assert "ai:model-x" in record.actor_ids
    assert "reviewer:moderator-1" in record.actor_ids
    assert unresolved == 0


def test_analysis_failure_review_can_finalize(store: SqliteStore) -> None:
    """Verifies REQ-INV-004: a typed-failure held case can be finalized by a current
    authorized review; the audit row keeps ``ai_verdict=None`` and the failure code, and
    carries a ``reviewer:<id>`` actor with no ``ai:`` actor."""
    snapshot = make_snapshot()
    case = make_case(
        advisory=None,
        snapshot=snapshot,
        status=CaseStatus.HELD,
        analysis_failure_code=FailureCode.TIMEOUT,
    )
    _seed_reviewable_case(
        store,
        case,
        snapshot=snapshot,
        queue_outcome="hold",
        reason_id="FB-ANALYSIS-TIMEOUT",
    )
    engine = PolicyEngine(snapshot)
    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        review=_review(outcome=Outcome.REJECT, case=case, snapshot=snapshot),
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="moderator-1", idempotency_key="idem-fail-review"),
    )
    assert result.status is CommitStatus.COMMITTED
    assert result.audit_id is not None
    with store.read_connection() as conn:
        record = AuditRepository.read(conn, result.audit_id)
        unresolved = QueueRepository.count(conn)
    assert record.outcome == Outcome.REJECT.value
    assert record.ai_verdict is None
    assert record.analysis_failure_code == FailureCode.TIMEOUT.value
    assert "reviewer:moderator-1" in record.actor_ids
    assert not any(a.startswith("ai:") for a in record.actor_ids)
    assert unresolved == 0


def _held_reviewable(store: SqliteStore) -> tuple[PolicySnapshot, CaseSnapshot]:
    """Seed a HELD case (and its queue entry) for review-rejection tests."""
    snapshot = make_snapshot()
    case = make_case(
        advisory=_advisory(verdict=Verdict.REVIEW, severity=Severity.MEDIUM),
        snapshot=snapshot,
        status=CaseStatus.HELD,
    )
    _seed_reviewable_case(
        store, case, snapshot=snapshot, queue_outcome="hold", reason_id="RULE-REVIEW"
    )
    return snapshot, case


@pytest.mark.parametrize("stale_field", ["case_id", "revision", "content_hash"])
def test_stale_review_cannot_finalize(store: SqliteStore, stale_field: str) -> None:
    """Verifies REQ-INV-003/004 (negative): a stale review (wrong case id / revision /
    content hash) is rejected with ``StaleReviewError``; through the commit path it
    returns FAILED with no state change."""
    snapshot, case = _held_reviewable(store)
    engine = PolicyEngine(snapshot)
    if stale_field == "case_id":
        stale = _review(
            outcome=Outcome.APPROVE, case=case, snapshot=snapshot, case_id="case-other"
        )
    elif stale_field == "revision":
        stale = _review(
            outcome=Outcome.APPROVE, case=case, snapshot=snapshot, revision=99
        )
    else:
        stale = _review(
            outcome=Outcome.APPROVE, case=case, snapshot=snapshot, content_hash="c" * 64
        )
    with pytest.raises(StaleReviewError):
        engine.evaluate(case=case, content_text="benign text", review=stale)

    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        review=stale,
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="moderator-1", idempotency_key="idem-stale"),
    )
    assert result.status is CommitStatus.FAILED
    assert _audit_count(store) == 0
    _rev, status = _case_row(store, case.case_id)
    assert status == CaseStatus.HELD.value


@pytest.mark.parametrize(
    "reviewer_role,rationale",
    [("submitter", "ok decision")],
)
def test_unauthorized_review_cannot_finalize(
    store: SqliteStore, reviewer_role: str, rationale: str
) -> None:
    """Verifies REQ-INV-003/004 (negative): a non-moderator review is rejected with
    ``UnauthorizedReviewError``; through commit it returns FAILED with no state change.

    An empty rationale is rejected earlier by ``ReviewRequest`` construction (the contract
    is stricter than the engine), so only the role check reaches the engine here."""
    snapshot = make_snapshot()
    case = make_case(
        advisory=_advisory(verdict=Verdict.REVIEW, severity=Severity.MEDIUM),
        snapshot=snapshot,
        status=CaseStatus.HELD,
    )
    _seed_reviewable_case(
        store, case, snapshot=snapshot, queue_outcome="hold", reason_id="RULE-REVIEW"
    )
    engine = PolicyEngine(snapshot)
    bad = _review(
        outcome=Outcome.APPROVE,
        case=case,
        snapshot=snapshot,
        reviewer_role=reviewer_role,
        rationale=rationale,
    )
    with pytest.raises(UnauthorizedReviewError):
        engine.evaluate(case=case, content_text="benign text", review=bad)

    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        review=bad,
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="moderator-1", idempotency_key="idem-unauth"),
    )
    assert result.status is CommitStatus.FAILED
    assert _audit_count(store) == 0
    _rev, status = _case_row(store, case.case_id)
    assert status == CaseStatus.HELD.value


def test_old_case_review_uses_pinned_snapshot(store: SqliteStore) -> None:
    """Verifies REQ-INV-003/004: after activating snapshot v2, a review of a case pinned to
    v1 loads v1 via ``SnapshotStore.load`` and commits with the v1 reason and snapshot
    identifiers — it does not fail because v2 is globally active."""
    v1 = make_snapshot()
    case = make_case(
        advisory=_advisory(verdict=Verdict.REVIEW, severity=Severity.MEDIUM),
        snapshot=v1,
        status=CaseStatus.HELD,
    )
    _seed_reviewable_case(
        store, case, snapshot=v1, queue_outcome="hold", reason_id="RULE-REVIEW"
    )
    with store.transaction() as conn:
        store.activate_snapshot(conn, make_snapshot_v2())
    engine = PolicyEngine(make_snapshot_v2())
    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        review=_review(outcome=Outcome.APPROVE, case=case, snapshot=v1),
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="moderator-1", idempotency_key="idem-old"),
    )
    assert result.status is CommitStatus.COMMITTED
    assert result.audit_id is not None
    with store.read_connection() as conn:
        record = AuditRepository.read(conn, result.audit_id)
    assert record.policy_snapshot_id == v1.snapshot_id
    assert record.policy_snapshot_digest == v1.digest
    assert record.policy_reason_id == "RULE-HUMAN-REVIEW"
    assert _audit_count(store) == 1


def test_review_replay_is_idempotent(store: SqliteStore) -> None:
    """Verifies REQ-INV-004: repeating a review commit (same replay key + same review)
    returns the same audit id and exactly one audit row; a different review under the same
    replay key is a CONFLICT."""
    snapshot = make_snapshot()
    case = make_case(
        advisory=_advisory(verdict=Verdict.REVIEW, severity=Severity.MEDIUM),
        snapshot=snapshot,
        status=CaseStatus.HELD,
    )
    _seed_reviewable_case(
        store, case, snapshot=snapshot, queue_outcome="hold", reason_id="RULE-REVIEW"
    )
    engine = PolicyEngine(snapshot)
    key = ReplayKey(actor_id="moderator-1", idempotency_key="idem-review-replay")
    review = _review(outcome=Outcome.APPROVE, case=case, snapshot=snapshot)

    first = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        review=review,
        expected_revision=case.revision,
        replay_key=key,
    )
    retry = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        review=review,
        expected_revision=case.revision,
        replay_key=key,
    )
    assert first.status is CommitStatus.COMMITTED
    assert retry.status is CommitStatus.COMMITTED
    assert retry.audit_id == first.audit_id
    assert _audit_count(store) == 1

    conflict = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        review=_review(outcome=Outcome.REJECT, case=case, snapshot=snapshot),
        expected_revision=case.revision,
        replay_key=key,
    )
    assert conflict.status is CommitStatus.CONFLICT
    assert _audit_count(store) == 1
