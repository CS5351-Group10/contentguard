"""Context budget tests for ADR-001, REQ-COS-001, REQ-INV-001."""

from __future__ import annotations

from fakes import analysis as fa

from contentguard.analysis import context
from contentguard.analysis.contracts import (
    AnalysisFailure,
    ContextPackage,
    RetrievedClause,
)


def retrieved(clause_tokens: int, clause_id: str = "c-01") -> tuple[RetrievedClause, ...]:
    """Build one retrieved clause for context tests (REQ-FUN-005)."""
    return (RetrievedClause(fa.make_clause(clause_id, tokens=clause_tokens), 1.0),)


def test_fits_budget_returns_recounted_package():
    """A small clause set assembles with recounted tokens (REQ-COS-001, ADR-001)."""
    clauses = (fa.make_clause("c-01", tokens=8),)
    snapshot = fa.build_snapshot(clauses)
    config = fa.make_config()
    package = context.assemble_context(
        fa.make_attempt(), "high", snapshot, retrieved(8), fa.make_capsule(), config, fa.FakeTokenizer(),
        corpus_revision=fa.make_anchor(snapshot).corpus_revision,
    )
    assert not isinstance(package, AnalysisFailure)
    assert 8 <= package.total_input_tokens <= config.input_cap_tokens


def test_input_cap_failure_is_typed():
    """Uncompactable input overflow yields context_overflow, never truncation (REQ-INV-001)."""
    clauses = (fa.make_clause("c-01", tokens=40),)
    snapshot = fa.build_snapshot(clauses)
    config = fa.make_config(input_cap_tokens=30, compaction_trigger_tokens=20)
    package = context.assemble_context(
        fa.make_attempt(), "high", snapshot, retrieved(40), fa.make_capsule(), config, fa.FakeTokenizer(),
        corpus_revision=fa.make_anchor(snapshot).corpus_revision,
    )
    assert not isinstance(package, AnalysisFailure)
    result = context.compact_context(
        package, config, fa.FakeTokenizer(), package.attempt, "high"
    )
    assert isinstance(result, AnalysisFailure)
    assert result.code == "context_overflow"


def test_serialized_context_stays_within_provider_limit():
    """Serialized context respects the provider limit (REQ-COS-001, ADR-001)."""
    clauses = (fa.make_clause("c-01", tokens=8),)
    snapshot = fa.build_snapshot(clauses)
    config = fa.make_config(input_cap_tokens=40, compaction_trigger_tokens=20)
    package = context.assemble_context(
        fa.make_attempt(), "high", snapshot, retrieved(8), fa.make_capsule(), config, fa.FakeTokenizer(),
        corpus_revision=fa.make_anchor(snapshot).corpus_revision,
    )
    assert not isinstance(package, AnalysisFailure)
    assert fa.FakeTokenizer().count_tokens(context.serialize_context(package)) <= config.provider_context_limit_tokens


def test_clause_text_is_never_truncated():
    """Compaction drops whole clauses only; it never truncates clause text (REQ-INV-001)."""
    clauses = (fa.make_clause("c-01", tokens=8), fa.make_clause("c-02", tokens=8))
    snapshot = fa.build_snapshot(clauses)
    package = context.assemble_context(
        fa.make_attempt(), "high", snapshot,
        (RetrievedClause(clauses[0], 1.0), RetrievedClause(clauses[1], 0.5)),
        fa.make_capsule(), fa.make_config(), fa.FakeTokenizer(),
        corpus_revision=fa.make_anchor(snapshot).corpus_revision,
    )
    assert isinstance(package, ContextPackage)
    compacted = context.compact_context(
        package, fa.make_config(), fa.FakeTokenizer(), fa.make_attempt(), "high"
    )
    assert not isinstance(compacted, AnalysisFailure)
    assert all(section.kind != "policy_clause" or section.token_count in (0, 8) for section in compacted.sections)
