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

import json
from dataclasses import replace
from datetime import UTC, datetime

from .contracts import (
    FINAL_STATUSES,
    REVIEWABLE_STATUSES,
    AdvisoryResult,
    AnalysisFailure,
    CaseSnapshot,
    CaseStatus,
    CommitResult,
    CommitStatus,
    FailureCode,
    Outcome,
    PolicyDecision,
    ReplayKey,
    ReviewRequest,
    Severity,
    Verdict,
    bind_decision_id,
    decision_payload_from_fields,
    effective_severity,
    is_frozen_dto,
)
from .enforcement import _AUTHORITY_TOKEN, EnforcementAuthority, _payload_hash
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
    HUMAN_REVIEW_REASON_ID,
    PREFILTER_HIGH_REASON_ID,
    PolicyRule,
    PolicySnapshot,
    SnapshotStore,
)
from .store import SqliteStore

_MODERATOR_ROLE = "moderator"
_POLICY_ACTOR = "policy"


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

        # Step 4: analysis failure (never a review in this slice). A held typed-failure
        # case reaches its disposition through step 7 (the review), so step 4 only applies
        # to the non-review path.
        if failure_code is not None and review is None:
            return self._build_failure_decision(
                case=case,
                failure_code=failure_code,
                prefilter_high=prefilter.high_severity,
                decided_at=decided_at,
                model_id=model_id,
            )

        # Step 5: effective severity via explicit rank (never string ordering). A typed
        # failure has no advisory severity; only the prefilter may contribute one.
        prefilter_severity = Severity.HIGH if prefilter.high_severity else None
        eff_severity = effective_severity(advisory_severity, prefilter_severity)

        # Step 7: a current authorized review of a HELD/ESCALATED case is the only path to
        # a final disposition. Regardless of why the case was held or escalated (high
        # severity, typed failure, or a normal hold), the reviewed APPROVE/REJECT is
        # evaluated against the pinned rules with the mandatory REJECT floor winning.
        if review is not None:
            return self._build_review_decision(
                case=case,
                review=review,
                verdict=verdict,
                advisory_severity=advisory_severity,
                model_id=model_id,
                model_version=model_version,
                failure_code=failure_code,
                eff_severity=eff_severity,
                prefilter_labels=prefilter.labels,
                decided_at=decided_at,
            )

        # Step 6: high severity escalates before any allow rule can finalise.
        assert verdict is not None
        assert advisory_severity is not None
        assert model_id is not None
        assert model_version is not None
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

        # Step 8: mandatory-reject floor, else first matching rule, else fallback.
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

    def evaluate_and_commit(
        self,
        *,
        store: SqliteStore,
        case: CaseSnapshot,
        content_text: str,
        advisory: AdvisoryResult | AnalysisFailure | None = None,
        review: ReviewRequest | None = None,
        expected_revision: int,
        replay_key: ReplayKey,
    ) -> CommitResult:
        """Evaluate against the case row's pinned snapshot and commit atomically.

        Loads the case row and its **pinned** snapshot first (not ``self.snapshot`` if a
        newer snapshot is globally active), reconstructs the row case, and evaluates the
        candidate with ``PolicyEngine(pinned)``. A replay is recognised by comparing the
        candidate's payload hash to the stored replay payload **before** the revision/
        status precondition, so a same-key/same-payload retry after a policy activation
        (or after the case revision advanced) returns the stored result rather than a
        spurious CONFLICT. A same-key/different-payload retry is a CONFLICT. The human-
        review transition (step 7) is not part of this slice; a review is passed through
        to ``evaluate`` which rejects it.
        """
        with store.read_connection() as conn:
            row = conn.execute(
                "SELECT revision, status, content_hash, policy_snapshot_id, "
                "policy_snapshot_digest, advisory_verdict, advisory_severity, "
                "advisory_model_id, advisory_model_version, analysis_failure_code "
                "FROM cases WHERE case_id = ?",
                (case.case_id,),
            ).fetchone()
            if row is None:
                return _conflict_result(case, "case not found")
            try:
                pinned = SnapshotStore.load(conn, str(row[3]))
            except PolicyKernelError as exc:
                return _failed_result(case, f"pinned snapshot unavailable: {exc}")
            replay = conn.execute(
                "SELECT payload_hash, result_json FROM commits "
                "WHERE replay_actor = ? AND replay_key = ?",
                (replay_key.actor_id, replay_key.idempotency_key),
            ).fetchone()

        (
            revision,
            status,
            row_content_hash,
            snap_id,
            snap_digest,
            adv_verdict,
            adv_severity,
            adv_model_id,
            adv_model_version,
            failure_code,
        ) = row

        row_case = CaseSnapshot(
            case_id=case.case_id,
            revision=expected_revision,
            status=CaseStatus(status),
            content_hash=str(row_content_hash),
            policy_snapshot_id=str(snap_id),
            policy_snapshot_digest=str(snap_digest),
            advisory_verdict=Verdict(adv_verdict) if adv_verdict is not None else None,
            advisory_severity=(
                Severity(adv_severity) if adv_severity is not None else None
            ),
            advisory_model_id=None if adv_model_id is None else str(adv_model_id),
            advisory_model_version=(
                None if adv_model_version is None else str(adv_model_version)
            ),
            analysis_failure_code=(
                FailureCode(failure_code) if failure_code is not None else None
            ),
        )

        pinned_engine = PolicyEngine(pinned)
        try:
            candidate = pinned_engine.evaluate(
                case=row_case,
                content_text=content_text,
                advisory=advisory,
                review=review,
            )
        except (
            PolicyConflictError,
            PolicyKernelError,
            InvalidReviewError,
            StaleReviewError,
            UnauthorizedReviewError,
        ) as exc:
            candidate = None
            candidate_error: Exception | None = exc
        else:
            candidate_error = None

        # Replay check before the revision/status precondition. The stored payload was
        # evaluated under the snapshot pinned at first commit; the candidate here uses the
        # same pinned snapshot, so a legitimate retry yields an identical payload hash
        # even if a newer snapshot is globally active.
        #
        # A first commit advances the case out of its intake status (revision +1, status
        # e.g. ``approved``). Re-evaluating that final row would trip the final-state guard
        # even though ``evaluate`` is deterministic and the payload hash does not include
        # ``status``/``revision``-derived status. When a replay row exists we therefore
        # reconstruct the candidate from the row's immutable evidence under a neutral
        # non-final status; the decision fields (which the payload hash covers) are
        # unchanged because the normal/failure/high-severity outcomes derive from the
        # advisory evidence, pre-filter, and pinned rules — never from ``status``.
        #
        # A review is the exception: step 7 only runs for a HELD/ESCALATED case, so the
        # neutral substitution would raise InvalidReviewError (not a PolicyKernelError) and
        # misclassify a legitimate review replay. A reviewed case commits to a final status,
        # but the pre-review status is recoverable: a reviewed decision is REJECT (floor or
        # reviewed) or APPROVE, and a reviewable row was HELD or ESCALATED. Re-evaluate
        # under ESCALATED (a reviewable, non-final status) so step 7 runs; the reviewed
        # outcome and its payload hash do not depend on HELD-vs-ESCALATED.
        if replay is not None and candidate is None:
            neutral_status = (
                CaseStatus.ESCALATED if review is not None else CaseStatus.ANALYZING
            )
            replay_case = replace(row_case, status=neutral_status)
            try:
                candidate = pinned_engine.evaluate(
                    case=replay_case,
                    content_text=content_text,
                    advisory=advisory,
                    review=review,
                )
            except (
                PolicyConflictError,
                PolicyKernelError,
                InvalidReviewError,
                StaleReviewError,
                UnauthorizedReviewError,
            ):
                candidate = None
            candidate_error = None

        if replay is not None:
            stored_payload_hash, stored_result_json = replay
            if candidate is not None and _payload_hash(candidate) == stored_payload_hash:
                return _commit_result_from_json(str(stored_result_json))
            return _conflict_result(case, "replay key reused with a different payload")

        # Not a replay: the caller's expected view must match the stored row.
        if (
            int(revision) != expected_revision
            or row_content_hash != case.content_hash
            or snap_id != case.policy_snapshot_id
            or snap_digest != case.policy_snapshot_digest
        ):
            return _conflict_result(case, "case revision/snapshot/hash mismatch")

        if candidate is None:
            if isinstance(candidate_error, PolicyConflictError):
                return _conflict_result(
                    case, f"cannot re-decide this case: {candidate_error}"
                )
            if isinstance(
                candidate_error,
                (InvalidReviewError, StaleReviewError, UnauthorizedReviewError),
            ):
                return _failed_result(case, f"review rejected: {candidate_error}")
            return _failed_result(case, f"policy error: {candidate_error}")

        authority = EnforcementAuthority(store)
        try:
            return authority.commit(
                candidate,
                expected_revision=expected_revision,
                replay_key=replay_key,
            )
        except PolicyKernelError as exc:
            return _failed_result(case, f"commit rejected: {exc}")

    # --- rule matching -----------------------------------------------------

    def _matching_rules(
        self,
        *,
        verdict: Verdict | None,
        severity: Severity | None,
        prefilter_labels: tuple[str, ...],
    ) -> list[PolicyRule]:
        labels = set(prefilter_labels)
        matched: list[PolicyRule] = []
        for rule in self._snapshot.rules:
            cond = rule.condition
            if cond.verdicts and (verdict is None or verdict not in cond.verdicts):
                continue
            if cond.severities and (severity is None or severity not in cond.severities):
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

    def _build_review_decision(
        self,
        *,
        case: CaseSnapshot,
        review: ReviewRequest,
        verdict: Verdict | None,
        advisory_severity: Severity | None,
        model_id: str | None,
        model_version: str | None,
        failure_code: FailureCode | None,
        eff_severity: Severity | None,
        prefilter_labels: tuple[str, ...],
        decided_at: datetime,
    ) -> PolicyDecision:
        """Apply an authorized review (S1 plan §3.5 step 7).

        Collect all matching rules; the first matching ``REJECT`` is a mandatory floor that
        overrides the review. Otherwise the reviewed APPROVE/REJECT applies with reason
        ``RULE-HUMAN-REVIEW``. The reviewer enters ``actor_ids``; a pinned AI model enters
        ``ai:<model_id>`` only when a verdict exists (a typed-failure case has none).
        """
        matched = self._matching_rules(
            verdict=verdict,
            severity=eff_severity,
            prefilter_labels=prefilter_labels,
        )
        reject_rule = next(
            (rule for rule in matched if rule.outcome is Outcome.REJECT), None
        )
        if reject_rule is not None:
            outcome = Outcome.REJECT
            reason_id = reject_rule.rule_id
            reason_text = reject_rule.reason_text
        else:
            outcome = review.requested_outcome
            reason_id = HUMAN_REVIEW_REASON_ID
            reason_text = self._snapshot.reason_text(HUMAN_REVIEW_REASON_ID)

        return _assemble(
            case=case,
            outcome=outcome,
            reason_id=reason_id,
            reason_text=reason_text,
            severity=eff_severity,
            advisory_verdict=verdict,
            advisory_severity=advisory_severity,
            advisory_model_id=model_id if verdict is not None else None,
            advisory_model_version=model_version if verdict is not None else None,
            analysis_failure_code=failure_code,
            requires_human_review=False,
            actor_ids=_actor_ids(
                model_id=model_id if verdict is not None else None,
                reviewer_id=review.reviewer.actor_id,
            ),
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


def _actor_ids(*, model_id: str | None, reviewer_id: str | None = None) -> tuple[str, ...]:
    actors = [_POLICY_ACTOR]
    if model_id:
        actors.append(f"ai:{model_id}")
    if reviewer_id:
        actors.append(f"reviewer:{reviewer_id}")
    return tuple(actors)


def _conflict_result(case: CaseSnapshot, message: str) -> CommitResult:
    return CommitResult(
        status=CommitStatus.CONFLICT,
        decision_id="",
        audit_id=None,
        case_revision=None,
        message=message,
    )


def _failed_result(case: CaseSnapshot, message: str) -> CommitResult:
    return CommitResult(
        status=CommitStatus.FAILED,
        decision_id="",
        audit_id=None,
        case_revision=None,
        message=message,
    )


def _commit_result_from_json(raw: str) -> CommitResult:
    data = json.loads(raw)
    return CommitResult(
        status=CommitStatus(str(data["status"])),
        decision_id=str(data["decision_id"]),
        audit_id=data["audit_id"],
        case_revision=data["case_revision"],
        message=str(data["message"]),
    )


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
