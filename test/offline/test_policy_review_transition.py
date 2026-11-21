"""Review-transition tests for ``PolicyEngine.review_and_commit`` (ADR-002).

Verifies REQ-FUN-003 / REQ-INV-003 against the ADR-002 acceptance matrix
(docs/architecture/adr/002-human-review-transition-precommit-validation.md,
"Implementation slice — acceptance matrix"):

- G1 prohibited approve (mandatory-rule violation) raises ``MandatoryRuleViolation``
  with ZERO writes (case revision/status, queue depth, audit row count, replay records
  all unchanged);
- G2 a permitted requested REJECT commits exactly once (case + audit + queue + replay
  land together);
- G3 a valid high-severity review commits whenever the mandatory rules permit them
  (the floor's low/medium severity condition does not match at eff_severity=HIGH);
- G4 stale or unauthorized review evidence is a typed validation failure without a
  commit;
- G5 a duplicate replay (same key, same payload) reconciles the stored result; a
  conflicting replay (same key, different payload) is a CONFLICT;
- G6 an injected persistence failure rolls back with no partial state.

Deterministic and offline: no network, no API key, no model access.
"""

from __future__ import annotations

import pytest
from conftest import CONTENT_HASH, make_case, make_snapshot

import contentguard.policy.engine as engine_module
from contentguard.audit.errors import AuditValidationError
from contentguard.escalation.repository import QueueRepository
from contentguard.policy.contracts import (
    ActorRef,
    AdvisoryResult,
    CaseSnapshot,
    CaseStatus,
    CommitResult,
    CommitStatus,
    FailureCode,
    Outcome,
    PolicyDecision,
    ReplayKey,
    ReviewRequest,
)
from contentguard.policy.engine import PolicyEngine
from contentguard.policy.errors import MandatoryRuleViolation
from contentguard.policy.snapshot import PolicySnapshot
from contentguard.policy.store import SqliteStore


@pytest.fixture()
def store(tmp_path: object) -> SqliteStore:
    """A fresh file-backed SQLite store with schemas created."""
    sqlite_store = SqliteStore(f"{tmp_path}/cases.db")
    sqlite_store.initialize()
    return sqlite_store


def _review(
    *,
    outcome: Outcome,
    case_id: str = "case-1",
    revision: int = 1,
    snapshot: PolicySnapshot | None = None,
    reviewer_id: str = "moderator-1",
    reviewer_role: str = "moderator",
    rationale: str = "manual moderator decision",
    content_hash: str = CONTENT_HASH,
) -> ReviewRequest:
    snap = snapshot or make_snapshot()
    return ReviewRequest(
        reviewer=ActorRef(actor_id=reviewer_id, role=reviewer_role),
        case_id=case_id,
        expected_revision=revision,
        requested_outcome=outcome,
        rationale=rationale,
        policy_snapshot_id=snap.snapshot_id,
        policy_snapshot_digest=snap.digest,
        content_hash=content_hash,
    )


def _seed_escalated_case(
    store: SqliteStore,
    case: CaseSnapshot,
    *,
    snapshot: PolicySnapshot,
) -> None:
    """Insert an escalated case row carrying its pinned advisory evidence and an open
    escalation queue entry (the state a reviewable case has before the transition)."""
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT 1 FROM policy_snapshots WHERE snapshot_id = ?",
            (snapshot.snapshot_id,),
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
                "seeded content",
                case.advisory_verdict.value if case.advisory_verdict else None,
                case.advisory_severity.value if case.advisory_severity else None,
                case.advisory_model_id,
                case.advisory_model_version,
                case.analysis_failure_code.value if case.analysis_failure_code else None,
                "2026-11-18T00:00:00+00:00",
            ),
        )
        from contentguard.escalation.contracts import QueueEntry

        QueueRepository.enqueue(
            conn,
            QueueEntry(
                case_id=case.case_id,
                case_revision=case.revision,
                outcome="escalate",
                reason_id="RULE-HIGH-SEVERITY",
                enqueued_at="2026-11-18T00:00:00+00:00",
            ),
        )


def _counts(store: SqliteStore) -> tuple[int, int, int]:
    """Return (audit row count, open queue depth, replay record count)."""
    with store.read_connection() as conn:
        audit = conn.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0]
        queue = QueueRepository.count(conn)
        replay = conn.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
    return int(audit), int(queue), int(replay)


def _case_row(store: SqliteStore, case_id: str) -> tuple[int, str]:
    with store.read_connection() as conn:
        row = conn.execute(
            "SELECT revision, status FROM cases WHERE case_id = ?", (case_id,)
        ).fetchone()
    assert row is not None
    return int(row[0]), str(row[1])


def _escalated_case(
    snapshot: PolicySnapshot,
    advisory: AdvisoryResult | None = None,
    *,
    case_id: str = "case-1",
    analysis_failure_code: FailureCode | None = None,
) -> CaseSnapshot:
    return make_case(
        case_id=case_id,
        revision=1,
        status=CaseStatus.ESCALATED,
        advisory=advisory,
        snapshot=snapshot,
        analysis_failure_code=analysis_failure_code,
    )


def _call(
    engine: PolicyEngine,
    store: SqliteStore,
    case: CaseSnapshot,
    review: ReviewRequest,
    *,
    content_text: str = "benign text",
    key: str = "idem-review-1",
    replay_actor: str | None = None,
) -> CommitResult:
    return engine.review_and_commit(
        store=store,
        case=case,
        content_text=content_text,
        review=review,
        expected_revision=case.revision,
        replay_key=ReplayKey(
            actor_id=replay_actor if replay_actor is not None else review.reviewer.actor_id,
            idempotency_key=key,
        ),
    )


# --- G1: prohibited approve -> MandatoryRuleViolation, ZERO writes --------------------


def test_g1_prohibited_approve_raises_with_zero_writes(
    store: SqliteStore,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> None:
    """G1 (ADR-002 matrix, REQ-FUN-003/REQ-INV-003): a requested APPROVE that the first
    matching mandatory REJECT rule would override is refused with zero writes.

    The case carries pinned advisory evidence (violate/medium) and the review content
    has no high-severity term, so eff_severity=MEDIUM matches the floor's
    violate+low/medium condition. Nothing may be written: case revision/status, queue
    depth, audit row count and replay records all stay unchanged (ADR-002 decision
    step 3: "no write of any kind").
    """
    snap = snapshot_with_reject_rule
    case = _escalated_case(snap, advisory_medium)
    _seed_escalated_case(store, case, snapshot=snap)
    engine = PolicyEngine(snap)
    review = _review(outcome=Outcome.APPROVE, snapshot=snap)
    before_counts = _counts(store)
    before_row = _case_row(store, case.case_id)

    with pytest.raises(MandatoryRuleViolation) as exc_info:
        _call(engine, store, case, review)

    assert exc_info.value.code == "MANDATORY_RULE_VIOLATION"
    assert _counts(store) == before_counts
    assert _case_row(store, case.case_id) == before_row


def test_g1_typed_failure_case_has_no_verdict_conditioned_floor(
    store: SqliteStore,
    snapshot_with_reject_rule: PolicySnapshot,
) -> None:
    """G1 boundary (ADR-002 matrix, REQ-FUN-003/REQ-INV-003): a typed-failure escalated case has no
    pinned verdict, so verdict-conditioned mandatory REJECT rules never match and the
    requested APPROVE is NOT a mandatory-rule refusal — the transition commits through
    the normal review path (the same matching inputs ``_build_review_decision`` uses)."""
    snap = snapshot_with_reject_rule
    case = _escalated_case(
        snap,
        case_id="case-typed",
        analysis_failure_code=FailureCode.PROVIDER_UNAVAILABLE,
    )
    _seed_escalated_case(store, case, snapshot=snap)
    engine = PolicyEngine(snap)
    review = _review(outcome=Outcome.APPROVE, case_id="case-typed", snapshot=snap)

    result = _call(engine, store, case, review)

    assert result.status == CommitStatus.COMMITTED
    assert _case_row(store, case.case_id) == (2, "approved")


# --- G2: permitted reject -> exactly one atomic commit --------------------------------


def test_g2_permitted_reject_commits_exactly_once(
    store: SqliteStore,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> None:
    """G2 (ADR-002 matrix, REQ-FUN-003/REQ-INV-003): a requested REJECT is permitted even against a
    mandatory REJECT floor (floor and request agree) and commits exactly once — case
    row, audit entry, queue resolution and replay record land together."""
    snap = snapshot_with_reject_rule
    case = _escalated_case(snap, advisory_medium)
    _seed_escalated_case(store, case, snapshot=snap)
    engine = PolicyEngine(snap)
    review = _review(outcome=Outcome.REJECT, snapshot=snap)

    result = _call(engine, store, case, review)

    assert result.status == CommitStatus.COMMITTED
    assert result.case_revision == 2
    assert result.audit_id is not None
    assert _case_row(store, case.case_id) == (2, "rejected")
    audit_count, queue_depth, replay_count = _counts(store)
    assert audit_count == 1
    assert replay_count == 1
    assert queue_depth == 0  # the open escalation entry was resolved atomically


# --- G3: valid high-severity review commits -------------------------------------------


def test_g3_high_severity_review_commits_when_permitted(
    store: SqliteStore,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> None:
    """G3 (ADR-002 matrix, REQ-FUN-003/REQ-INV-003): authorized high-severity reviews remain
    possible whenever the mandatory rules permit them. The floor rule's low/medium
    severity condition does not match at eff_severity=HIGH (prefilter high + advisory
    medium), so the requested APPROVE is not a violation and commits."""
    snap = snapshot_with_reject_rule
    case = _escalated_case(snap, advisory_medium)
    _seed_escalated_case(store, case, snapshot=snap)
    engine = PolicyEngine(snap)
    review = _review(outcome=Outcome.APPROVE, snapshot=snap)

    result = _call(engine, store, case, review, content_text="dangerous threat here")

    assert result.status == CommitStatus.COMMITTED
    assert result.case_revision == 2
    assert _case_row(store, case.case_id) == (2, "approved")


# --- G4: stale/unauthorized -> typed failure without commit ---------------------------


def test_g4_stale_review_conflicts_without_commit(
    store: SqliteStore,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> None:
    """G4 (ADR-002 matrix, REQ-FUN-003/REQ-INV-003): stale review evidence (content hash no longer
    matching the case) is a typed validation failure without commit (same
    ``_validate_review`` behaviour the evaluate path applies)."""
    snap = snapshot_with_reject_rule
    case = _escalated_case(snap, advisory_medium)
    _seed_escalated_case(store, case, snapshot=snap)
    engine = PolicyEngine(snap)
    review = _review(outcome=Outcome.REJECT, snapshot=snap, content_hash="c" * 64)
    before_counts = _counts(store)
    before_row = _case_row(store, case.case_id)

    result = _call(engine, store, case, review)

    assert result.status == CommitStatus.CONFLICT
    assert result.audit_id is None
    assert _counts(store) == before_counts
    assert _case_row(store, case.case_id) == before_row


def test_g4_unauthorized_review_fails_without_commit(
    store: SqliteStore,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> None:
    """G4 (ADR-002 matrix, REQ-FUN-003/REQ-INV-003): a non-moderator reviewer is a typed validation
    failure without commit (unauthorized evidence never reaches the mandatory-rule
    stage)."""
    snap = snapshot_with_reject_rule
    case = _escalated_case(snap, advisory_medium)
    _seed_escalated_case(store, case, snapshot=snap)
    engine = PolicyEngine(snap)
    review = _review(outcome=Outcome.REJECT, snapshot=snap, reviewer_role="submitter")
    before_counts = _counts(store)
    before_row = _case_row(store, case.case_id)

    result = _call(engine, store, case, review)

    assert result.status == CommitStatus.FAILED
    assert result.audit_id is None
    assert _counts(store) == before_counts
    assert _case_row(store, case.case_id) == before_row


# --- G5: replay reconcile vs conflict --------------------------------------------------


def test_g5_same_key_same_payload_reconciles_stored_result(
    store: SqliteStore,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> None:
    """G5 (ADR-002 matrix, REQ-FUN-003/REQ-INV-003, replay ordering 1): a same-key/
    same-payload retry after the
    commit returns the stored result — not a spurious CONFLICT — and writes nothing
    new (the replay check precedes the revision/status precondition, and the candidate
    is re-evaluated under the neutral reviewable status)."""
    snap = snapshot_with_reject_rule
    case = _escalated_case(snap, advisory_medium)
    _seed_escalated_case(store, case, snapshot=snap)
    engine = PolicyEngine(snap)
    review = _review(outcome=Outcome.REJECT, snapshot=snap)

    first = _call(engine, store, case, review)
    assert first.status == CommitStatus.COMMITTED
    counts_after_first = _counts(store)

    retry = _call(engine, store, case, review)

    assert retry.status == CommitStatus.COMMITTED
    assert retry.decision_id == first.decision_id
    assert retry.audit_id == first.audit_id
    assert retry.case_revision == first.case_revision
    assert _counts(store) == counts_after_first  # reconciled, no new writes


def test_g5_same_key_different_payload_conflicts(
    store: SqliteStore,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> None:
    """G5 (ADR-002 matrix, REQ-FUN-003/REQ-INV-003, replay ordering 1): a same-key/
    different-payload retry is a
    CONFLICT (a different reviewer changes ``actor_ids``, so the candidate payload hash
    differs from the stored one) and writes nothing."""
    snap = snapshot_with_reject_rule
    case = _escalated_case(snap, advisory_medium)
    _seed_escalated_case(store, case, snapshot=snap)
    engine = PolicyEngine(snap)
    review = _review(outcome=Outcome.REJECT, snapshot=snap)

    first = _call(engine, store, case, review, key="idem-shared", replay_actor="moderator-1")
    assert first.status == CommitStatus.COMMITTED
    counts_after_first = _counts(store)

    other_review = _review(outcome=Outcome.REJECT, snapshot=snap, reviewer_id="moderator-2")
    retry = _call(
        engine,
        store,
        case,
        other_review,
        key="idem-shared",
        replay_actor="moderator-1",
    )

    assert retry.status == CommitStatus.CONFLICT
    assert retry.audit_id is None
    assert _counts(store) == counts_after_first


# --- G6: injected persistence failure -> rollback, no partial state --------------------


def test_g6_injected_persistence_failure_rolls_back(
    store: SqliteStore,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G6 (ADR-002 matrix, REQ-FUN-003/REQ-INV-003, replay ordering 5): an injected
    persistence failure inside
    the atomic commit machinery rolls the transaction back — no partial state: case
    row, audit, queue and replay records all stay unchanged and the result is a typed
    FAILED, not an exception."""

    real_authority_cls = engine_module.EnforcementAuthority

    class _ExplodingAuthority:
        def __init__(self, s: SqliteStore) -> None:
            def _explode(decision: PolicyDecision) -> dict[str, object]:
                raise AuditValidationError("injected persistence failure")

            self._real = real_authority_cls(s, audit_record_factory=_explode)

        def commit(
            self,
            decision: PolicyDecision,
            *,
            expected_revision: int,
            replay_key: ReplayKey,
        ) -> CommitResult:
            return self._real.commit(
                decision, expected_revision=expected_revision, replay_key=replay_key
            )

    monkeypatch.setattr(engine_module, "EnforcementAuthority", _ExplodingAuthority)

    snap = snapshot_with_reject_rule
    case = _escalated_case(snap, advisory_medium)
    _seed_escalated_case(store, case, snapshot=snap)
    engine = PolicyEngine(snap)
    review = _review(outcome=Outcome.REJECT, snapshot=snap)
    before_counts = _counts(store)
    before_row = _case_row(store, case.case_id)

    result = _call(engine, store, case, review)

    assert result.status == CommitStatus.FAILED
    assert result.audit_id is None
    assert _counts(store) == before_counts
    assert _case_row(store, case.case_id) == before_row
