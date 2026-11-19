"""Handoff and failure-mapping tests for ADR-001, REQ-INV-001..004."""

from __future__ import annotations

import asyncio
import json

import pytest
from fakes import analysis as fa

from contentguard.analysis.contracts import AdvisoryResult, AnalysisFailure, Usage
from contentguard.analysis.service import analyze, project_handoff


def run_analyze(
    retriever_mode: str = "normal",
    provider_mode: str = "normal",
    raw_json: str | None = None,
):
    """Run the advisory slice with deterministic injectors (REQ-FUN-002, REQ-FUN-005)."""
    clauses = (fa.make_clause("c-01"), fa.make_clause("c-02"))
    snapshot = fa.build_snapshot(clauses)
    query = fa.make_query(text="rule c-01 text")
    return asyncio.run(
        analyze(
            query,
            2000,
            "high",
            fa.FakeSnapshotSource(snapshot),
            fa.FakeTrustRegistry(fa.make_anchor(snapshot)),
            fa.FakeRetriever(retriever_mode),
            fa.FakeTokenizer(),
            fa.FakeProvider(provider_mode, raw_json=raw_json),
            fa.FakeClock(),
            fa.make_capsule(),
            fa.make_config(),
        )
    )


def test_analyze_returns_advisory_result_on_valid_path():
    """Valid path returns an internal AdvisoryResult without enforcement (REQ-FUN-002, REQ-INV-001)."""
    result = run_analyze()
    assert isinstance(result, AdvisoryResult)
    assert result.verdict == "review"


@pytest.mark.parametrize(
    ("field", "value"),
    [("verdict", []), ("verdict", {}), ("severity", []), ("severity", {})],
)
def test_analyze_returns_typed_failure_for_unhashable_wire_fields(field, value):
    """Unhashable wire fields produce typed failures across analyze (REQ-FUN-002, REQ-INV-002)."""
    payload = {"verdict": "review", "severity": "high", "rationale": "r", "citations": []}
    payload[field] = value
    result = run_analyze(raw_json=json.dumps(payload))
    assert isinstance(result, AnalysisFailure)
    assert result.code == "invalid_response"


def test_grounding_failure_preserves_known_severity():
    """Grounding failure preserves the trusted known severity (REQ-INV-003, REQ-INV-002)."""
    result = run_analyze(retriever_mode="no_match")
    assert isinstance(result, AnalysisFailure)
    assert result.code == "grounding_unavailable"
    assert result.known_severity == "high"


def test_failure_payload_has_only_code_and_detail():
    """S1 receives only failure code and detail (REQ-INV-002, REQ-INV-001)."""
    failure = AnalysisFailure("timeout", "deadline", fa.make_attempt(), Usage(0, 0, True), "high")
    assert set(failure.to_s1_payload()) == {"code", "detail"}


def test_handoff_has_no_disposition_or_audit_fields():
    """Handoff contains no disposition, audit id, hold or tools (REQ-INV-001..004)."""
    failure = AnalysisFailure("timeout", "deadline", fa.make_attempt(), Usage(0, 0, True), "high")
    handoff = project_handoff(failure, "high")
    assert handoff.final_disposition is None
    assert handoff.audit_id is None
    assert handoff.hold_committed is None
    assert handoff.severity_known == "high"
