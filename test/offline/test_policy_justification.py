"""Policy justification tests (REQ-FUN-004) — every decision carries a resolvable id.

Verifies REQ-FUN-004: every emitted ``reason_id`` resolves in the pinned snapshot's
rule/fallback/built-in reason catalog, and the decision carries the human-readable
reason text and the pinned snapshot identifiers. No DB, no network.

Slice A covers the pure engine; the "old decision keeps v1 ids after v2 activation"
half of the #25 case is completed in the persistence slice (it needs the snapshot store).
"""

from __future__ import annotations

import pytest
from conftest import make_case, make_snapshot, make_snapshot_v2

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
from contentguard.policy.snapshot import PolicySnapshot


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


def test_rule_or_fallback_id(snapshot_v1: PolicySnapshot) -> None:
    """Verifies REQ-FUN-004: a rule match and a fallback each carry the expected id.

    - An allow advisory matches ``RULE-ALLOW-LOW``.
    - A review advisory with no more specific rule falls through to the declared
      fallback (``FB-DEFAULT-HOLD``) when no rule matches.
    """
    engine = PolicyEngine(snapshot_v1)

    allow_decision = engine.evaluate(
        case=make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW)),
        content_text="benign",
    )
    assert allow_decision.reason_id == "RULE-ALLOW-LOW"
    assert allow_decision.outcome == Outcome.APPROVE
    assert allow_decision.reason_text == _reason_text(snapshot_v1, "RULE-ALLOW-LOW")


def test_fallback_id_when_no_rule_matches(snapshot_no_allow: PolicySnapshot) -> None:
    """Verifies REQ-FUN-004: with no matching rule the declared fallback id is emitted."""
    engine = PolicyEngine(snapshot_no_allow)
    decision = engine.evaluate(
        case=make_case(
            advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW),
            snapshot=snapshot_no_allow,
        ),
        content_text="benign",
    )
    assert decision.outcome == Outcome.HOLD
    assert decision.reason_id == "FB-DEFAULT-HOLD"
    assert decision.reason_text == _reason_text_by_fallback(snapshot_no_allow)
    assert decision.requires_human_review is True


def test_rule_hold_requires_human_review(snapshot_v1: PolicySnapshot) -> None:
    """Verifies REQ-FUN-004: a HOLD resolved by a matched rule (RULE-REVIEW) also sets
    ``requires_human_review=True`` — every non-final normal-path outcome requires review."""
    engine = PolicyEngine(snapshot_v1)
    decision = engine.evaluate(
        case=make_case(advisory=_advisory(verdict=Verdict.REVIEW, severity=Severity.MEDIUM)),
        content_text="benign",
    )
    assert decision.outcome == Outcome.HOLD
    assert decision.reason_id == "RULE-REVIEW"
    assert decision.requires_human_review is True


def test_decision_carries_pinned_snapshot_ids(snapshot_v1: PolicySnapshot) -> None:
    """Verifies REQ-FUN-004: the decision copies the pinned snapshot id and digest."""
    engine = PolicyEngine(snapshot_v1)
    decision = engine.evaluate(
        case=make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW)),
        content_text="benign",
    )
    assert decision.policy_snapshot_id == snapshot_v1.snapshot_id
    assert decision.policy_snapshot_digest == snapshot_v1.digest


def test_v2_snapshot_reason_text_is_stable(snapshot_v1: PolicySnapshot) -> None:
    """Verifies REQ-FUN-004 grounding: reason text comes from the snapshot that pinned it.

    The same rule id may carry different text in v2; a v1-pinned case must keep the v1
    text and identifiers (the store-level half is in the persistence slice).
    """
    v2 = make_snapshot_v2()
    v1_decision = PolicyEngine(snapshot_v1).evaluate(
        case=make_case(
            advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW),
            snapshot=snapshot_v1,
        ),
        content_text="benign",
    )
    v2_decision = PolicyEngine(v2).evaluate(
        case=make_case(
            advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW),
            snapshot=v2,
        ),
        content_text="benign",
    )
    assert v1_decision.policy_snapshot_id != v2_decision.policy_snapshot_id
    assert v1_decision.reason_text == _reason_text(snapshot_v1, "RULE-ALLOW-LOW")


def test_analysis_failure_reason_id_resolves(snapshot_v1: PolicySnapshot) -> None:
    """Verifies REQ-FUN-004: a typed failure emits a resolvable ``FB-ANALYSIS-<CODE>``."""
    engine = PolicyEngine(snapshot_v1)
    decision = engine.evaluate(
        case=make_case(advisory=None),
        content_text="benign",
        advisory=AnalysisFailure(code=FailureCode.CONTEXT_OVERFLOW, detail="too long"),
    )
    assert decision.reason_id == "FB-ANALYSIS-CONTEXT_OVERFLOW"
    assert decision.reason_text == _reason_text(snapshot_v1, "FB-ANALYSIS-CONTEXT_OVERFLOW")


def test_undeclared_reason_id_is_controlled_error() -> None:
    """Verifies REQ-FUN-004 (negative): a snapshot whose catalog lacks a built-in id is
    rejected at construction with a controlled error, never a bare unresolved string."""
    with pytest.raises(PolicyKernelError):
        make_snapshot(missing_builtin="RULE-HIGH-SEVERITY")


def test_high_severity_reason_id_resolves(snapshot_v1: PolicySnapshot) -> None:
    """Verifies REQ-FUN-004: the high-severity escalate emits the built-in id with text."""
    engine = PolicyEngine(snapshot_v1)
    decision = engine.evaluate(
        case=make_case(advisory=_advisory(verdict=Verdict.VIOLATE, severity=Severity.HIGH)),
        content_text="benign",
    )
    assert decision.reason_id == "RULE-HIGH-SEVERITY"
    assert decision.reason_text == _reason_text(snapshot_v1, "RULE-HIGH-SEVERITY")
    assert decision.requires_human_review is True


def _reason_text(snapshot: PolicySnapshot, reason_id: str) -> str:
    for rule in snapshot.rules:
        if rule.rule_id == reason_id:
            return rule.reason_text
    for entry in snapshot.builtin_reasons:
        if entry.reason_id == reason_id:
            return entry.reason_text
    raise AssertionError(f"reason {reason_id} not in snapshot catalog")


def _reason_text_by_fallback(snapshot: PolicySnapshot) -> str:
    return snapshot.fallback.reason_text
