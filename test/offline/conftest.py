"""Shared offline fixtures for the S1 policy/audit tests (deterministic, offline).

Scope (CP1): this file only inserts ``src/`` on ``sys.path`` so ``contentguard`` is
importable without packaging, and provides fixtures that need only the CP1 scaffold
(the DTO builders). Fixtures that require unimplemented modules (``PolicySnapshot``,
``SqliteStore``, repositories) are added in the slice that implements them, per the S1
execution plan.

No network, no API key, no model access; no shared mutable state across tests.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from contentguard.policy.contracts import (
    AdvisoryResult,
    CaseSnapshot,
    CaseStatus,
    FailureCode,
    RequestContext,
    Severity,
    Usage,
    Verdict,
)
from contentguard.policy.snapshot import PolicySnapshot

FIXED_TIME = datetime(2026, 11, 18, 12, 0, 0, tzinfo=UTC)

SNAPSHOT_ID_V1 = "POL-SNAP-V1"
SNAPSHOT_DIGEST_V1 = "a" * 64
CONTENT_HASH = "b" * 64


@pytest.fixture()
def request_context() -> RequestContext:
    """A server-authenticated submitter context."""
    return RequestContext(actor_id="submitter-1", role="submitter", idempotency_key="idem-1")


@pytest.fixture()
def moderator_context() -> RequestContext:
    """A server-authenticated moderator context (the only authorized reviewer in S1)."""
    return RequestContext(actor_id="moderator-1", role="moderator", idempotency_key="idem-mod-1")


@pytest.fixture()
def usage_known() -> Usage:
    """A provider-reported per-attempt usage record."""
    return Usage(input_tokens=120, output_tokens=40, usage_unknown=False)


@pytest.fixture()
def advisory_medium(usage_known: Usage) -> AdvisoryResult:
    """An advisory result at medium severity, built through the documented key set."""
    return AdvisoryResult.from_payload(
        {
            "role": "initial_review",
            "verdict": Verdict.VIOLATE.value,
            "severity": Severity.MEDIUM.value,
            "rationale": "Contains targeted harassment.",
            "citations": ("clause-001",),
            "prompt_version": "prompt-v1",
            "model_id": "model-x",
            "model_version": "2026-11",
            "usage": {
                "input_tokens": usage_known.input_tokens,
                "output_tokens": usage_known.output_tokens,
                "usage_unknown": usage_known.usage_unknown,
            },
        }
    )


def make_case(
    *,
    case_id: str = "case-1",
    revision: int = 1,
    status: CaseStatus = CaseStatus.ANALYZING,
    advisory: AdvisoryResult | None = None,
    snapshot: PolicySnapshot | None = None,
    analysis_failure_code: FailureCode | None = None,
) -> CaseSnapshot:
    """Build a case snapshot pinned to a snapshot (v1 by default).

    When ``snapshot`` is omitted, the case is pinned to ``make_snapshot()``'s real digest
    so ``PolicyEngine`` accepts it. ``analysis_failure_code`` (a ``FailureCode``) pins a
    typed-failure case instead of advisory evidence.
    """
    if snapshot is None:
        snapshot = make_snapshot()
    snapshot_id = snapshot.snapshot_id
    snapshot_digest = snapshot.digest
    if analysis_failure_code is not None:
        return CaseSnapshot(
            case_id=case_id,
            revision=revision,
            status=status,
            content_hash=CONTENT_HASH,
            policy_snapshot_id=snapshot_id,
            policy_snapshot_digest=snapshot_digest,
            analysis_failure_code=analysis_failure_code,
        )
    if advisory is None:
        return CaseSnapshot(
            case_id=case_id,
            revision=revision,
            status=status,
            content_hash=CONTENT_HASH,
            policy_snapshot_id=snapshot_id,
            policy_snapshot_digest=snapshot_digest,
        )
    return CaseSnapshot(
        case_id=case_id,
        revision=revision,
        status=status,
        content_hash=CONTENT_HASH,
        policy_snapshot_id=snapshot_id,
        policy_snapshot_digest=snapshot_digest,
        advisory_verdict=advisory.verdict,
        advisory_severity=advisory.severity,
        advisory_model_id=advisory.model_id,
        advisory_model_version=advisory.model_version,
    )


@pytest.fixture()
def case_analyzing(advisory_medium: AdvisoryResult) -> CaseSnapshot:
    """An analyzing case carrying a medium-severity advisory verdict."""
    return make_case(advisory=advisory_medium)


@pytest.fixture()
def fixed_now() -> Iterator[datetime]:
    """A fixed UTC timestamp for deterministic ``decided_at`` assertions."""
    yield FIXED_TIME


def _snapshot_dict(
    *,
    snapshot_id: str,
    revision: int,
    rules: list[dict[str, object]],
    fallback_id: str = "FB-DEFAULT-HOLD",
    fallback_outcome: str = "hold",
    high_severity_terms: tuple[str, ...] = ("dangerous", "threat"),
    missing_builtin: str | None = None,
) -> dict[str, object]:
    """Assemble a ``PolicySnapshot.from_dict`` payload.

    ``missing_builtin`` drops one required built-in reason id so a negative test can
    prove that a catalog missing a built-in id is rejected.
    """
    builtin_ids = [
        "RULE-HIGH-SEVERITY",
        "RULE-PREFILTER-HIGH",
        "RULE-HUMAN-REVIEW",
        "FB-ANALYSIS-PROVIDER_UNAVAILABLE",
        "FB-ANALYSIS-TIMEOUT",
        "FB-ANALYSIS-INVALID_RESPONSE",
        "FB-ANALYSIS-GROUNDING_UNAVAILABLE",
        "FB-ANALYSIS-CONTEXT_OVERFLOW",
    ]
    if missing_builtin is not None:
        builtin_ids = [b for b in builtin_ids if b != missing_builtin]
    builtin_reasons = [
        {"reason_id": rid, "reason_text": f"builtin {rid}"} for rid in builtin_ids
    ]
    return {
        "snapshot_id": snapshot_id,
        "revision": revision,
        "rules": rules,
        "fallback": {
            "fallback_id": fallback_id,
            "outcome": fallback_outcome,
            "reason_text": "No approved rule matched; held for human review.",
        },
        "high_severity_terms": list(high_severity_terms),
        "builtin_reasons": builtin_reasons,
    }


_BASE_ALLOW_RULE: dict[str, object] = {
    "rule_id": "RULE-ALLOW-LOW",
    "condition": {"verdicts": ["allow"], "severities": ["low"], "prefilter_labels": []},
    "outcome": "approve",
    "reason_text": "Allowed: low severity, clean advisory.",
}

_REVIEW_RULE: dict[str, object] = {
    "rule_id": "RULE-REVIEW",
    "condition": {"verdicts": ["review"], "severities": ["medium"], "prefilter_labels": []},
    "outcome": "hold",
    "reason_text": "Review advisory: held.",
}

_REJECT_RULE: dict[str, object] = {
    "rule_id": "RULE-REJECT-VIOLATE",
    "condition": {"verdicts": ["violate"], "severities": ["low", "medium"], "prefilter_labels": []},
    "outcome": "reject",
    "reason_text": "Violating content rejected.",
}


def make_snapshot(*, missing_builtin: str | None = None) -> PolicySnapshot:
    """Build policy snapshot v1 via ``PolicySnapshot.from_dict``.

    Lazy import keeps the CP1 smoke tests passing before ``snapshot.py`` exists; the new
    Slice-A tests fail red until it is implemented.
    """
    

    return PolicySnapshot.from_dict(
        _snapshot_dict(
            snapshot_id=SNAPSHOT_ID_V1,
            revision=1,
            rules=[_BASE_ALLOW_RULE, _REVIEW_RULE, _REJECT_RULE],
            missing_builtin=missing_builtin,
        )
    )


def make_snapshot_v2() -> PolicySnapshot:
    """Build policy snapshot v2 with a different id and reason text for the same rule."""
    

    allow_v2 = dict(_BASE_ALLOW_RULE)
    allow_v2["reason_text"] = "Allowed (v2): low severity, clean advisory."
    return PolicySnapshot.from_dict(
        _snapshot_dict(
            snapshot_id="POL-SNAP-V2",
            revision=2,
            rules=[allow_v2, _REVIEW_RULE, _REJECT_RULE],
        )
    )


def make_snapshot_no_allow() -> PolicySnapshot:
    """Build a snapshot with no allow rule, so an allow advisory hits the fallback."""
    

    return PolicySnapshot.from_dict(
        _snapshot_dict(
            snapshot_id=SNAPSHOT_ID_V1,
            revision=1,
            rules=[_REVIEW_RULE, _REJECT_RULE],
        )
    )


def make_snapshot_with_reject_rule() -> PolicySnapshot:
    """Build a snapshot whose allow rule is preceded by a mandatory reject floor."""
    

    return PolicySnapshot.from_dict(
        _snapshot_dict(
            snapshot_id=SNAPSHOT_ID_V1,
            revision=1,
            rules=[_BASE_ALLOW_RULE, _REJECT_RULE],
        )
    )


@pytest.fixture()
def snapshot_v1() -> PolicySnapshot:
    """The default v1 policy snapshot (allow-low, review, reject-violate rules)."""
    return make_snapshot()


@pytest.fixture()
def snapshot_v2() -> PolicySnapshot:
    """The v2 policy snapshot (same rule ids, different reason text/id)."""
    return make_snapshot_v2()


@pytest.fixture()
def snapshot_no_allow() -> PolicySnapshot:
    """A v1 snapshot with no allow rule (allow advisory falls through to fallback)."""
    return make_snapshot_no_allow()


@pytest.fixture()
def snapshot_with_reject_rule() -> PolicySnapshot:
    """A v1 snapshot with an allow rule and a matching reject rule (floor check)."""
    return make_snapshot_with_reject_rule()
