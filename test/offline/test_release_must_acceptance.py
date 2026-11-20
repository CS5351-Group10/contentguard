"""Release-acceptance Must flows across the currently merged components.

End-to-end acceptance flows available on the current baseline: a normal decision is
committed with a resolvable audit record, an analysis failure reaches a durable hold and
finalizes only through an authorized review, and decision attribution stays pinned after
a policy snapshot change.

S2/S3-dependent integration steps (intake, analysis, retrieval, API) are deferred until
those branches merge. Deterministic and offline.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import make_case

from contentguard.audit.repository import AuditRepository
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
from contentguard.policy.snapshot import PolicySnapshot
from contentguard.policy.store import SqliteStore

_UPDATED_AT = "2026-11-18T12:00:00+00:00"


def _advisory(*, verdict: Verdict, severity: Severity) -> AdvisoryResult:
    return AdvisoryResult.from_payload(
        {
            "role": "initial_review",
            "verdict": verdict.value,
            "severity": severity.value,
            "rationale": "Acceptance fixture rationale.",
            "citations": ("clause-001",),
            "prompt_version": "prompt-v1",
            "model_id": "model-x",
            "model_version": "2026-11",
            "usage": {
                "input_tokens": 120,
                "output_tokens": 40,
                "usage_unknown": False,
            },
        }
    )


@pytest.fixture()
def store(tmp_path: Path) -> SqliteStore:
    instance = SqliteStore(tmp_path / "release-must.db")
    instance.initialize()
    return instance


def _seed_case(
    store: SqliteStore, case: CaseSnapshot, snapshot: PolicySnapshot
) -> None:
    with store.transaction() as conn:
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
                "acceptance fixture content",
                case.advisory_verdict.value
                if case.advisory_verdict is not None
                else None,
                case.advisory_severity.value
                if case.advisory_severity is not None
                else None,
                case.advisory_model_id,
                case.advisory_model_version,
                case.analysis_failure_code.value
                if case.analysis_failure_code is not None
                else None,
                _UPDATED_AT,
            ),
        )


def _audit_count(store: SqliteStore) -> int:
    with store.read_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM audit_records").fetchone()
    assert row is not None
    return int(row[0])


def _case_row(store: SqliteStore, case_id: str) -> tuple[int, str, str]:
    with store.read_connection() as conn:
        row = conn.execute(
            "SELECT revision, status, policy_snapshot_id FROM cases WHERE case_id = ?",
            (case_id,),
        ).fetchone()
    assert row is not None
    return int(row[0]), str(row[1]), str(row[2])


def _queue_count(store: SqliteStore) -> int:
    with store.read_connection() as conn:
        return QueueRepository.count(conn)


def _read_audit(store: SqliteStore, audit_id: str):
    with store.read_connection() as conn:
        return AuditRepository.read(conn, audit_id)


def test_must_normal_triage_commits_resolvable_audit_and_replays(
    store: SqliteStore, snapshot_v1: PolicySnapshot
) -> None:
    """REQ-FUN-004, REQ-QUA-001, REQ-INV-004: a normal decision is attributable and replayable.

    End-to-end acceptance across policy + audit + escalation: the committed decision
    yields one resolvable audit row with the pinned snapshot and rules, the queue stays
    empty, and the same replay key returns the same audit id without a second row.
    """
    case = make_case(
        advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW),
        snapshot=snapshot_v1,
    )
    _seed_case(store, case, snapshot_v1)
    engine = PolicyEngine(snapshot_v1)
    replay_key = ReplayKey("submitter-1", "must-normal-triage")

    first = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW),
        expected_revision=1,
        replay_key=replay_key,
    )

    assert first.status is CommitStatus.COMMITTED
    assert first.audit_id is not None
    assert _case_row(store, case.case_id)[:2] == (2, CaseStatus.APPROVED.value)
    assert _queue_count(store) == 0

    record = _read_audit(store, first.audit_id)
    assert record.outcome == Outcome.APPROVE.value
    assert record.policy_reason_id == "RULE-ALLOW-LOW"
    assert record.policy_snapshot_id == snapshot_v1.snapshot_id
    assert record.policy_snapshot_digest == snapshot_v1.digest
    assert record.content_hash == case.content_hash
    assert record.ai_verdict == Verdict.ALLOW.value
    assert record.analysis_failure_code is None
    assert "policy" in record.actor_ids
    assert "ai:model-x" in record.actor_ids

    second = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW),
        expected_revision=1,
        replay_key=replay_key,
    )

    assert second.status is CommitStatus.COMMITTED
    assert second.audit_id == first.audit_id
    assert _audit_count(store) == 1


def test_must_analysis_failure_hold_finalizes_only_through_review(
    store: SqliteStore, snapshot_v1: PolicySnapshot
) -> None:
    """REQ-INV-002, REQ-INV-003, REQ-INV-004, REQ-FUN-003, REQ-FUN-004.

    End-to-end acceptance across policy + escalation + audit: a typed analysis failure
    commits to HELD with one queue entry and a failure audit row. Re-evaluation without a
    review is rejected and leaves the held case, unresolved queue entry, and audit count
    unchanged. A current moderator review then produces the only final disposition,
    resolves the queue, and appends the reviewer-attributed audit row.
    """
    case = make_case(advisory=None, snapshot=snapshot_v1)
    _seed_case(store, case, snapshot_v1)
    engine = PolicyEngine(snapshot_v1)

    held = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=AnalysisFailure(
            code=FailureCode.INVALID_RESPONSE, detail="injected invalid response"
        ),
        expected_revision=1,
        replay_key=ReplayKey("submitter-1", "must-failure-hold"),
    )

    assert held.status is CommitStatus.COMMITTED
    assert held.audit_id is not None
    assert _case_row(store, case.case_id)[:2] == (2, CaseStatus.HELD.value)
    assert _queue_count(store) == 1
    held_record = _read_audit(store, held.audit_id)
    assert held_record.outcome == Outcome.HOLD.value
    assert held_record.ai_verdict is None
    assert held_record.analysis_failure_code == FailureCode.INVALID_RESPONSE.value

    unreviewed = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW),
        expected_revision=2,
        replay_key=ReplayKey("submitter-1", "must-failure-unreviewed"),
    )

    assert unreviewed.status is CommitStatus.CONFLICT
    assert unreviewed.audit_id is None
    assert _case_row(store, case.case_id)[:2] == (2, CaseStatus.HELD.value)
    assert _queue_count(store) == 1
    assert _audit_count(store) == 1

    review = ReviewRequest(
        reviewer=ActorRef(actor_id="moderator-1", role="moderator"),
        case_id=case.case_id,
        expected_revision=2,
        requested_outcome=Outcome.APPROVE,
        rationale="Reviewed the failed analysis and approved the content.",
        policy_snapshot_id=case.policy_snapshot_id,
        policy_snapshot_digest=case.policy_snapshot_digest,
        content_hash=case.content_hash,
    )
    finalized = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        review=review,
        expected_revision=2,
        replay_key=ReplayKey("moderator-1", "must-failure-review"),
    )

    assert finalized.status is CommitStatus.COMMITTED
    assert finalized.audit_id is not None
    assert _case_row(store, case.case_id)[:2] == (3, CaseStatus.APPROVED.value)
    assert _queue_count(store) == 0
    assert _audit_count(store) == 2

    final_record = _read_audit(store, finalized.audit_id)
    assert final_record.outcome == Outcome.APPROVE.value
    assert final_record.policy_reason_id == "RULE-HUMAN-REVIEW"
    assert final_record.ai_verdict is None
    assert (
        final_record.analysis_failure_code == FailureCode.INVALID_RESPONSE.value
    )
    assert "reviewer:moderator-1" in final_record.actor_ids
    assert not any(actor.startswith("ai:") for actor in final_record.actor_ids)


def test_must_decision_attribution_survives_a_policy_change(
    store: SqliteStore,
    snapshot_v1: PolicySnapshot,
    snapshot_v2: PolicySnapshot,
) -> None:
    """REQ-FUN-004, REQ-INV-004: an old decision keeps its pinned snapshot and reason.

    End-to-end acceptance across policy + audit: after a new snapshot becomes active, the
    original audit row and the case's pinned snapshot id are unchanged, so historical
    decisions remain attributable to the policy version that produced them.
    """
    case = make_case(
        advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW),
        snapshot=snapshot_v1,
    )
    _seed_case(store, case, snapshot_v1)

    result = PolicyEngine(snapshot_v1).evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW),
        expected_revision=1,
        replay_key=ReplayKey("submitter-1", "must-policy-change"),
    )

    assert result.status is CommitStatus.COMMITTED
    assert result.audit_id is not None
    before = _read_audit(store, result.audit_id)
    assert before.policy_snapshot_id == snapshot_v1.snapshot_id
    assert before.policy_reason_id == "RULE-ALLOW-LOW"

    with store.transaction() as conn:
        store.activate_snapshot(conn, snapshot_v2)

    after = _read_audit(store, result.audit_id)
    assert after == before
    assert _case_row(store, case.case_id)[2] == snapshot_v1.snapshot_id
