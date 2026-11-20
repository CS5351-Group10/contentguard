"""S3-to-S1 policy adapter (ADR-001; REQ-FUN-002/004, REQ-INV-001/004).

This module may depend on policy contracts and the engine entry point.  It never
imports enforcement internals and never interprets model output as an action.
"""

from __future__ import annotations

from typing import Protocol

from contentguard.analysis.contracts import (
    AdvisoryResult as AnalysisAdvisory,
    AnalysisFailure as AnalysisFailure,
)
from contentguard.policy.contracts import (
    AdvisoryResult as PolicyAdvisory,
    AnalysisFailure as PolicyFailure,
    CaseSnapshot,
    CommitResult,
    FailureCode,
    ReplayKey,
)


class _PolicyEntryPoint(Protocol):
    def evaluate_and_commit(
        self,
        *,
        store: object,
        case: CaseSnapshot,
        content_text: str,
        advisory: PolicyAdvisory | PolicyFailure | None,
        review: object | None,
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
        store: object,
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


__all__ = ["PolicyAdapter"]
