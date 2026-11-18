"""Escalation-routing tests (REQ-INV-003) — engine + commit/queue.

Verifies REQ-INV-003: high-severity content can never reach a final disposition without
human review; the effective severity uses an explicit rank (never string ordering); and a
held/escalated case reaches a final disposition **only** through a current authorized
human review (S1 plan §3.5 step 7), which resolves the queue entry atomically.

Slice A asserts engine-produced decisions (no DB). Slice C (CP4) adds the commit/queue
matrix and the reviewed-finalisation path against real SQLite (``tmp_path``).
"""

from __future__ import annotations

import itertools

import pytest
from conftest import CONTENT_HASH, make_case, make_snapshot

from contentguard.escalation.repository import QueueRepository
from contentguard.policy.contracts import (
    ActorRef,
    AdvisoryResult,
    CaseStatus,
    CommitStatus,
    Outcome,
    ReplayKey,
    ReviewRequest,
    Severity,
    Verdict,
)
from contentguard.policy.engine import PolicyEngine
from contentguard.policy.snapshot import PolicySnapshot
from contentguard.policy.store import SqliteStore


def _review(
    *,
    outcome: Outcome,
    case_id: str = "case-1",
    revision: int = 1,
    snapshot: PolicySnapshot | None = None,
    reviewer_role: str = "moderator",
    rationale: str = "manual moderator decision",
    content_hash: str = CONTENT_HASH,
) -> ReviewRequest:
    snap = snapshot or make_snapshot()
    return ReviewRequest(
        reviewer=ActorRef(actor_id="moderator-1", role=reviewer_role),
        case_id=case_id,
        expected_revision=revision,
        requested_outcome=outcome,
        rationale=rationale,
        policy_snapshot_id=snap.snapshot_id,
        policy_snapshot_digest=snap.digest,
        content_hash=content_hash,
    )


def _advisory(*, verdict: Verdict, severity: Severity) -> AdvisoryResult:
    return AdvisoryResult.from_payload(
        {
            "role": "initial_review",
            "verdict": verdict.value,
            "severity": severity.value,
            "rationale": "model rationale",
            "citations": ("clause-001",),
            "prompt_version": "prompt-v1",
            "model_id": "model-x",
            "model_version": "2026-11",
            "usage": {"input_tokens": 10, "output_tokens": 5, "usage_unknown": False},
        }
    )


@pytest.mark.parametrize(
    "ai_verdict,ai_severity,use_high_prefilter",
    [
        (verdict, severity, high)
        for verdict, severity, high in itertools.product(
            [Verdict.ALLOW, Verdict.REVIEW, Verdict.VIOLATE],
            [Severity.HIGH],
            [False, True],
        )
    ],
)
def test_high_severity_always_escalates(
    snapshot_v1: PolicySnapshot,
    snapshot_with_reject_rule: PolicySnapshot,
    ai_verdict: Verdict,
    ai_severity: Severity,
    use_high_prefilter: bool,
) -> None:
    """Verifies REQ-INV-003: any AI-high case escalates regardless of verdict/rule set.

    No allow rule and no advisory ``ALLOW`` can produce a final disposition before a
    valid human review; the outcome is always ``ESCALATE`` with human review required.
    """
    text = "dangerous threat here" if use_high_prefilter else "benign text"
    for snapshot in (snapshot_v1, snapshot_with_reject_rule):
        engine = PolicyEngine(snapshot)
        decision = engine.evaluate(
            case=make_case(
                advisory=_advisory(verdict=ai_verdict, severity=ai_severity),
                snapshot=snapshot,
            ),
            content_text=text,
        )
        assert decision.outcome == Outcome.ESCALATE
        assert decision.requires_human_review is True


@pytest.mark.parametrize("high_prefilter", [False, True])
def test_high_severity_prefilter_only_escalates(
    snapshot_v1: PolicySnapshot,
    high_prefilter: bool,
) -> None:
    """Verifies REQ-INV-003: the deterministic prefilter alone can force escalation.

    A low AI severity plus a high prefilter term still escalates (effective severity is
    the maximum by rank), and a low AI severity with no prefilter hit does not.
    """
    engine = PolicyEngine(snapshot_v1)
    text = "dangerous threat here" if high_prefilter else "benign text"
    decision = engine.evaluate(
        case=make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW)),
        content_text=text,
    )
    if high_prefilter:
        assert decision.outcome == Outcome.ESCALATE
        assert decision.requires_human_review is True
    else:
        assert decision.outcome == Outcome.APPROVE
        assert decision.requires_human_review is False


def test_severity_rank_edges(snapshot_v1: PolicySnapshot) -> None:
    """Verifies REQ-INV-003: explicit severity rank defeats lexical string ordering.

    AI-high + prefilter-low and prefilter-high + advisory-medium both resolve to HIGH.
    A ``max()`` over string values would pick ``"low"``/``"medium"`` over ``"high"`` and
    silently invert the invariant.
    """
    engine = PolicyEngine(snapshot_v1)

    ai_high_prefilter_low = engine.evaluate(
        case=make_case(advisory=_advisory(verdict=Verdict.VIOLATE, severity=Severity.HIGH)),
        content_text="benign text",
    )
    assert ai_high_prefilter_low.severity == Severity.HIGH
    assert ai_high_prefilter_low.outcome == Outcome.ESCALATE

    prefilter_high_advisory_medium = engine.evaluate(
        case=make_case(advisory=_advisory(verdict=Verdict.REVIEW, severity=Severity.MEDIUM)),
        content_text="dangerous threat here",
    )
    assert prefilter_high_advisory_medium.severity == Severity.HIGH
    assert prefilter_high_advisory_medium.outcome == Outcome.ESCALATE


def test_effective_severity_uses_rank_not_string() -> None:
    """Verifies REQ-INV-003: ``effective_severity`` returns HIGH over LOW/MEDIUM.

    Guards directly against ``"low" > "high"`` lexical inversion.
    """
    from contentguard.policy.contracts import effective_severity

    assert effective_severity(Severity.HIGH, Severity.LOW) == Severity.HIGH
    assert effective_severity(Severity.MEDIUM, Severity.HIGH) == Severity.HIGH
    assert effective_severity(Severity.LOW, None) == Severity.LOW
    assert effective_severity(None, None) is None


# --- Slice C (CP4): commit/queue matrix + reviewed finalisation ---------------------


@pytest.fixture()
def store(tmp_path: object) -> SqliteStore:
    """A fresh file-backed SQLite store with schemas created."""
    sqlite_store = SqliteStore(f"{tmp_path}/cases.db")
    sqlite_store.initialize()
    return sqlite_store


def _seed_held_case(
    store: SqliteStore,
    case: object,
    *,
    snapshot: PolicySnapshot,
    queue_revision: int,
    queue_outcome: str,
    reason_id: str,
) -> None:
    """Insert a case row (its current status) and its unresolved queue entry."""
    from contentguard.policy.contracts import CaseSnapshot

    assert isinstance(case, CaseSnapshot)
    with store.transaction() as conn:
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
        from contentguard.escalation.contracts import QueueEntry

        QueueRepository.enqueue(
            conn,
            QueueEntry(
                case_id=case.case_id,
                case_revision=queue_revision,
                outcome=queue_outcome,
                reason_id=reason_id,
                enqueued_at="2026-11-18T00:00:00+00:00",
            ),
        )


def _queue_unresolved(store: SqliteStore) -> int:
    with store.read_connection() as conn:
        return QueueRepository.count(conn)


@pytest.mark.parametrize(
    "ai_verdict,use_high_prefilter",
    list(itertools.product([Verdict.ALLOW, Verdict.REVIEW, Verdict.VIOLATE], [False, True])),
)
def test_high_severity_matrix_commit_escalates_and_enqueues(
    store: SqliteStore,
    ai_verdict: Verdict,
    use_high_prefilter: bool,
    snapshot_with_reject_rule: PolicySnapshot,
) -> None:
    """Verifies REQ-INV-003 (commit/queue matrix): an AI-high or prefilter-high case is
    committed as a non-final ESCALATE and enqueued for review — it never commits a final
    disposition regardless of verdict or rule set."""
    snapshot = snapshot_with_reject_rule
    text = "dangerous threat here" if use_high_prefilter else "benign text"
    case = make_case(
        advisory=_advisory(verdict=ai_verdict, severity=Severity.HIGH),
        snapshot=snapshot,
    )
    with store.transaction() as conn:
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
                case.advisory_model_id, case.advisory_model_version, None,
                "2026-11-18T00:00:00+00:00",
            ),
        )
    engine = PolicyEngine(snapshot)
    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text=text,
        advisory=None,
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="submitter-1", idempotency_key="idem-hi"),
    )
    assert result.status is CommitStatus.COMMITTED
    with store.read_connection() as conn:
        row = conn.execute(
            "SELECT status FROM cases WHERE case_id = ?", (case.case_id,)
        ).fetchone()
    assert row[0] == CaseStatus.ESCALATED.value
    assert _queue_unresolved(store) == 1


@pytest.mark.parametrize("requested", [Outcome.APPROVE, Outcome.REJECT])
@pytest.mark.parametrize("case_status", [CaseStatus.ESCALATED, CaseStatus.HELD])
def test_review_finalizes_held_case_and_resolves_queue(
    store: SqliteStore,
    requested: Outcome,
    case_status: CaseStatus,
) -> None:
    """Verifies REQ-INV-003/004: a current authorized review of a HELD/ESCALATED case
    commits the reviewed final disposition and resolves the queue entry in the same
    transaction (queue count drops to zero)."""
    snapshot = make_snapshot()
    case = make_case(
        advisory=_advisory(verdict=Verdict.REVIEW, severity=Severity.MEDIUM),
        snapshot=snapshot,
        status=case_status,
    )
    _seed_held_case(
        store,
        case,
        snapshot=snapshot,
        queue_revision=case.revision,
        queue_outcome=(
            "hold" if case_status is CaseStatus.HELD else "escalate"
        ),
        reason_id="RULE-REVIEW",
    )
    engine = PolicyEngine(snapshot)
    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        review=_review(outcome=requested, revision=case.revision),
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="moderator-1", idempotency_key="idem-review"),
    )
    assert result.status is CommitStatus.COMMITTED
    expected_status = (
        CaseStatus.APPROVED if requested is Outcome.APPROVE else CaseStatus.REJECTED
    )
    with store.read_connection() as conn:
        row = conn.execute(
            "SELECT status FROM cases WHERE case_id = ?", (case.case_id,)
        ).fetchone()
    assert row[0] == expected_status.value
    assert _queue_unresolved(store) == 0


def test_high_severity_case_review_can_finalize(store: SqliteStore) -> None:
    """Verifies REQ-INV-003: a case escalated by high severity reaches a final disposition
    only through a current authorized review (step 7), which resolves the queue entry."""
    snapshot = make_snapshot()
    case = make_case(
        advisory=_advisory(verdict=Verdict.VIOLATE, severity=Severity.HIGH),
        snapshot=snapshot,
        status=CaseStatus.ESCALATED,
    )
    _seed_held_case(
        store,
        case,
        snapshot=snapshot,
        queue_revision=case.revision,
        queue_outcome="escalate",
        reason_id="RULE-HIGH-SEVERITY",
    )
    engine = PolicyEngine(snapshot)
    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        review=_review(outcome=Outcome.REJECT, revision=case.revision),
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="moderator-1", idempotency_key="idem-hi-review"),
    )
    assert result.status is CommitStatus.COMMITTED
    with store.read_connection() as conn:
        row = conn.execute(
            "SELECT status FROM cases WHERE case_id = ?", (case.case_id,)
        ).fetchone()
    assert row[0] == CaseStatus.REJECTED.value
    assert _queue_unresolved(store) == 0


def test_reject_floor_overrides_review_approve(snapshot_with_reject_rule: PolicySnapshot) -> None:
    """Verifies REQ-INV-003: the mandatory REJECT floor wins over a reviewed APPROVE.

    A snapshot with an earlier matching APPROVE rule and a later matching REJECT rule
    still rejects on a review; the reason is the REJECT rule id, never
    ``RULE-HUMAN-REVIEW`` or the earlier allow.
    """
    snapshot = snapshot_with_reject_rule
    engine = PolicyEngine(snapshot)
    case = make_case(
        advisory=_advisory(verdict=Verdict.VIOLATE, severity=Severity.LOW),
        snapshot=snapshot,
        status=CaseStatus.HELD,
    )
    decision = engine.evaluate(
        case=case,
        content_text="benign text",
        review=_review(outcome=Outcome.APPROVE, snapshot=snapshot, revision=case.revision),
    )
    assert decision.outcome is Outcome.REJECT
    assert decision.reason_id == "RULE-REJECT-VIOLATE"
