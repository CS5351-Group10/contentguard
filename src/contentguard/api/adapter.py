"""S3-to-S1 policy adapter (ADR-001; REQ-FUN-002/004, REQ-INV-001/004).

This module may depend on policy contracts and the engine entry point.  It never
imports enforcement internals and never interprets model output as an action.
"""

from __future__ import annotations

from typing import Any, Protocol

from contentguard.analysis.contracts import (
    AdvisoryResult as AnalysisAdvisory,
)
from contentguard.analysis.contracts import (
    AnalysisFailure,
)
from contentguard.policy.contracts import (
    ActorRef,
    CaseSnapshot,
    CaseStatus,
    CommitResult,
    CommitStatus,
    FailureCode,
    Outcome,
    ReplayKey,
    ReviewRequest,
)
from contentguard.policy.contracts import (
    AdvisoryResult as PolicyAdvisory,
)
from contentguard.policy.contracts import (
    AnalysisFailure as PolicyFailure,
)

from .schemas import CaseView, ProcessingResult, ProcessingStatus


class _PolicyEntryPoint(Protocol):
    def evaluate_and_commit(
        self,
        *,
        store: Any,
        case: CaseSnapshot,
        content_text: str,
        advisory: PolicyAdvisory | PolicyFailure | None,
        review: Any | None,
        expected_revision: int,
        replay_key: ReplayKey,
    ) -> CommitResult: ...

    def review_and_commit(
        self,
        *,
        store: Any,
        case: CaseSnapshot,
        content_text: str,
        review: Any,
        expected_revision: int,
        replay_key: ReplayKey,
    ) -> CommitResult: ...


class PolicyAdapter:
    """Project validated S3 output and invoke the sole policy commit entry point."""

    def __init__(self, engine: _PolicyEntryPoint, *, store: Any | None = None) -> None:
        self._engine = engine
        self._store = store

    def evaluate_and_commit(
        self,
        *,
        store: Any,
        case: CaseSnapshot,
        content_text: str,
        analysis: AnalysisAdvisory | AnalysisFailure,
        expected_revision: int,
        replay_key: ReplayKey,
    ) -> CommitResult:
        """Call ``evaluate_and_commit`` once with a strict immutable policy DTO."""

        if isinstance(analysis, AnalysisAdvisory):
            projected: PolicyAdvisory | PolicyFailure = PolicyAdvisory.from_payload(
                analysis.to_s1_payload()
            )
        else:
            projected = PolicyFailure(
                code=FailureCode(analysis.code),
                detail=analysis.detail,
            )
        return self._engine.evaluate_and_commit(
            store=store,
            case=case,
            content_text=content_text,
            advisory=projected,
            review=None,
            expected_revision=expected_revision,
            replay_key=replay_key,
        )

    def review_and_commit(
        self,
        *,
        case: CaseView,
        reviewer_id: str,
        expected_revision: int,
        requested_outcome: str,
        rationale: str,
    ) -> ProcessingResult:
        """Run the policy-owned review transition for one authorized review (ADR-002).

        The route has already authenticated the actor and checked the moderator grant;
        this port binds the reviewed case to the caller's expected view, synthesizes
        the replay key from the reviewer and the reviewed revision, and lets the
        policy-owned ``MandatoryRuleViolation`` propagate for the route's 422 mapping.
        """
        if self._store is None:
            raise ValueError("review port requires a policy store at construction")
        snapshot = CaseSnapshot(
            case_id=case.case_id,
            revision=expected_revision,
            status=CaseStatus(case.status),
            content_hash=case.content_hash,
            policy_snapshot_id=case.policy_snapshot_id,
            policy_snapshot_digest=case.policy_snapshot_digest,
        )
        review = ReviewRequest(
            reviewer=ActorRef(actor_id=reviewer_id, role="moderator"),
            case_id=case.case_id,
            expected_revision=expected_revision,
            requested_outcome=Outcome(requested_outcome),
            rationale=rationale,
            policy_snapshot_id=case.policy_snapshot_id,
            policy_snapshot_digest=case.policy_snapshot_digest,
            content_hash=case.content_hash,
        )
        replay_key = ReplayKey(
            actor_id=reviewer_id,
            idempotency_key=f"review:{case.case_id}:{expected_revision}",
        )
        commit = self._engine.review_and_commit(
            store=self._store,
            case=snapshot,
            # content_text is policy-owned row state; legacy NULL rows prefilter as
            # empty, which cannot manufacture a prefilter high-severity escalation.
            content_text=case.content_text or "",
            review=review,
            expected_revision=expected_revision,
            replay_key=replay_key,
        )
        if commit.status is CommitStatus.COMMITTED:
            # Review invariant (ADR-002): a committed review's outcome equals the
            # requested one — an APPROVE that a mandatory REJECT floor would override
            # never commits (it raises before any write).
            return ProcessingResult(
                status="committed",
                case_id=case.case_id,
                case_revision=commit.case_revision,
                decision_id=commit.decision_id,
                audit_id=commit.audit_id,
                outcome=requested_outcome,
                message=commit.message,
            )
        return to_processing_result(commit, case_id=case.case_id)


def to_processing_result(
    commit: CommitResult, *, case_id: str | None = None
) -> ProcessingResult:
    """Project a policy commit result truthfully, without inventing success evidence."""

    if commit.status is CommitStatus.COMMITTED:
        if not case_id or commit.audit_id is None or commit.case_revision is None:
            raise ValueError("committed policy result requires case, revision and audit")
        return ProcessingResult(
            status="committed",
            case_id=case_id,
            case_revision=commit.case_revision,
            decision_id=commit.decision_id,
            audit_id=commit.audit_id,
            outcome=None,
            message=commit.message,
        )

    status: ProcessingStatus
    if commit.status is CommitStatus.CONFLICT:
        status = "conflict"
    elif commit.status is CommitStatus.PENDING_UNCONFIRMED:
        status = "pending_unconfirmed"
    else:
        status = "failed"
    return ProcessingResult(
        status=status,
        case_id=case_id,
        case_revision=None,
        decision_id=commit.decision_id,
        audit_id=None,
        outcome=None,
        message=commit.message,
    )


__all__ = ["PolicyAdapter", "to_processing_result"]
