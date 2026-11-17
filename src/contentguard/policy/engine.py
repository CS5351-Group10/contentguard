"""Deterministic policy engine (REQ-INV-001/003/004, REQ-FUN-004, REQ-QUA-001).

``PolicyEngine.evaluate`` is a pure, write-free decision function. It implements S1 plan
§3.5 evaluation steps 1-6 and 8-11 (branch on advisory evidence, typed-failure hold,
explicit severity rank, high-severity escalate, mandatory-reject floor, declared-rule /
fallback resolution, reason-catalog resolution, deterministic decision identity).

**Step 7 — the human-review transition — is NOT implemented in this slice.** A current
authorized review of a HELD/ESCALATED case is accepted structurally but its final
disposition is deferred to the routing slice. The persistence/commit path
(``evaluate_and_commit``, ``EnforcementAuthority``) arrives in a later slice.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .contracts import (
    FINAL_STATUSES,
    REVIEWABLE_STATUSES,
    AdvisoryResult,
    AnalysisFailure,
    CaseSnapshot,
    FailureCode,
    Outcome,
    PolicyDecision,
    ReviewRequest,
    Severity,
    Verdict,
    bind_decision_id,
    decision_payload_from_fields,
    effective_severity,
    is_frozen_dto,
)
from .errors import (
    InvalidReviewError,
    PolicyConflictError,
    PolicyKernelError,
    StaleReviewError,
    UnauthorizedReviewError,
)
from .prefilter import DeterministicPrefilter
from .snapshot import (
    HIGH_SEVERITY_REASON_ID,
    PREFILTER_HIGH_REASON_ID,
    PolicyRule,
    PolicySnapshot,
)

_AUTHORITY_TOKEN = "contentguard.policy.engine.authority"
_MODERATOR_ROLE = "moderator"
_POLICY_ACTOR = "policy"


def _is_engine_token(token: str | None) -> bool:
    return token == _AUTHORITY_TOKEN


class PolicyEngine:
    """Pure deterministic decision engine bound to one pinned snapshot."""

    def __init__(self, snapshot: PolicySnapshot) -> None:
        if not is_frozen_dto(snapshot):
            raise PolicyKernelError("engine requires an immutable PolicySnapshot")
        self._snapshot = snapshot
        self._prefilter = DeterministicPrefilter(snapshot.high_severity_terms)

    @property
    def snapshot(self) -> PolicySnapshot:
        return self._snapshot

    def evaluate(
        self,
        *,
        case: CaseSnapshot,
        content_text: str,
        advisory: AdvisoryResult | AnalysisFailure | None = None,
        review: ReviewRequest | None = None,
        decided_at: datetime | None = None,
    ) -> PolicyDecision:
        """Return the deterministic decision for the complete input/state tuple.

        Steps 1-6 and 8-11 of S1 plan §3.5. The human-review transition (step 7) is not
        part of this slice: a review of a HELD/ESCALATED case is currency/authorization
        checked here but raises a controlled error until the routing slice lands.
        """
        _validate_case_snapshot(case, self._snapshot)
        _validate_review(case, review)

        # Step 2: deterministic pre-filter.
        prefilter = self._prefilter.evaluate(content_text)

        # Step 3: branch on advisory evidence before reading severity.
        verdict, advisory_severity, model_id, model_version, failure_code = (
            _resolve_advisory_evidence(case, advisory)
        )

        decided_at = decided_at or datetime.now(UTC)

        # Step 4: analysis failure (never a review in this slice).
        if failure_code is not None:
            return self._build_failure_decision(
                case=case,
                failure_code=failure_code,
                prefilter_high=prefilter.high_severity,
                decided_at=decided_at,
                model_id=model_id,
            )

        # Step 5: effective severity via explicit rank (never string ordering).
        # After step 4 (no failure code) the advisory evidence is a full verdict tuple.
        assert verdict is not None
        assert advisory_severity is not None
        assert model_id is not None
        assert model_version is not None
        prefilter_severity = Severity.HIGH if prefilter.high_severity else None
        eff_severity = effective_severity(advisory_severity, prefilter_severity)
        assert eff_severity is not None  # a verdict always carries a severity

        # Step 6: high severity escalates before any allow rule can finalise.
        if eff_severity is Severity.HIGH:
            return self._build_high_severity_decision(
                case=case,
                advisory=advisory,
                verdict=verdict,
                advisory_severity=advisory_severity,
                model_id=model_id,
                model_version=model_version,
                decided_at=decided_at,
            )

        # Step 7 (review transition) is deferred to the routing slice. Reaching here
        # with a review is a held/escalated case; that cannot be finalised yet.
        if review is not None:
            raise InvalidReviewError(
                "human-review transition is implemented in the routing slice"
            )

        # Step 8: mandatory-reject floor, else first matching rule, else fallback.
        assert verdict is not None and advisory_severity is not None
        matched = self._matching_rules(
            verdict=verdict,
            severity=advisory_severity,
            prefilter_labels=prefilter.labels,
        )
        reason_id, reason_text, outcome = self._resolve_normal_outcome(matched)

        return _assemble(
            case=case,
            outcome=outcome,
            reason_id=reason_id,
            reason_text=reason_text,
            severity=eff_severity,
            advisory_verdict=verdict,
            advisory_severity=advisory_severity,
            advisory_model_id=model_id,
            advisory_model_version=model_version,
            analysis_failure_code=None,
            requires_human_review=False,
            actor_ids=_actor_ids(model_id=model_id),
            decided_at=decided_at,
        )

    # --- rule matching -----------------------------------------------------

    def _matching_rules(
        self,
        *,
        verdict: Verdict,
        severity: Severity,
        prefilter_labels: tuple[str, ...],
    ) -> list[PolicyRule]:
        labels = set(prefilter_labels)
        matched: list[PolicyRule] = []
        for rule in self._snapshot.rules:
            cond = rule.condition
            if cond.verdicts and verdict not in cond.verdicts:
                continue
            if cond.severities and severity not in cond.severities:
                continue
            if cond.prefilter_labels and not (set(cond.prefilter_labels) & labels):
                continue
            matched.append(rule)
        return matched

    def _resolve_normal_outcome(
        self, matched: list[PolicyRule]
    ) -> tuple[str, str, Outcome]:
        # Mandatory floor: the first matching REJECT wins over any earlier rule.
        for rule in matched:
            if rule.outcome is Outcome.REJECT:
                return rule.rule_id, rule.reason_text, Outcome.REJECT
        if matched:
            first = matched[0]
            return first.rule_id, first.reason_text, first.outcome
        fallback = self._snapshot.fallback
        return fallback.fallback_id, fallback.reason_text, fallback.outcome

    # --- decision builders -------------------------------------------------

    def _build_failure_decision(
        self,
        *,
        case: CaseSnapshot,
        failure_code: FailureCode,
        prefilter_high: bool,
        decided_at: datetime,
        model_id: str | None,
    ) -> PolicyDecision:
        if prefilter_high:
            outcome = Outcome.ESCALATE
            reason_id = PREFILTER_HIGH_REASON_ID
            severity: Severity | None = Severity.HIGH
        else:
            outcome = Outcome.HOLD
            reason_id = f"FB-ANALYSIS-{failure_code.name}"
            severity = None
        return _assemble(
            case=case,
            outcome=outcome,
            reason_id=reason_id,
            reason_text=self._snapshot.reason_text(reason_id),
            severity=severity,
            advisory_verdict=None,
            advisory_severity=None,
            advisory_model_id=model_id,
            advisory_model_version=None,
            analysis_failure_code=failure_code,
            requires_human_review=True,
            actor_ids=_actor_ids(model_id=None),
            decided_at=decided_at,
        )

    def _build_high_severity_decision(
        self,
        *,
        case: CaseSnapshot,
        advisory: AdvisoryResult | AnalysisFailure | None,
        verdict: Verdict,
        advisory_severity: Severity,
        model_id: str,
        model_version: str,
        decided_at: datetime,
    ) -> PolicyDecision:
        return _assemble(
            case=case,
            outcome=Outcome.ESCALATE,
            reason_id=HIGH_SEVERITY_REASON_ID,
            reason_text=self._snapshot.reason_text(HIGH_SEVERITY_REASON_ID),
            severity=Severity.HIGH,
            advisory_verdict=verdict,
            advisory_severity=advisory_severity,
            advisory_model_id=model_id,
            advisory_model_version=model_version,
            analysis_failure_code=None,
            requires_human_review=True,
            actor_ids=_actor_ids(model_id=model_id),
            decided_at=decided_at,
        )


# --- free helpers ----------------------------------------------------------


def _assemble(
    *,
    case: CaseSnapshot,
    outcome: Outcome,
    reason_id: str,
    reason_text: str,
    severity: Severity | None,
    advisory_verdict: Verdict | None,
    advisory_severity: Severity | None,
    advisory_model_id: str | None,
    advisory_model_version: str | None,
    analysis_failure_code: FailureCode | None,
    requires_human_review: bool,
    actor_ids: tuple[str, ...],
    decided_at: datetime,
) -> PolicyDecision:
    """Build a ``PolicyDecision`` with its deterministic ``decision_id`` filled in.

    The id is a sha256 digest of the complete input/state tuple, excluding
    ``decided_at`` and ``_authority_token`` (QUA-001). The id is computed from raw fields
    before construction, so the frozen DTO is built once with a valid, non-empty id.
    """
    decision_id = bind_decision_id(
        decision_payload_from_fields(
            case_id=case.case_id,
            case_revision=case.revision,
            content_hash=case.content_hash,
            policy_snapshot_id=case.policy_snapshot_id,
            policy_snapshot_digest=case.policy_snapshot_digest,
            advisory_verdict=advisory_verdict,
            advisory_severity=advisory_severity,
            advisory_model_id=advisory_model_id,
            advisory_model_version=advisory_model_version,
            analysis_failure_code=analysis_failure_code,
            outcome=outcome,
            reason_id=reason_id,
            requires_human_review=requires_human_review,
            actor_ids=actor_ids,
        )
    )
    return PolicyDecision(
        decision_id=decision_id,
        case_id=case.case_id,
        case_revision=case.revision,
        outcome=outcome,
        reason_id=reason_id,
        reason_text=reason_text,
        severity=severity,
        advisory_verdict=advisory_verdict,
        advisory_severity=advisory_severity,
        advisory_model_id=advisory_model_id,
        advisory_model_version=advisory_model_version,
        analysis_failure_code=analysis_failure_code,
        policy_snapshot_id=case.policy_snapshot_id,
        policy_snapshot_digest=case.policy_snapshot_digest,
        content_hash=case.content_hash,
        requires_human_review=requires_human_review,
        actor_ids=actor_ids,
        decided_at=decided_at,
        _authority_token=_AUTHORITY_TOKEN,
    )


def _actor_ids(*, model_id: str | None) -> tuple[str, ...]:
    actors = [_POLICY_ACTOR]
    if model_id:
        actors.append(f"ai:{model_id}")
    return tuple(actors)


def _validate_case_snapshot(case: CaseSnapshot, snapshot: PolicySnapshot) -> None:
    if case.status in FINAL_STATUSES:
        raise PolicyConflictError(f"case {case.case_id} is in a final state")
    if (
        case.policy_snapshot_id != snapshot.snapshot_id
        or case.policy_snapshot_digest != snapshot.digest
    ):
        raise PolicyConflictError("case is pinned to a different policy snapshot")


def _validate_review(case: CaseSnapshot, review: ReviewRequest | None) -> None:
    """Apply step-1 currency/authorization checks; never write, never decide."""
    if review is None:
        if case.status in REVIEWABLE_STATUSES:
            raise PolicyConflictError(
                "a held/escalated case can only be re-decided through a current review"
            )
        return
    if case.status not in REVIEWABLE_STATUSES:
        raise InvalidReviewError(f"case {case.case_id} in status {case.status.value} cannot be reviewed")
    if (
        review.case_id != case.case_id
        or review.expected_revision != case.revision
        or review.policy_snapshot_id != case.policy_snapshot_id
        or review.policy_snapshot_digest != case.policy_snapshot_digest
        or review.content_hash != case.content_hash
    ):
        raise StaleReviewError("review evidence is stale for the current case")
    if review.reviewer.role != _MODERATOR_ROLE or not review.rationale.strip():
        raise UnauthorizedReviewError("review requires a moderator and a non-empty rationale")


def _resolve_advisory_evidence(
    case: CaseSnapshot,
    advisory: AdvisoryResult | AnalysisFailure | None,
) -> tuple[Verdict | None, Severity | None, str | None, str | None, FailureCode | None]:
    """Return (verdict, advisory_severity, model_id, model_version, failure_code).

    A supplied ``AnalysisFailure`` wins; a supplied ``AdvisoryResult`` next; otherwise
    the case's pinned evidence. With neither, a controlled error (no invented verdict).
    """
    if isinstance(advisory, AnalysisFailure):
        return None, None, None, None, advisory.code
    if isinstance(advisory, AdvisoryResult):
        return (
            advisory.verdict,
            advisory.severity,
            advisory.model_id,
            advisory.model_version,
            None,
        )
    if case.analysis_failure_code is not None:
        return None, None, case.advisory_model_id, None, case.analysis_failure_code
    if case.advisory_verdict is not None:
        return (
            case.advisory_verdict,
            case.advisory_severity,
            case.advisory_model_id,
            case.advisory_model_version,
            None,
        )
    raise PolicyKernelError(
        f"case {case.case_id} has neither advisory evidence nor a typed analysis failure"
    )


__all__ = ["PolicyEngine"]
