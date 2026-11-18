"""Offline advisory analysis orchestration (ADR-001, REQ-FUN-002/005, REQ-INV-001..004).

Every public function cites its governing requirements.
"""

from __future__ import annotations

from dataclasses import replace

from . import context, retrieval, validation
from . import provider as provider_runtime
from .contracts import (
    AdvisoryResult,
    AnalysisFailure,
    AnalysisHandoff,
    ContextConfig,
    FailureCode,
    KnownSeverity,
    PolicySnapshot,
    ProviderRequest,
    RetrievalQuery,
    RetrievalResult,
    TrustedCapsule,
    Usage,
)
from .errors import DomainValidationError
from .ports import (
    ClockPort,
    ProviderPort,
    RetrieverPort,
    SnapshotSourcePort,
    TokenizerPort,
    TrustRegistryPort,
)
from .snapshot import load_snapshot, validate_approval, verify_corpus_digest


def _failure(
    detail: str,
    query: RetrievalQuery,
    trusted_severity: KnownSeverity,
    code: FailureCode = "grounding_unavailable",
) -> AnalysisFailure:
    """Create a failure bound to the original attempt and trusted severity (REQ-INV-002, REQ-INV-003)."""
    return AnalysisFailure(code, detail, query.attempt, Usage(0, 0, True), trusted_severity)


def _normalize_failure(
    failure: AnalysisFailure,
    query: RetrievalQuery,
    trusted_severity: KnownSeverity,
) -> AnalysisFailure:
    """Normalize every failure identity and severity, rejecting foreign identity (REQ-SEC-001, REQ-INV-002)."""
    if failure.attempt != query.attempt:
        return AnalysisFailure(
            failure.code,
            "transport failure identity mismatch",
            query.attempt,
            failure.usage,
            trusted_severity,
        )
    return replace(failure, attempt=query.attempt, known_severity=trusted_severity)


def _reverify_snapshot(
    snapshot: PolicySnapshot,
    grounded: RetrievalResult,
) -> PolicySnapshot | DomainValidationError:
    """Reverify a second snapshot load against the approved anchor and first digest (REQ-FUN-005, REQ-SEC-001)."""
    if (
        snapshot.snapshot_id != grounded.snapshot_id
        or snapshot.revision != grounded.snapshot_revision
        or snapshot.corpus_id != grounded.binding.corpus_id
    ):
        return DomainValidationError(
            "stale_snapshot", "reloaded snapshot mismatch", grounded.snapshot_id, grounded.snapshot_revision
        )
    approved = validate_approval(snapshot, grounded.binding)
    if isinstance(approved, DomainValidationError):
        return approved
    verified = verify_corpus_digest(snapshot, grounded.binding)
    if isinstance(verified, DomainValidationError):
        return verified
    if snapshot.corpus_digest != grounded.corpus_digest:
        return DomainValidationError(
            "digest_mismatch", "reloaded digest mismatch", snapshot.snapshot_id, snapshot.revision
        )
    return snapshot


async def analyze(
    query: RetrievalQuery,
    deadline_ms: int,
    known_severity: KnownSeverity,
    source: SnapshotSourcePort,
    registry: TrustRegistryPort,
    retriever: RetrieverPort,
    tokenizer: TokenizerPort,
    provider: ProviderPort,
    clock: ClockPort,
    capsule: TrustedCapsule,
    config: ContextConfig,
) -> AdvisoryResult | AnalysisFailure:
    """Run the advisory slice without enforcement or audit effects (REQ-INV-001)."""
    trusted = query.known_severity
    if known_severity != trusted:
        return _failure("known severity mismatch", query, trusted, "invalid_response")
    grounded = retrieval.retrieve(query, source, registry, retriever)
    if isinstance(grounded, AnalysisFailure):
        return _normalize_failure(grounded, query, trusted)
    loaded = load_snapshot(query.snapshot_id, query.snapshot_revision, source)
    if isinstance(loaded, DomainValidationError):
        return _failure(loaded.detail, query, trusted)
    reloaded = _reverify_snapshot(loaded, grounded)
    if isinstance(reloaded, DomainValidationError):
        return _failure(reloaded.detail, query, trusted)
    package = context.assemble_context(
        query.attempt,
        trusted,
        reloaded,
        grounded.clauses,
        capsule,
        config,
        tokenizer,
        submitted_text=query.text,
        critical_evidence=query.critical_evidence,
        history_refs=query.history_refs,
    )
    if isinstance(package, AnalysisFailure):
        return _normalize_failure(package, query, trusted)
    compacted = context.compact_context(
        package, config, tokenizer, query.attempt, trusted
    )
    if isinstance(compacted, AnalysisFailure):
        return _normalize_failure(compacted, query, trusted)
    reinjected = context.reinject_capsule(
        compacted, capsule, config, tokenizer, query.attempt, trusted
    )
    if isinstance(reinjected, AnalysisFailure):
        return _normalize_failure(reinjected, query, trusted)
    request = ProviderRequest(query.attempt, context.serialize_context(reinjected), config.output_tokens)
    response = await provider_runtime.invoke_provider(request, deadline_ms, clock, provider, config)
    if isinstance(response, AnalysisFailure):
        return _normalize_failure(response, query, trusted)
    validated = validation.validate_advisory(
        response.raw_json, tuple(reinjected.retained_clauses), reloaded, query.attempt, response.usage, trusted
    )
    if isinstance(validated, AnalysisFailure):
        return _normalize_failure(validated, query, trusted)
    return validated


def project_handoff(
    outcome: AdvisoryResult | AnalysisFailure,
    known_severity: KnownSeverity,
    critical_evidence: tuple[str, ...] = (),
) -> AnalysisHandoff:
    """Project advisory fields while preserving trusted evidence and severity (REQ-INV-003)."""
    if outcome.known_severity != known_severity:
        raise ValueError("conflicting known severity inputs")
    advisory_severity = outcome.severity if isinstance(outcome, AdvisoryResult) else None
    return AnalysisHandoff(
        outcome=outcome,
        severity_known=known_severity,
        severity_advisory=advisory_severity,
        attempt=outcome.attempt,
        preserved_critical_evidence=critical_evidence,
        final_disposition=None,
        audit_id=None,
        hold_committed=None,
    )
