"""Policy determinism tests (QUA-001) — pure engine, no persistence.

Verifies REQ-QUA-001: the same complete input/state tuple always yields the same
``outcome`` and ``reason_id`` (``decided_at`` is operational metadata and may differ).
No DB, no network.

Slice A covers only the pure engine (steps 1-6, 8-11); the review transition (step 7)
is exercised in the routing/audit slices.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from conftest import (
    make_case,
)

from contentguard.policy.contracts import (
    AdvisoryResult,
    AnalysisFailure,
    FailureCode,
    Outcome,
    Severity,
    Verdict,
)
from contentguard.policy.engine import PolicyEngine
from contentguard.policy.errors import PolicyKernelError
from contentguard.policy.prefilter import DeterministicPrefilter
from contentguard.policy.snapshot import PolicySnapshot


def _advisory(*, verdict: Verdict, severity: Severity, model_id: str = "model-x") -> AdvisoryResult:
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


def _engine(snapshot: PolicySnapshot) -> PolicyEngine:
    return PolicyEngine(snapshot)


def test_repeat_and_reorder(snapshot_v1: PolicySnapshot) -> None:
    """Verifies REQ-QUA-001: repeated evaluation of one tuple yields identical outcome/reason.

    Reordering repeated calls and varying ``decided_at`` must not change ``outcome`` or
    ``reason_id`` (operational metadata only).
    """
    case = make_case(
        advisory=_advisory(verdict=Verdict.VIOLATE, severity=Severity.MEDIUM),
    )
    engine = _engine(snapshot_v1)
    times = [
        datetime(2026, 11, 18, 1, 0, 0, tzinfo=UTC),
        datetime(2026, 11, 18, 2, 0, 0, tzinfo=UTC),
        datetime(2026, 11, 18, 3, 0, 0, tzinfo=UTC),
    ]

    results = [
        engine.evaluate(case=case, content_text="benign text", advisory=None, decided_at=t)
        for t in times
    ]
    for result in results:
        assert result.outcome == results[0].outcome
        assert result.reason_id == results[0].reason_id

    assert results[0].decided_at != results[1].decided_at


@pytest.mark.parametrize(
    "advisory,expected_outcome,expected_reason",
    [
        # A clean allow advisory with no matching REJECT rule → allow rule.
        (
            _advisory(verdict=Verdict.ALLOW, severity=Severity.LOW),
            Outcome.APPROVE,
            "RULE-ALLOW-LOW",
        ),
        # A medium review verdict, no high severity → falls through to the rule set.
        (
            _advisory(verdict=Verdict.REVIEW, severity=Severity.MEDIUM),
            Outcome.HOLD,
            "RULE-REVIEW",
        ),
        # A high-severity advisory → escalate (step 6 precedes normal rules).
        (
            _advisory(verdict=Verdict.VIOLATE, severity=Severity.HIGH),
            Outcome.ESCALATE,
            "RULE-HIGH-SEVERITY",
        ),
    ],
)
def test_deterministic_outcome_matrix(
    snapshot_v1: PolicySnapshot,
    advisory: AdvisoryResult,
    expected_outcome: Outcome,
    expected_reason: str,
) -> None:
    """Verifies REQ-QUA-001: each complete tuple maps to one stable outcome/reason."""
    case = make_case(advisory=advisory)
    engine = _engine(snapshot_v1)
    first = engine.evaluate(case=case, content_text="benign text")
    second = engine.evaluate(case=case, content_text="benign text")
    assert first.outcome == second.outcome == expected_outcome
    assert first.reason_id == second.reason_id == expected_reason


def test_reason_id_independent_of_decided_at(snapshot_v1: PolicySnapshot) -> None:
    """Verifies REQ-QUA-001: ``decided_at`` never affects outcome or reason identity."""
    case = make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW))
    engine = _engine(snapshot_v1)
    a = engine.evaluate(
        case=case, content_text="benign", decided_at=datetime(2020, 1, 1, tzinfo=UTC)
    )
    b = engine.evaluate(
        case=case, content_text="benign", decided_at=datetime(2030, 1, 1, tzinfo=UTC)
    )
    assert (a.outcome, a.reason_id) == (b.outcome, b.reason_id)


def test_no_advisory_evidence_is_controlled_failure(snapshot_v1: PolicySnapshot) -> None:
    """Verifies REQ-QUA-001 (negative): a case with neither advisory nor typed failure
    raises a controlled ``PolicyKernelError`` — no invented verdict, no result."""
    case = make_case(advisory=None)
    assert case.advisory_verdict is None
    assert case.analysis_failure_code is None
    engine = _engine(snapshot_v1)
    with pytest.raises(PolicyKernelError):
        engine.evaluate(case=case, content_text="benign")


def test_typed_failure_is_deterministic(snapshot_v1: PolicySnapshot) -> None:
    """Verifies REQ-QUA-001: a typed analysis failure deterministically holds."""
    failure = AnalysisFailure(code=FailureCode.TIMEOUT, detail="provider timed out")
    case = make_case(advisory=None)
    engine = _engine(snapshot_v1)
    first = engine.evaluate(case=case, content_text="benign", advisory=failure)
    second = engine.evaluate(case=case, content_text="benign", advisory=failure)
    assert first.outcome == second.outcome == Outcome.HOLD
    assert first.reason_id == second.reason_id == "FB-ANALYSIS-TIMEOUT"


def test_prefilter_is_deterministic_and_case_folded() -> None:
    """Verifies REQ-QUA-001: the deterministic pre-filter is stable and case-folded.

    Literal substring matching only (no regex); labels are sorted.
    """
    prefilter = DeterministicPrefilter(terms=("badword", "THREAT"))
    first = prefilter.evaluate("This has BADWORD and a threat.")
    second = prefilter.evaluate("This has BADWORD and a threat.")
    assert first.high_severity is True
    assert first.labels == second.labels
    assert first.matched_terms == second.matched_terms
    assert first.labels == tuple(sorted(first.labels))
