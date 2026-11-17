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
    RequestContext,
    Severity,
    Usage,
    Verdict,
)

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
) -> CaseSnapshot:
    """Build a case snapshot pinned to v1, optionally carrying the advisory evidence."""
    if advisory is None:
        return CaseSnapshot(
            case_id=case_id,
            revision=revision,
            status=status,
            content_hash=CONTENT_HASH,
            policy_snapshot_id=SNAPSHOT_ID_V1,
            policy_snapshot_digest=SNAPSHOT_DIGEST_V1,
        )
    return CaseSnapshot(
        case_id=case_id,
        revision=revision,
        status=status,
        content_hash=CONTENT_HASH,
        policy_snapshot_id=SNAPSHOT_ID_V1,
        policy_snapshot_digest=SNAPSHOT_DIGEST_V1,
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
