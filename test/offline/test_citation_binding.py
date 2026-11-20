"""Strict citation grammar and trusted revision tests for REQ-FUN-005, REQ-SEC-001, REQ-INV-002."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace

from fakes import analysis as fa

from contentguard.analysis import context, validation
from contentguard.analysis.contracts import (
    AdvisoryResult,
    AnalysisFailure,
    AttemptIdentity,
    PolicyClause,
    PolicySnapshot,
    RetrievedClause,
    Usage,
)
from contentguard.analysis.service import analyze

CORPUS_REVISION = 7


def oversized_revision() -> str:
    """Return a 5000-digit revision that exceeds Python's int conversion limit (REQ-SEC-001)."""
    return "9" * 5000


def fixture_digest() -> str:
    """Return the canonical digest of the fixture clause text (REQ-FUN-005)."""
    return fa.canonical_digest("rule c-01 <TOKENS:8>")


def fixture_parts() -> tuple[PolicyClause, PolicySnapshot, AttemptIdentity]:
    """Build a clause, snapshot and attempt with unequal corpus revisions (REQ-FUN-005)."""
    clause = fa.make_clause("c-01")
    snapshot = fa.build_snapshot((clause,))
    return clause, snapshot, fa.make_attempt()


def full_citation(
    *,
    corpus_revision: int = CORPUS_REVISION,
    snapshot_id: str = "snap-synthetic-v1",
    snapshot_revision: int = 1,
    digest: str | None = None,
) -> str:
    """Build a canonical full-form citation from trusted fixture values (REQ-FUN-005)."""
    value = fixture_digest() if digest is None else digest
    return (
        f"corpus-synthetic@{corpus_revision}:{snapshot_id}@{snapshot_revision}:"
        f"c-01@1#{value}"
    )


def raw_response(citation: str) -> str:
    """Build a strict advisory response with one citation (REQ-FUN-002)."""
    return json.dumps({"verdict": "review", "severity": "high", "rationale": "r", "citations": [citation]})


def validate(raw: str, corpus_revision: int = CORPUS_REVISION) -> AdvisoryResult | AnalysisFailure:
    """Validate wire output against a trusted corpus revision (REQ-SEC-001)."""
    clause, snapshot, attempt = fixture_parts()
    return validation.validate_advisory(
        raw, (clause,), snapshot, attempt, Usage(3, 2, False), "high", corpus_revision=corpus_revision
    )


def test_full_form_citation_accepts_pinned_prefixes_and_exact_digest():
    """Full-form citations are accepted only with pinned prefixes and exact digest (REQ-FUN-005, REQ-SEC-001)."""
    result = validate(raw_response(full_citation()))
    assert not isinstance(result, AnalysisFailure)
    assert result.citations[0].corpus_id == "corpus-synthetic"
    assert result.citations[0].corpus_revision == CORPUS_REVISION
    assert result.citations[0].clause_digest == fixture_digest()


def test_short_form_citation_uses_trusted_corpus_revision():
    """Short-form citations remain valid but inherit the trusted corpus revision (REQ-FUN-005, REQ-INV-002)."""
    result = validate(raw_response("c-01@1"))
    assert not isinstance(result, AnalysisFailure)
    assert result.citations[0].corpus_revision == CORPUS_REVISION


def test_forged_corpus_and_snapshot_prefixes_are_rejected():
    """Forged corpus or snapshot prefixes are rejected, not parsed away (REQ-SEC-001, REQ-INV-002)."""
    forged = full_citation(corpus_revision=999, snapshot_id="snap-evil", snapshot_revision=999)
    result = validate(raw_response(forged))
    assert isinstance(result, AnalysisFailure)
    assert result.code == "invalid_response"


def test_full_form_corpus_revision_must_match_trusted_binding():
    """A full-form citation revision must match the trusted release binding (REQ-FUN-005, REQ-SEC-001)."""
    result = validate(raw_response(full_citation()), corpus_revision=8)
    assert isinstance(result, AnalysisFailure)
    assert result.code == "invalid_response"


def test_full_form_wrong_digest_is_rejected():
    """A full-form citation with a wrong digest is rejected (REQ-FUN-005, REQ-SEC-001)."""
    wrong = "sha256:" + "0" * 64
    result = validate(raw_response(full_citation(digest=wrong)))
    assert isinstance(result, AnalysisFailure)
    assert result.code == "invalid_response"


def test_noncanonical_revision_prefix_is_rejected():
    """Noncanonical zero-padded revisions do not bypass full-form validation (REQ-SEC-001, REQ-FUN-005)."""
    noncanonical = f"corpus-synthetic@07:snap-synthetic-v1@01:c-01@01#{fixture_digest()}"
    result = validate(raw_response(noncanonical))
    assert isinstance(result, AnalysisFailure)
    assert result.code == "invalid_response"


def test_oversized_full_form_revision_returns_typed_failure():
    """Oversized full-form revisions stay inside typed failures (REQ-FUN-002, REQ-SEC-001, REQ-INV-002)."""
    revision = oversized_revision()
    citation = f"corpus-synthetic@{revision}:snap-synthetic-v1@1:c-01@1#{fixture_digest()}"
    result = validate(raw_response(citation))
    assert isinstance(result, AnalysisFailure)
    assert result.code == "invalid_response"


def test_oversized_short_revision_returns_typed_failure_through_analyze():
    """Oversized short-form revisions stay inside typed failures through analyze (REQ-INV-002, REQ-SEC-001)."""
    revision = oversized_revision()
    _clause, snapshot, _ = fixture_parts()
    provider = fa.FakeProvider("normal", raw_json=raw_response(f"c-01@{revision}"))
    result = asyncio.run(
        analyze(
            fa.make_query(text="rule c-01"),
            2000,
            "high",
            fa.FakeSnapshotSource(snapshot),
            fa.FakeTrustRegistry(fa.make_anchor(snapshot)),
            fa.FakeRetriever(),
            fa.FakeTokenizer(),
            provider,
            fa.FakeClock(),
            fa.make_capsule(),
            fa.make_config(),
        )
    )
    assert isinstance(result, AnalysisFailure)
    assert result.code == "invalid_response"


def test_context_renders_distinct_trusted_corpus_revision():
    """Context renders corpus revision from the trusted binding, not snapshot revision (REQ-FUN-005, REQ-INV-002)."""
    clause, snapshot, attempt = fixture_parts()
    package = context.assemble_context(
        attempt,
        "high",
        snapshot,
        (RetrievedClause(clause, 1.0),),
        fa.make_capsule(),
        fa.make_config(),
        fa.FakeTokenizer(),
        corpus_revision=CORPUS_REVISION,
    )
    assert not isinstance(package, AnalysisFailure)
    serialized = context.serialize_context(package)
    assert "corpus: corpus-synthetic@7" in serialized
    assert "snapshot: snap-synthetic-v1@1" in serialized
    assert "corpus: corpus-synthetic@1" not in serialized


def test_analyze_binds_full_form_citation_to_trusted_corpus_revision():
    """Analyze passes the trusted corpus revision to context and citation validation (REQ-FUN-005, REQ-SEC-001)."""
    _clause, snapshot, _ = fixture_parts()
    anchor = replace(fa.make_anchor(snapshot), corpus_revision=CORPUS_REVISION)
    query = fa.make_query(text="rule c-01", corpus_revision=CORPUS_REVISION)
    provider = fa.FakeProvider("normal", raw_json=raw_response(full_citation()))
    result = asyncio.run(
        analyze(
            query,
            2000,
            "high",
            fa.FakeSnapshotSource(snapshot),
            fa.FakeTrustRegistry(anchor),
            fa.FakeRetriever(),
            fa.FakeTokenizer(),
            provider,
            fa.FakeClock(),
            fa.make_capsule(),
            fa.make_config(),
        )
    )
    assert not isinstance(result, AnalysisFailure)
    assert result.citations[0].corpus_revision == CORPUS_REVISION
    assert len(provider.calls) == 1
    assert "corpus: corpus-synthetic@7" in provider.calls[0].serialized_context
