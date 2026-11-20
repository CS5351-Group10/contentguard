"""Immutable analysis DTOs for ADR-001, REQ-FUN-002, REQ-FUN-005 and REQ-SEC-001."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

Role = Literal["initial_review"]
ApprovalStatus = Literal["approved", "unapproved", "unknown"]
Verdict = Literal["allow", "review", "violate"]
AdvisorySeverity = Literal["low", "medium", "high"]
KnownSeverity = Literal["low", "medium", "high", "unknown"]
FailureCode = Literal[
    "provider_unavailable",
    "timeout",
    "invalid_response",
    "grounding_unavailable",
    "context_overflow",
]
DomainErrorCode = Literal[
    "missing_approval",
    "invalid_approval_status",
    "approval_reference_mismatch",
    "digest_mismatch",
    "missing_corpus",
    "stale_snapshot",
    "conflicting_metadata",
]
ContextSectionKind = Literal[
    "identity_schema",
    "safety_capsule",
    "citation_rules",
    "submitted_content",
    "policy_clause",
    "critical_evidence",
    "content_history",
    "resumable_state",
    "delimiter",
]

_FULL_CITATION_RE = re.compile(
    r"(?P<corpus_id>[^@:#\s]+)@(?P<corpus_revision>[0-9]+):"
    r"(?P<snapshot_id>[^@:#\s]+)@(?P<snapshot_revision>[0-9]+):"
    r"(?P<clause_id>[^@:#\s]+)@(?P<clause_revision>[0-9]+)"
    r"#(?P<clause_digest>sha256:[0-9a-f]{64})"
)
_SHORT_CITATION_RE = re.compile(
    r"(?P<clause_id>[^@:#\s]+)@(?P<clause_revision>[0-9]+)"
)


@dataclass(frozen=True)
class Usage:
    """Provider usage; unknown is a flag, never zero (REQ-COS-001, ADR-001)."""

    input_tokens: int
    output_tokens: int
    usage_unknown: bool

    def __post_init__(self) -> None:
        if self.usage_unknown and (self.input_tokens != 0 or self.output_tokens != 0):
            raise ValueError("unknown usage must have zero counts")
        if not self.usage_unknown and (self.input_tokens < 0 or self.output_tokens < 0):
            raise ValueError("reported usage counts must be non-negative")


@dataclass(frozen=True)
class ApprovalRecord:
    """Explicit snapshot approval status; no default approval (REQ-FUN-005, REQ-SEC-001)."""

    status: ApprovalStatus
    approver_ref: str
    approval_revision: str
    evidence_ref: str
    approved_at: str


@dataclass(frozen=True)
class TrustAnchor:
    """Synthetic release binding pinning corpus and policy artifacts (REQ-FUN-005, ADR-001)."""

    corpus_id: str
    corpus_revision: int
    approved_corpus_digest: str
    approval_reference: str
    status: ApprovalStatus
    policy_snapshot_id: str
    policy_snapshot_digest: str
    approved_by: str
    approved_at: str
    registry_version: str


@dataclass(frozen=True)
class AttemptIdentity:
    """Adapter-owned identity metadata; model JSON cannot supply it (REQ-SEC-001, ADR-001)."""

    attempt_id: str
    case_id: str
    case_revision: int
    snapshot_id: str
    snapshot_revision: int
    prompt_version: str
    model_id: str
    model_version: str
    tokenizer_id: str
    contract_version: str
    role: Role


@dataclass(frozen=True)
class PolicyClause:
    """One complete approved corpus clause with pinned digest (REQ-FUN-005)."""

    clause_id: str
    clause_revision: int
    text: str
    category: str
    severity_hint: AdvisorySeverity
    source_ref: str
    clause_digest: str


@dataclass(frozen=True)
class PolicySnapshot:
    """Synthetic approved-status corpus snapshot; approval is explicit (REQ-FUN-005, REQ-SEC-001)."""

    snapshot_id: str
    revision: int
    corpus_id: str
    approval: ApprovalRecord
    corpus_digest: str
    clauses: tuple[PolicyClause, ...]


@dataclass(frozen=True)
class RetrievalQuery:
    """Grounding request carrying trusted severity, evidence and history (REQ-FUN-005, REQ-INV-003)."""

    attempt: AttemptIdentity
    text: str
    snapshot_id: str
    snapshot_revision: int
    corpus_id: str
    corpus_revision: int
    known_severity: KnownSeverity
    critical_evidence: tuple[str, ...]
    history_refs: tuple[str, ...]


@dataclass(frozen=True)
class RetrievedClause:
    """Ranked clause with deterministic lexical score (REQ-FUN-005)."""

    clause: PolicyClause
    lexical_score: float


@dataclass(frozen=True)
class RetrievalResult:
    """Ordered unique clauses plus release binding (REQ-FUN-005, REQ-INV-001)."""

    attempt: AttemptIdentity
    snapshot_id: str
    snapshot_revision: int
    binding: TrustAnchor
    corpus_digest: str
    clauses: tuple[RetrievedClause, ...]


@dataclass(frozen=True)
class Citation:
    """Validated citation resolved against pinned clauses (REQ-FUN-005, REQ-SEC-001)."""

    corpus_id: str
    corpus_revision: int
    clause_id: str
    clause_revision: int
    clause_digest: str


@dataclass(frozen=True)
class FullCitationParts:
    """Parsed full-form citation fields before provenance checks (REQ-FUN-005, REQ-SEC-001)."""

    corpus_id: str
    corpus_revision: int
    snapshot_id: str
    snapshot_revision: int
    clause_id: str
    clause_revision: int
    clause_digest: str


def encode_citation(
    clause: PolicyClause | Citation,
    snapshot_id: str,
    snapshot_revision: int,
    corpus_id: str,
    corpus_revision: int,
) -> str:
    """Canonicalize a validated citation with exactly one digest prefix (REQ-FUN-005)."""
    return (
        f"{corpus_id}@{corpus_revision}:{snapshot_id}@{snapshot_revision}:"
        f"{clause.clause_id}@{clause.clause_revision}#{clause.clause_digest}"
    )


def parse_full_citation(raw: str) -> FullCitationParts | None:
    """Parse a strict full-form citation without inferring missing prefixes (REQ-SEC-001)."""
    match = _FULL_CITATION_RE.fullmatch(raw)
    if match is None:
        return None
    try:
        corpus_revision = int(match.group("corpus_revision"))
        snapshot_revision = int(match.group("snapshot_revision"))
        clause_revision = int(match.group("clause_revision"))
    except ValueError:
        return None
    return FullCitationParts(
        corpus_id=match.group("corpus_id"),
        corpus_revision=corpus_revision,
        snapshot_id=match.group("snapshot_id"),
        snapshot_revision=snapshot_revision,
        clause_id=match.group("clause_id"),
        clause_revision=clause_revision,
        clause_digest=match.group("clause_digest"),
    )


def parse_short_citation(raw: str) -> tuple[str, int] | None:
    """Parse a short clause-only citation resolved from trusted context (REQ-FUN-005)."""
    match = _SHORT_CITATION_RE.fullmatch(raw)
    if match is None:
        return None
    try:
        revision = int(match.group("clause_revision"))
    except ValueError:
        return None
    return match.group("clause_id"), revision


@dataclass(frozen=True)
class AdvisoryResult:
    """Internal advisory DTO; adapter projects nine fields to S1 (REQ-FUN-002, ADR-001)."""

    attempt: AttemptIdentity
    verdict: Verdict
    severity: AdvisorySeverity
    rationale: str
    citations: tuple[Citation, ...]
    usage: Usage
    known_severity: KnownSeverity

    def to_s1_payload(self) -> Mapping[str, object]:
        """Return only the nine S1-compatible advisory fields (REQ-FUN-002, REQ-INV-001)."""
        return {
            "role": self.attempt.role,
            "verdict": self.verdict,
            "severity": self.severity,
            "rationale": self.rationale,
            "citations": tuple(
                encode_citation(
                    item,
                    self.attempt.snapshot_id,
                    self.attempt.snapshot_revision,
                    item.corpus_id,
                    item.corpus_revision,
                )
                for item in self.citations
            ),
            "prompt_version": self.attempt.prompt_version,
            "model_id": self.attempt.model_id,
            "model_version": self.attempt.model_version,
            "usage": {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
                "usage_unknown": self.usage.usage_unknown,
            },
        }


@dataclass(frozen=True)
class AnalysisFailure:
    """Typed failure with S3 evidence and S1-compatible code/detail projection (REQ-INV-002)."""

    code: FailureCode
    detail: str
    attempt: AttemptIdentity
    usage: Usage
    known_severity: KnownSeverity

    def to_s1_payload(self) -> Mapping[str, object]:
        """Return only S1 failure code and detail (REQ-INV-002, REQ-INV-001)."""
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class ModelWireResponse:
    """Strict model JSON allowlist; no identity or authority fields (REQ-SEC-001, ADR-001)."""

    verdict: Verdict
    severity: AdvisorySeverity
    rationale: str
    citations: tuple[str, ...]


@dataclass(frozen=True)
class ProviderRequest:
    """Bounded provider invocation request without a stale remaining budget (REQ-COS-001)."""

    attempt: AttemptIdentity
    serialized_context: str
    max_output_tokens: int


@dataclass(frozen=True)
class ProviderResponse:
    """Adapter-enriched response with transport attempt identity (REQ-SEC-001, ADR-001)."""

    attempt: AttemptIdentity
    raw_json: str
    usage: Usage


@dataclass(frozen=True)
class ContextSection:
    """One delimited context layer with token count (ADR-001, REQ-SEC-001)."""

    kind: ContextSectionKind
    text: str
    token_count: int
    clause_id: str | None
    essential: bool = False


@dataclass(frozen=True)
class ContextPackage:
    """Recounted context with preserved evidence, history and revision (REQ-INV-003, ADR-001)."""

    attempt: AttemptIdentity
    known_severity: KnownSeverity
    sections: tuple[ContextSection, ...]
    total_input_tokens: int
    capsule_version: str
    clause_ids: tuple[str, ...]
    preserved_critical_evidence: tuple[str, ...]
    preserved_history_refs: tuple[str, ...]
    case_revision: int
    submitted_text: str = ""
    retained_clauses: tuple[PolicyClause, ...] = ()


@dataclass(frozen=True)
class TrustedCapsule:
    """Versioned safety/schema/citation capsule; behavior-affecting (REQ-INV-005, ADR-001)."""

    version: str
    identity_schema: tuple[str, ...]
    safety_rules: tuple[str, ...]
    citation_rules: tuple[str, ...]


@dataclass(frozen=True)
class ContextConfig:
    """Provisional offline ADR context settings, not release SLO values (ADR-001, REQ-COS-001)."""

    envelope_tokens: int
    input_cap_tokens: int
    compaction_trigger_tokens: int
    safety_schema_tokens: int
    output_tokens: int
    reserve_tokens: int
    policy_tokens: int
    content_history_tokens: int
    state_tokens: int
    delimiter_tokens: int
    max_complete_clauses: int
    per_call_cap_ms: int
    provider_context_limit_tokens: int


@dataclass(frozen=True)
class AnalysisHandoff:
    """Immutable handoff with no disposition, hold or audit id (REQ-INV-001..004)."""

    outcome: AdvisoryResult | AnalysisFailure
    severity_known: KnownSeverity
    severity_advisory: AdvisorySeverity | None
    attempt: AttemptIdentity
    preserved_critical_evidence: tuple[str, ...]
    final_disposition: None
    audit_id: None
    hold_committed: None
