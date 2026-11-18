"""Analysis DTO and strict-validation tests for ADR-001, REQ-FUN-002, REQ-SEC-001."""

from __future__ import annotations

import json

import pytest
from fakes import analysis as fa

from contentguard.analysis import validation
from contentguard.analysis.contracts import (
    AdvisoryResult,
    AnalysisFailure,
    Citation,
    Usage,
)
from contentguard.analysis.errors import ModelValidationError


def advisory_result(usage: Usage | None = None) -> AdvisoryResult:
    """Build an internal advisory DTO for projection tests (REQ-FUN-002)."""
    return AdvisoryResult(
        attempt=fa.make_attempt(),
        verdict="review",
        severity="high",
        rationale="grounded rationale",
        citations=(Citation("corpus-synthetic", 1, "c-01", 1, fa.canonical_digest("rule c-01 <TOKENS:8>")),),
        usage=usage or Usage(3, 2, False),
        known_severity="high",
    )


def test_advisory_projection_has_exactly_nine_s1_fields():
    """S1 projection contains exactly the nine advisory fields (REQ-FUN-002, REQ-INV-001)."""
    payload = advisory_result().to_s1_payload()
    assert set(payload) == {
        "role", "verdict", "severity", "rationale", "citations",
        "prompt_version", "model_id", "model_version", "usage",
    }


def test_advisory_projection_excludes_enforcement_fields():
    """S1 projection excludes action, outcome and enforcement metadata (REQ-INV-001, REQ-SEC-001)."""
    payload = advisory_result().to_s1_payload()
    for forbidden in ("action", "outcome", "enforcement", "actor", "privileges", "tools", "audit_id"):
        assert forbidden not in payload


def test_unknown_usage_never_masquerades_as_zero():
    """Unknown usage is explicit and distinct from real zero usage (REQ-COS-001)."""
    assert Usage(0, 0, True) != Usage(0, 0, False)
    with pytest.raises(ValueError):
        Usage(3, 0, True)


def test_parse_model_wire_accepts_strict_allowlist():
    """Valid model JSON parses without identity or authority fields (REQ-FUN-002, REQ-SEC-001)."""
    raw = json.dumps({"verdict": "review", "severity": "high", "rationale": "r", "citations": ["c-01@1"]})
    parsed = validation.parse_model_wire(raw)
    assert not isinstance(parsed, ModelValidationError)
    assert parsed.verdict == "review"


@pytest.mark.parametrize("field", ["action", "outcome", "enforcement", "actor", "privileges", "tools"])
def test_privileged_fields_rejected(field):
    """Any privileged field in model JSON is rejected (REQ-SEC-001, REQ-INV-001)."""
    payload = {"verdict": "review", "severity": "high", "rationale": "r", "citations": [], field: "x"}
    error = validation.assert_no_privileged_fields(payload)
    assert error is not None
    assert field in error.detail


def test_validate_advisory_returns_internal_dto():
    """Valid wire output becomes an internal advisory DTO (REQ-FUN-002, ADR-001)."""
    clause = fa.make_clause("c-01")
    snapshot = fa.build_snapshot((clause,))
    raw = json.dumps({"verdict": "review", "severity": "high", "rationale": "r", "citations": ["c-01@1"]})
    result = validation.validate_advisory(
        raw, (clause,), snapshot, fa.make_attempt(), Usage(3, 2, False), "high"
    )
    assert not isinstance(result, AnalysisFailure)
    assert result.verdict == "review"


@pytest.mark.parametrize(
    "raw",
    [
        '{"verdict": true, "severity": "high", "rationale": "r", "citations": []}',
        '{"verdict": "review", "severity": NaN, "rationale": "r", "citations": []}',
        '{"verdict": "review", "severity": "high", "rationale": true, "citations": []}',
        '{"verdict": "review", "severity": "high", "rationale": "r", "citations": [""]}',
        '{"verdict": "review", "severity": "high", "rationale": "r", "citations": [true]}',
    ],
)
def test_strict_shape_rejects_bool_nan_and_empty_citation(raw):
    """Strict model shape rejects booleans, NaN and empty citations (REQ-SEC-001, REQ-FUN-002)."""
    assert isinstance(validation.parse_model_wire(raw), ModelValidationError)
