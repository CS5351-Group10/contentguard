"""Second-pass Codex review regression tests for ADR-001, REQ-COS-001, REQ-FUN-005, REQ-SEC-001."""

from __future__ import annotations

import asyncio
import hashlib
import json
import unicodedata
from typing import Any, cast

import pytest
from fakes import analysis as fa

from contentguard.analysis import context, retrieval, snapshot
from contentguard.analysis.contracts import (
    AnalysisFailure,
    KnownSeverity,
    PolicyClause,
    RetrievedClause,
)
from contentguard.analysis.service import analyze


def canonical_digest(text: str) -> str:
    """Compute the expected NFC/CRLF-normalized clause digest (REQ-FUN-005)."""
    normalized = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def valid_raw() -> str:
    """Return a strict advisory response citing the first clause (REQ-FUN-002)."""
    return json.dumps({"verdict": "review", "severity": "high", "rationale": "r", "citations": ["c-01@1"]})


def run_analyze(**overrides: Any) -> AnalysisFailure | object:
    """Run analyze with injected failure-mode fakes (REQ-FUN-002, REQ-FUN-005)."""
    clauses = (fa.make_clause("c-01"),)
    snapshot_artifact = fa.build_snapshot(clauses)
    query = fa.make_query(text="rule c-01")
    provider = fa.FakeProvider(str(overrides.get("provider_mode", "normal")), raw_json=valid_raw())
    retriever = fa.FakeRetriever(str(overrides.get("retriever_mode", "normal")))
    source = overrides.get("source", fa.FakeSnapshotSource(snapshot_artifact))
    return asyncio.run(
        analyze(
            query,
            2000,
            cast(KnownSeverity, overrides.get("known_severity", "high")),
            source,
            fa.FakeTrustRegistry(fa.make_anchor(snapshot_artifact)),
            retriever,
            fa.FakeTokenizer(),
            provider,
            fa.FakeClock(),
            fa.make_capsule(),
            fa.make_config(),
        )
    )


def test_non_power_of_two_envelope_and_larger_provider_limit_are_accepted():
    """Valid envelope values are not constrained to powers of two (REQ-COS-001)."""
    config = fa.make_config(
        envelope_tokens=9000,
        input_cap_tokens=6000,
        output_tokens=1000,
        reserve_tokens=1000,
        provider_context_limit_tokens=10000,
        compaction_trigger_tokens=4608,
    )
    clauses = (fa.make_clause("c-01", tokens=8),)
    snapshot = fa.build_snapshot(clauses)
    package = context.assemble_context(
        fa.make_attempt(), "high", snapshot,
        (RetrievedClause(clauses[0], 1.0),),
        fa.make_capsule(), config, fa.FakeTokenizer(),
        corpus_revision=fa.make_anchor(snapshot).corpus_revision,
    )
    assert not isinstance(package, AnalysisFailure)


def test_severity_mismatch_is_rejected_before_retrieval():
    """Trusted severity mismatch stops analysis before retrieval or provider use (REQ-INV-003)."""
    retriever = fa.FakeRetriever()
    provider = fa.FakeProvider("normal", raw_json=valid_raw())
    clauses = (fa.make_clause("c-01"),)
    snapshot_artifact = fa.build_snapshot(clauses)
    result = asyncio.run(
        analyze(
            fa.make_query(text="rule c-01"), 2000, "low",
            fa.FakeSnapshotSource(snapshot_artifact),
            fa.FakeTrustRegistry(fa.make_anchor(snapshot_artifact)),
            retriever, fa.FakeTokenizer(), provider, fa.FakeClock(),
            fa.make_capsule(), fa.make_config(),
        )
    )
    assert isinstance(result, AnalysisFailure)
    assert result.known_severity == "high"
    assert retriever.calls == 0
    assert provider.calls == []


def test_forged_retrieval_failure_is_normalized_to_trusted_identity():
    """A forged retrieval failure never leaks foreign identity or severity (REQ-INV-002, REQ-SEC-001)."""
    result = run_analyze(retriever_mode="forged_failure")
    assert isinstance(result, AnalysisFailure)
    assert result.attempt == fa.make_attempt()
    assert result.known_severity == "high"


def test_forged_provider_failure_is_rejected_and_normalized():
    """A provider failure with a foreign attempt is rejected and normalized (REQ-SEC-001, REQ-INV-002)."""
    result = run_analyze(provider_mode="forged_failure")
    assert isinstance(result, AnalysisFailure)
    assert result.attempt == fa.make_attempt()
    assert result.known_severity == "high"


def test_swapped_snapshot_on_second_load_is_rejected():
    """A second-load snapshot swap cannot reach context or provider (REQ-FUN-005, REQ-SEC-001)."""
    first = fa.build_snapshot((fa.make_clause("c-01", text="rule c-01 first"),))
    second = fa.build_snapshot((fa.make_clause("c-01", text="rule c-01 second"),))
    source = fa.SwappingSnapshotSource(first, second)
    provider = fa.FakeProvider("normal", raw_json=valid_raw())
    query = fa.make_query(text="rule c-01")
    result = asyncio.run(
        analyze(
            query, 2000, "high", source, fa.FakeTrustRegistry(fa.make_anchor(first)),
            fa.FakeRetriever(), fa.FakeTokenizer(), provider, fa.FakeClock(),
            fa.make_capsule(), fa.make_config(),
        )
    )
    assert isinstance(result, AnalysisFailure)
    assert result.code == "grounding_unavailable"
    assert result.attempt == query.attempt
    assert result.known_severity == "high"
    assert provider.calls == []


def test_unicode_canonicalization_accepts_equivalent_clause_text():
    """Canonical NFC/CRLF clause text uses the shared digest helper (REQ-FUN-005, REQ-SEC-001)."""
    text = "rule café\r\nsecond line"
    clause = PolicyClause(
        clause_id="c-01",
        clause_revision=1,
        text=text,
        category="safety",
        severity_hint="medium",
        source_ref="synthetic://clauses/c-01/1",
        clause_digest=canonical_digest(text),
    )
    artifact = fa.build_snapshot((clause,))
    query = fa.make_query(text="rule café")
    result = retrieval.retrieve(
        query, fa.FakeSnapshotSource(artifact), fa.FakeTrustRegistry(fa.make_anchor(artifact)), fa.FakeRetriever()
    )
    assert not isinstance(result, AnalysisFailure)
    assert snapshot.canonical_clause_digest(text) == clause.clause_digest


@pytest.mark.parametrize("mode", ["category", "severity_hint"])
def test_retrieval_rejects_metadata_mismatch_and_preserves_severity(mode):
    """Clauses with tampered category or severity metadata fail as grounded high-severity failures (REQ-SEC-001)."""
    artifact = fa.build_snapshot((fa.make_clause("c-01"),))
    query = fa.make_query(text="rule c-01")
    result = retrieval.retrieve(
        query,
        fa.FakeSnapshotSource(artifact),
        fa.FakeTrustRegistry(fa.make_anchor(artifact)),
        fa.TamperingRetriever(mode),
    )
    assert isinstance(result, AnalysisFailure)
    assert result.attempt == query.attempt
    assert result.known_severity == "high"
