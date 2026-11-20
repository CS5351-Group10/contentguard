"""Strict model JSON validation and citation checks (ADR-001, REQ-FUN-002, REQ-SEC-001).

Every public function cites its governing requirements.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import cast

from .contracts import (
    AdvisoryResult,
    AdvisorySeverity,
    AnalysisFailure,
    AttemptIdentity,
    Citation,
    KnownSeverity,
    ModelWireResponse,
    PolicyClause,
    PolicySnapshot,
    Usage,
    Verdict,
    encode_citation,
    parse_full_citation,
    parse_short_citation,
)
from .errors import ModelValidationError
from .snapshot import canonical_clause_digest

_ALLOWED = frozenset({"verdict", "severity", "rationale", "citations"})
_FORBIDDEN = frozenset({
    "action", "outcome", "enforcement", "actor", "privileges", "tools", "hold", "audit_id",
    "case_id", "case_revision", "snapshot_id", "prompt_version", "model_id", "model_version",
    "role", "usage", "attempt_id",
})
_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def assert_no_privileged_fields(payload: Mapping[str, object]) -> ModelValidationError | None:
    """Reject any identity, enforcement or authority field from model JSON (REQ-SEC-001)."""
    for key in sorted(_FORBIDDEN & set(payload)):
        return ModelValidationError("invalid_response", f"privileged field: {key}")
    return None


def parse_model_wire(raw_json: str) -> ModelWireResponse | ModelValidationError:
    """Parse only the strict advisory wire allowlist (REQ-FUN-002, REQ-SEC-001)."""
    try:
        payload = json.loads(raw_json)
    except (TypeError, ValueError) as exc:
        return ModelValidationError("invalid_response", f"invalid json: {type(exc).__name__}")
    if not isinstance(payload, dict):
        return ModelValidationError("invalid_response", "payload must be object")
    privileged = assert_no_privileged_fields(payload)
    if privileged is not None:
        return privileged
    extra = sorted(set(payload) - _ALLOWED)
    if extra:
        return ModelValidationError("invalid_response", f"unexpected field: {extra[0]}")
    missing = sorted(_ALLOWED - set(payload))
    if missing:
        return ModelValidationError("invalid_response", f"missing field: {missing[0]}")
    verdict = payload["verdict"]
    severity = payload["severity"]
    rationale = payload["rationale"]
    citations = payload["citations"]
    if not isinstance(verdict, str) or verdict not in {"allow", "review", "violate"}:
        return ModelValidationError("invalid_response", "invalid verdict")
    if not isinstance(severity, str) or severity not in _SEVERITY_ORDER:
        return ModelValidationError("invalid_response", "invalid severity")
    if not isinstance(rationale, str) or not rationale.strip():
        return ModelValidationError("invalid_response", "rationale required")
    if not isinstance(citations, (list, tuple)) or not all(isinstance(item, str) and item for item in citations):
        return ModelValidationError("invalid_response", "citations must be non-empty strings")
    return ModelWireResponse(
        verdict=cast(Verdict, verdict),
        severity=cast(AdvisorySeverity, severity),
        rationale=rationale,
        citations=tuple(citations),
    )


def validate_advisory(
    raw_json: str,
    supplied_clauses: tuple[PolicyClause, ...],
    snapshot: PolicySnapshot,
    attempt: AttemptIdentity,
    usage: Usage,
    known_severity: KnownSeverity,
    *,
    corpus_revision: int,
) -> AdvisoryResult | AnalysisFailure:
    """Return an internal advisory DTO or a typed failure (REQ-FUN-002, REQ-INV-002)."""
    parsed = parse_model_wire(raw_json)
    if isinstance(parsed, ModelValidationError):
        return AnalysisFailure("invalid_response", parsed.detail, attempt, usage, known_severity)
    if known_severity in _SEVERITY_ORDER and _SEVERITY_ORDER[parsed.severity] < _SEVERITY_ORDER[known_severity]:
        return AnalysisFailure(
            "invalid_response", "advisory severity cannot lower known severity", attempt, usage, known_severity
        )
    pinned = {
        (clause.clause_id, clause.clause_revision): clause
        for clause in snapshot.clauses
    }
    citations: list[Citation] = []
    for raw in parsed.citations:
        full = parse_full_citation(raw)
        if full is not None:
            if (
                full.corpus_id != snapshot.corpus_id
                or full.corpus_revision != corpus_revision
                or full.snapshot_id != snapshot.snapshot_id
                or full.snapshot_revision != snapshot.revision
                or full.snapshot_id != attempt.snapshot_id
                or full.snapshot_revision != attempt.snapshot_revision
            ):
                return AnalysisFailure(
                    "invalid_response", f"invalid citation prefix: {raw}", attempt, usage, known_severity
                )
            key = (full.clause_id, full.clause_revision)
        else:
            short = parse_short_citation(raw)
            if short is None:
                return AnalysisFailure("invalid_response", f"invalid citation: {raw}", attempt, usage, known_severity)
            key = short
        clause = pinned.get(key)
        if clause is None or clause not in supplied_clauses:
            return AnalysisFailure("invalid_response", f"unknown citation: {raw}", attempt, usage, known_severity)
        expected = canonical_clause_digest(clause.text)
        if clause.clause_digest != expected:
            return AnalysisFailure("invalid_response", f"tampered citation: {raw}", attempt, usage, known_severity)
        if full is not None:
            canonical = encode_citation(
                clause, snapshot.snapshot_id, snapshot.revision, snapshot.corpus_id, corpus_revision
            )
            if raw != canonical:
                return AnalysisFailure("invalid_response", f"invalid citation: {raw}", attempt, usage, known_severity)
        citations.append(
            Citation(
                corpus_id=snapshot.corpus_id,
                corpus_revision=corpus_revision,
                clause_id=clause.clause_id,
                clause_revision=clause.clause_revision,
                clause_digest=clause.clause_digest,
            )
        )
    return AdvisoryResult(
        attempt=attempt,
        verdict=parsed.verdict,
        severity=parsed.severity,
        rationale=parsed.rationale,
        citations=tuple(citations),
        usage=usage,
        known_severity=known_severity,
    )
