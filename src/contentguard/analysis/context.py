"""Context assembly and compaction (ADR-001, REQ-COS-001, REQ-INV-001/003).

Every public function cites its governing requirements.
"""

from __future__ import annotations

from .contracts import (
    AnalysisFailure,
    AttemptIdentity,
    ContextConfig,
    ContextPackage,
    ContextSection,
    KnownSeverity,
    PolicyClause,
    PolicySnapshot,
    RetrievedClause,
    TrustedCapsule,
    Usage,
)
from .ports import TokenizerPort

_DELIMITER = "\n---\n"
_CAPSULE_KINDS = frozenset({"identity_schema", "safety_capsule", "citation_rules"})


def _config_valid(config: ContextConfig) -> bool:
    """Validate the complete reserve/output/provider envelope (REQ-COS-001)."""
    return (
        config.envelope_tokens > 0
        and config.provider_context_limit_tokens >= config.envelope_tokens
        and config.input_cap_tokens > 0
        and config.output_tokens > 0
        and config.reserve_tokens > 0
        and config.input_cap_tokens + config.output_tokens + config.reserve_tokens <= config.envelope_tokens
        and config.compaction_trigger_tokens > 0
        and config.compaction_trigger_tokens <= config.input_cap_tokens
        and config.max_complete_clauses > 0
        and config.safety_schema_tokens > 0
        and config.policy_tokens > 0
        and config.content_history_tokens > 0
        and config.state_tokens > 0
        and config.delimiter_tokens > 0
        and config.per_call_cap_ms > 0
    )


def _config_failure(attempt: AttemptIdentity, known_severity: KnownSeverity) -> AnalysisFailure:
    """Return a typed envelope configuration failure (REQ-COS-001, REQ-INV-002)."""
    return AnalysisFailure(
        "context_overflow", "invalid context envelope configuration", attempt, Usage(0, 0, True), known_severity
    )


def _capsule_sections(capsule: TrustedCapsule) -> tuple[ContextSection, ...]:
    """Render trusted identity, safety and citation rules (REQ-INV-005, ADR-001)."""
    return (
        ContextSection(
            "identity_schema",
            "IDENTITY_SCHEMA\n" + "\n".join(capsule.identity_schema),
            0,
            None,
            True,
        ),
        ContextSection(
            "safety_capsule",
            f"SAFETY_CAPSULE {capsule.version}\n" + "\n".join(capsule.safety_rules),
            0,
            None,
            True,
        ),
        ContextSection(
            "citation_rules",
            "CITATION_RULES\n" + "\n".join(capsule.citation_rules),
            0,
            None,
            True,
        ),
    )


def _clause_section(item: RetrievedClause, snapshot: PolicySnapshot) -> ContextSection:
    """Render one complete clause with pinned provenance metadata (REQ-FUN-005, REQ-INV-001)."""
    clause = item.clause
    text = "\n".join(
        (
            "POLICY_CLAUSE",
            f"clause: {clause.clause_id}@{clause.clause_revision}",
            f"corpus: {snapshot.corpus_id}@{snapshot.revision}",
            f"snapshot: {snapshot.snapshot_id}@{snapshot.revision}",
            f"source_ref: {clause.source_ref}",
            f"digest: {clause.clause_digest}",
            "text:",
            clause.text,
            "END_POLICY_CLAUSE",
        )
    )
    return ContextSection("policy_clause", text, 0, clause.clause_id)


def _serialize(sections: tuple[ContextSection, ...]) -> str:
    """Serialize delimited context sections with explicit boundaries (ADR-001, REQ-SEC-001)."""
    return _DELIMITER.join(section.text for section in sections)


def _rebuild(
    package: ContextPackage,
    sections: tuple[ContextSection, ...] | list[ContextSection],
    tokenizer: TokenizerPort,
    retained_clauses: tuple[PolicyClause, ...] | None = None,
    capsule_version: str | None = None,
) -> ContextPackage:
    """Recount each section and the entire serialized request (REQ-COS-001)."""
    recounted = tuple(
        ContextSection(
            section.kind,
            section.text,
            tokenizer.count_tokens(section.text),
            section.clause_id,
            section.essential,
        )
        for section in sections
    )
    serialized = _serialize(recounted)
    return ContextPackage(
        attempt=package.attempt,
        known_severity=package.known_severity,
        sections=recounted,
        total_input_tokens=tokenizer.count_tokens(serialized),
        capsule_version=package.capsule_version if capsule_version is None else capsule_version,
        clause_ids=tuple(section.clause_id for section in recounted if section.clause_id is not None),
        preserved_critical_evidence=package.preserved_critical_evidence,
        preserved_history_refs=package.preserved_history_refs,
        case_revision=package.case_revision,
        submitted_text=package.submitted_text,
        retained_clauses=package.retained_clauses if retained_clauses is None else retained_clauses,
    )


def _cap_failure(attempt: AttemptIdentity, known_severity: KnownSeverity) -> AnalysisFailure:
    """Return a typed hard-cap failure after compaction (REQ-COS-001, REQ-INV-001)."""
    return AnalysisFailure(
        "context_overflow", "context budget exceeded", attempt, Usage(0, 0, True), known_severity
    )


def assemble_context(
    attempt: AttemptIdentity,
    known_severity: KnownSeverity,
    snapshot: PolicySnapshot,
    clauses: tuple[RetrievedClause, ...],
    capsule: TrustedCapsule,
    config: ContextConfig,
    tokenizer: TokenizerPort,
    submitted_text: str = "",
    critical_evidence: tuple[str, ...] = (),
    history_refs: tuple[str, ...] = (),
) -> ContextPackage | AnalysisFailure:
    """Assemble prioritized context without truncating pinned content (ADR-001, REQ-INV-001)."""
    if not _config_valid(config):
        return _config_failure(attempt, known_severity)
    sections: list[ContextSection] = list(_capsule_sections(capsule))
    sections.append(
        ContextSection(
            "submitted_content",
            f"UNTRUSTED_SUBMITTED_CONTENT_BEGIN\n{submitted_text}\nUNTRUSTED_SUBMITTED_CONTENT_END",
            0,
            None,
            True,
        )
    )
    included = clauses[: config.max_complete_clauses]
    sections.extend(_clause_section(item, snapshot) for item in included)
    sections.append(
        ContextSection(
            "critical_evidence",
            "CRITICAL_EVIDENCE\n" + "\n".join(critical_evidence),
            0,
            None,
            True,
        )
    )
    sections.append(
        ContextSection(
            "content_history",
            "CONTENT_HISTORY\n" + "\n".join(history_refs),
            0,
            None,
        )
    )
    sections.append(
        ContextSection(
            "resumable_state",
            f"STATE known={known_severity} case_revision={attempt.case_revision}",
            0,
            None,
            True,
        )
    )
    sections.append(ContextSection("delimiter", "END_CONTEXT", 0, None, True))
    package = ContextPackage(
        attempt=attempt,
        known_severity=known_severity,
        sections=(),
        total_input_tokens=0,
        capsule_version=capsule.version,
        clause_ids=(),
        preserved_critical_evidence=critical_evidence,
        preserved_history_refs=history_refs,
        case_revision=attempt.case_revision,
        submitted_text=submitted_text,
        retained_clauses=tuple(item.clause for item in included),
    )
    return _rebuild(package, tuple(sections), tokenizer)


def compact_context(
    package: ContextPackage,
    config: ContextConfig,
    tokenizer: TokenizerPort,
    attempt: AttemptIdentity,
    known_severity: KnownSeverity,
) -> ContextPackage | AnalysisFailure:
    """Drop whole clauses then nonessential history, preserving one grounding clause (REQ-INV-003)."""
    if not _config_valid(config):
        return _config_failure(attempt, known_severity)
    if package.total_input_tokens <= config.compaction_trigger_tokens:
        return package
    sections = list(package.sections)
    retained = list(package.retained_clauses)
    limit = min(config.input_cap_tokens, config.provider_context_limit_tokens)
    compacted = _rebuild(package, tuple(sections), tokenizer, tuple(retained))
    while compacted.total_input_tokens > limit:
        clause_positions = [pos for pos, section in enumerate(sections) if section.kind == "policy_clause"]
        if len(clause_positions) > 1:
            position = clause_positions[-1]
            clause_id = sections[position].clause_id
            sections.pop(position)
            for index in range(len(retained) - 1, -1, -1):
                if retained[index].clause_id == clause_id:
                    retained.pop(index)
                    break
            compacted = _rebuild(package, tuple(sections), tokenizer, tuple(retained))
            continue
        history_position = next(
            (
                pos
                for pos, section in enumerate(sections)
                if not section.essential and section.kind != "policy_clause"
            ),
            None,
        )
        if history_position is None:
            return _cap_failure(attempt, known_severity)
        sections.pop(history_position)
        compacted = _rebuild(package, tuple(sections), tokenizer, tuple(retained))
    return compacted


def reinject_capsule(
    package: ContextPackage,
    capsule: TrustedCapsule,
    config: ContextConfig,
    tokenizer: TokenizerPort,
    attempt: AttemptIdentity,
    known_severity: KnownSeverity,
) -> ContextPackage | AnalysisFailure:
    """Replace forged capsule layers with trusted content after compaction (REQ-INV-005, REQ-SEC-001)."""
    if not _config_valid(config):
        return _config_failure(attempt, known_severity)
    sections = [section for section in package.sections if section.kind not in _CAPSULE_KINDS]
    sections[0:0] = list(_capsule_sections(capsule))
    rebuilt = _rebuild(package, tuple(sections), tokenizer, capsule_version=capsule.version)
    limit = min(config.input_cap_tokens, config.provider_context_limit_tokens)
    if rebuilt.total_input_tokens > limit:
        return _cap_failure(attempt, known_severity)
    return rebuilt


def serialize_context(package: ContextPackage) -> str:
    """Serialize the full delimited context for the provider request (ADR-001, REQ-COS-001)."""
    return _serialize(package.sections)
