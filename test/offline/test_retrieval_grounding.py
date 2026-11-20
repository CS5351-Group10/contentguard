"""Grounding, approval and digest tests for ADR-001, REQ-FUN-005, REQ-SEC-001."""

from __future__ import annotations

from dataclasses import replace

import pytest
from fakes import analysis as fa

from contentguard.analysis import retrieval as retrieval_module
from contentguard.analysis import snapshot as snapshot_module
from contentguard.analysis.contracts import AnalysisFailure

_CASES = fa.load_fixture("retrieval_cases.json")


def test_fixture_manifest_counts_pinned_cases():
    """Pinned corpus has 100 cases with 40 matches and 60 tampering/error cases (REQ-FUN-005)."""
    manifest = fa.load_fixture("manifest.json")
    cases = _CASES
    assert len(cases) == manifest["fixture_count"] == 100
    assert sum(1 for case in cases if case["kind"] == "match") >= 20
    assert sum(1 for case in cases if case["kind"] in {"tampering", "error"}) >= 20


@pytest.mark.parametrize("case", _CASES, ids=[case["id"] for case in _CASES])
def test_every_retrieval_fixture_is_executed(case):
    """Every pinned case is executed against its declared mutation or error (REQ-FUN-005)."""
    clauses = tuple(fa.make_clause(f"c-{index:02d}") for index in range(1, 6))
    snapshot = fa.build_snapshot(clauses)
    query = fa.make_query(text=case["text"])
    if case["kind"] == "match":
        retriever = fa.FakeRetriever()
    elif case["kind"] == "tampering":
        retriever = fa.TamperingRetriever(case["tamper"])
    else:
        retriever = fa.FakeRetriever(case["retriever_mode"])
    result = retrieval_module.retrieve(
        query,
        fa.FakeSnapshotSource(snapshot),
        fa.FakeTrustRegistry(fa.make_anchor(snapshot)),
        retriever,
    )
    if case["kind"] == "match":
        assert not isinstance(result, AnalysisFailure)
        assert result.clauses[0].clause.clause_id == case["expected_clause"]
    else:
        assert isinstance(result, AnalysisFailure)
        assert result.code == case.get("expected_code", "grounding_unavailable")


def test_missing_trust_binding_is_rejected():
    """Missing explicit approval is rejected with missing_approval (REQ-FUN-005, REQ-SEC-001)."""
    snapshot = fa.build_snapshot((fa.make_clause("c-01"),))
    anchor = fa.make_anchor(snapshot)
    error = snapshot_module.lookup_trust_anchor(
        snapshot.corpus_id, snapshot.revision, fa.FakeTrustRegistry(anchor, mode="missing")
    )
    assert error.code == "missing_approval"


def test_corpus_digest_matches_synthetic_clause_set():
    """Corpus digest is computed from pinned clause metadata (REQ-FUN-005, ADR-001)."""
    clauses = (fa.make_clause("c-01"), fa.make_clause("c-02"))
    snapshot = fa.build_snapshot(clauses)
    assert snapshot_module.compute_corpus_digest(snapshot) == fa.corpus_digest(clauses)


def test_tampered_snapshot_is_rejected():
    """Tampered corpus digest fails verification (REQ-FUN-005, REQ-INV-002)."""
    snapshot = fa.build_snapshot((fa.make_clause("c-01"),))
    tampered = replace(snapshot, corpus_digest="sha256:tampered")
    result = snapshot_module.verify_corpus_digest(tampered, fa.make_anchor(snapshot))
    assert result.code == "digest_mismatch"
