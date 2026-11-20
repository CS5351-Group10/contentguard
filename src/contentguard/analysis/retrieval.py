"""Grounded deterministic retrieval (ADR-001, REQ-FUN-005, REQ-INV-001/002).

Every public function cites its governing requirements.
"""

from __future__ import annotations

from .contracts import (
    AnalysisFailure,
    KnownSeverity,
    PolicySnapshot,
    RetrievalQuery,
    RetrievalResult,
    Usage,
)
from .errors import DomainValidationError
from .ports import RetrieverPort, SnapshotSourcePort, TrustRegistryPort
from .snapshot import (
    canonical_clause_digest,
    canonical_text,
    load_snapshot,
    lookup_trust_anchor,
    validate_approval,
    verify_corpus_digest,
)


def retrieve(
    query: RetrievalQuery,
    source: SnapshotSourcePort,
    registry: TrustRegistryPort,
    retriever: RetrieverPort,
) -> RetrievalResult | AnalysisFailure:
    """Retrieve provenance-valid clauses or a typed grounding failure (REQ-FUN-005)."""
    usage = Usage(0, 0, True)

    def fail(detail: str) -> AnalysisFailure:
        """Create a grounding failure preserving trusted severity (REQ-INV-002, REQ-INV-003)."""
        return AnalysisFailure("grounding_unavailable", detail, query.attempt, usage, query.known_severity)

    snapshot = load_snapshot(query.snapshot_id, query.snapshot_revision, source)
    if isinstance(snapshot, DomainValidationError):
        return fail(snapshot.detail)
    if query.corpus_id != snapshot.corpus_id:
        return fail("corpus id mismatch")
    anchor = lookup_trust_anchor(query.corpus_id, query.corpus_revision, registry)
    if isinstance(anchor, DomainValidationError):
        return fail(anchor.detail)
    approved = validate_approval(snapshot, anchor)
    if isinstance(approved, DomainValidationError):
        return fail(approved.detail)
    verified = verify_corpus_digest(snapshot, anchor)
    if isinstance(verified, DomainValidationError):
        return fail(verified.detail)
    try:
        ranked = retriever.retrieve(query, snapshot.clauses)
    except (RuntimeError, ValueError, TypeError, OSError) as exc:
        return fail(f"retriever error: {type(exc).__name__}")
    if isinstance(ranked, AnalysisFailure):
        if ranked.attempt != query.attempt:
            return fail("retriever failure identity mismatch")
        return AnalysisFailure(ranked.code, ranked.detail, query.attempt, ranked.usage, query.known_severity)
    if not ranked:
        return fail("no grounded clause available")
    seen: set[tuple[str, int]] = set()
    unique = []
    for item in ranked:
        key = (item.clause.clause_id, item.clause.clause_revision)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    result = RetrievalResult(
        attempt=query.attempt,
        snapshot_id=snapshot.snapshot_id,
        snapshot_revision=snapshot.revision,
        binding=anchor,
        corpus_digest=snapshot.corpus_digest,
        clauses=tuple(unique),
    )
    return validate_provenance(result, snapshot, query.known_severity)


def validate_provenance(
    result: RetrievalResult,
    snapshot: PolicySnapshot,
    known_severity: KnownSeverity = "unknown",
) -> RetrievalResult | AnalysisFailure:
    """Validate every clause field against pinned metadata (REQ-FUN-005, REQ-SEC-001)."""

    def fail(detail: str) -> AnalysisFailure:
        """Create a provenance failure with trusted severity (REQ-INV-002, REQ-INV-003)."""
        return AnalysisFailure(
            "grounding_unavailable", detail, result.attempt, Usage(0, 0, True), known_severity
        )

    if result.snapshot_id != snapshot.snapshot_id or result.snapshot_revision != snapshot.revision:
        return fail("snapshot provenance mismatch")
    clause_map = {
        (clause.clause_id, clause.clause_revision): clause
        for clause in snapshot.clauses
    }
    for item in result.clauses:
        pinned = clause_map.get((item.clause.clause_id, item.clause.clause_revision))
        if pinned is None:
            return fail("clause provenance mismatch")
        if (
            canonical_text(pinned.text) != canonical_text(item.clause.text)
            or pinned.category != item.clause.category
            or pinned.severity_hint != item.clause.severity_hint
            or pinned.source_ref != item.clause.source_ref
            or pinned.clause_digest != item.clause.clause_digest
            or item.clause.clause_digest != canonical_clause_digest(item.clause.text)
            or pinned.clause_digest != canonical_clause_digest(pinned.text)
        ):
            return fail("clause provenance mismatch")
    return result
