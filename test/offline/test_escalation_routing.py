"""Escalation-routing tests (REQ-INV-003) — pure engine (Slice A).

Verifies REQ-INV-003: high-severity content can never reach a final disposition without
human review; the effective severity uses an explicit rank (never string ordering).

Slice A asserts only engine-produced decisions (no DB/commit). Queue persistence,
commit binding and stale/forged-review rejection are added in the persistence/routing
slices.
"""

from __future__ import annotations

import itertools

import pytest
from conftest import make_case

from contentguard.policy.contracts import (
    AdvisoryResult,
    Outcome,
    Severity,
    Verdict,
)
from contentguard.policy.engine import PolicyEngine
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
