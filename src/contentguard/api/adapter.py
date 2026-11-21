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
    AdvisoryResult as PolicyAdvisory,
)
from contentguard.policy.contracts import (
    AnalysisFailure as PolicyFailure,
)
from contentguard.policy.contracts import (
    CaseSnapshot,
    CommitResult,
    CommitStatus,
    FailureCode,
    ReplayKey,
)

from .schemas import ProcessingResult, ProcessingStatus


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


class PolicyAdapter:
    """Project validated S3 output and invoke the sole policy commit entry point."""

    def __init__(self, engine: _PolicyEntryPoint) -> None:
        self._engine = engine

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
