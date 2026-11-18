"""Compaction invariant tests for ADR-001, REQ-INV-003, REQ-INV-005, REQ-SEC-001."""

from __future__ import annotations

from fakes import analysis as fa

from contentguard.analysis import context
from contentguard.analysis.contracts import (
    AnalysisFailure,
    ContextPackage,
    RetrievedClause,
)


def package_with_evidence() -> ContextPackage:
    """Build a package carrying evidence and history for invariant tests (REQ-INV-003)."""
    clauses = (fa.make_clause("c-01", tokens=8), fa.make_clause("c-02", tokens=8))
    snapshot = fa.build_snapshot(clauses)
    package = context.assemble_context(
        fa.make_attempt(), "high", snapshot,
        (RetrievedClause(clauses[0], 1.0), RetrievedClause(clauses[1], 0.5)),
        fa.make_capsule(), fa.make_config(), fa.FakeTokenizer(),
        critical_evidence=("evidence-A",), history_refs=("h-1",),
    )
    assert not isinstance(package, AnalysisFailure)
    return package


def test_critical_evidence_and_history_survive_compaction():
    """Critical evidence, history and case revision survive compaction (REQ-INV-003)."""
    original = package_with_evidence()
    compacted = context.compact_context(
        original, fa.make_config(), fa.FakeTokenizer(), original.attempt, "high"
    )
    assert not isinstance(compacted, AnalysisFailure)
    assert compacted.preserved_critical_evidence == ("evidence-A",)
    assert compacted.preserved_history_refs == ("h-1",)
    assert compacted.case_revision == original.case_revision


def test_capsule_reinjected_after_compaction():
    """Behavior-affecting capsule is reinjected after compaction (REQ-INV-005, REQ-INV-003)."""
    original = package_with_evidence()
    compacted = context.compact_context(
        original, fa.make_config(), fa.FakeTokenizer(), original.attempt, "high"
    )
    assert not isinstance(compacted, AnalysisFailure)
    reinjected = context.reinject_capsule(
        compacted, fa.make_capsule(), fa.make_config(), fa.FakeTokenizer(), original.attempt, "high"
    )
    assert not isinstance(reinjected, AnalysisFailure)
    assert any(section.kind == "safety_capsule" for section in reinjected.sections)


def test_known_severity_survives_compaction():
    """Known severity is preserved through context compaction (REQ-INV-003, ADR-001)."""
    original = package_with_evidence()
    compacted = context.compact_context(
        original, fa.make_config(), fa.FakeTokenizer(), original.attempt, "high"
    )
    assert not isinstance(compacted, AnalysisFailure)
    assert compacted.known_severity == "high"
