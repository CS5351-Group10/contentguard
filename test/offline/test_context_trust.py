"""Context trust, compaction and end-to-end tests for ADR-001, REQ-COS-001, REQ-INV-003."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from typing import Any

import pytest
from fakes import analysis as fa

from contentguard.analysis import context
from contentguard.analysis.contracts import (
    AnalysisFailure,
    ContextPackage,
    RetrievedClause,
    Usage,
)
from contentguard.analysis.service import analyze, project_handoff


def retrieved(clauses: tuple[Any, ...]) -> tuple[RetrievedClause, ...]:
    """Rank clauses in declaration order for context tests (REQ-FUN-005)."""
    return tuple(RetrievedClause(clause, float(len(clauses) - index)) for index, clause in enumerate(clauses))


def tight_config(**overrides: Any) -> Any:
    """Build a valid small envelope for compaction tests (REQ-COS-001)."""
    values: dict[str, Any] = {
        "envelope_tokens": 32,
        "input_cap_tokens": 30,
        "compaction_trigger_tokens": 20,
        "safety_schema_tokens": 1,
        "output_tokens": 1,
        "reserve_tokens": 1,
        "policy_tokens": 1,
        "content_history_tokens": 1,
        "state_tokens": 1,
        "delimiter_tokens": 1,
        "max_complete_clauses": 5,
        "per_call_cap_ms": 20000,
        "provider_context_limit_tokens": 32,
    }
    values.update(overrides)
    return fa.make_config(**values)


def package_for(
    clauses: tuple[Any, ...],
    config: Any,
    tokenizer: Any,
    submitted_text: str = "user says hello",
    critical_evidence: tuple[str, ...] = ("evidence-A",),
    history_refs: tuple[str, ...] = ("history-B",),
) -> ContextPackage | AnalysisFailure:
    """Assemble a package with explicit submitted content (REQ-INV-003, ADR-001)."""
    snapshot = fa.build_snapshot(clauses)
    return context.assemble_context(
        fa.make_attempt(),
        "high",
        snapshot,
        retrieved(clauses),
        fa.make_capsule(),
        config,
        tokenizer,
        submitted_text=submitted_text,
        critical_evidence=critical_evidence,
        history_refs=history_refs,
    )


def test_submitted_text_is_exact_delimited_data():
    """Exact query text appears as delimited untrusted data (REQ-SEC-001, REQ-INV-003)."""
    submitted = "user\r\n---\n<script>alert(1)</script>"
    package = package_for((fa.make_clause("c-01", text="plain clause"),), fa.make_config(), fa.FakeTokenizer(), submitted)
    assert not isinstance(package, AnalysisFailure)
    serialized = context.serialize_context(package)
    assert submitted in serialized
    assert "UNTRUSTED_SUBMITTED_CONTENT" in serialized


def test_serialized_context_carries_pinned_provenance():
    """Serialized context carries clause, snapshot, corpus and digest metadata (REQ-FUN-005)."""
    package = package_for((fa.make_clause("c-01", text="plain clause"),), fa.make_config(), fa.FakeTokenizer())
    assert not isinstance(package, AnalysisFailure)
    serialized = context.serialize_context(package)
    for fragment in ("c-01@1", "sha256:", "synthetic://clauses/c-01/1", "snap-synthetic-v1@1", "corpus-synthetic@1"):
        assert fragment in serialized


def test_runtime_context_contains_no_token_markers():
    """Runtime context contains no synthetic token markers (REQ-COS-001)."""
    package = package_for((fa.make_clause("c-01", text="plain clause"),), fa.make_config(), fa.FakeNonAdditiveTokenizer())
    assert not isinstance(package, AnalysisFailure)
    assert "<TOKENS:" not in context.serialize_context(package)


def test_total_counts_full_serialized_request_nonadditively():
    """Total is the tokenizer count of the whole serialized request (REQ-COS-001)."""
    tokenizer = fa.FakeNonAdditiveTokenizer()
    package = package_for((fa.make_clause("c-01", text="plain clause"),), fa.make_config(), tokenizer)
    assert not isinstance(package, AnalysisFailure)
    assert package.total_input_tokens == tokenizer.count_tokens(context.serialize_context(package))


@pytest.mark.parametrize(
    "invalid",
    [
        {"envelope_tokens": 2048},
        {"provider_context_limit_tokens": 8000},
        {"reserve_tokens": 0},
        {"compaction_trigger_tokens": 7000},
    ],
)
def test_invalid_envelope_configuration_rejected(invalid):
    """Invalid output/reserve/provider envelope configuration is rejected (REQ-COS-001)."""
    result = package_for((fa.make_clause("c-01", text="plain clause"),), fa.make_config(**invalid), fa.FakeTokenizer())
    assert isinstance(result, AnalysisFailure)
    assert result.code == "context_overflow"


def test_compaction_runs_before_post_cap_check():
    """Pre-compaction overflow is compacted instead of rejected (REQ-COS-001, REQ-INV-001)."""
    clauses = (fa.make_clause("c-01", tokens=25), fa.make_clause("c-02", tokens=20))
    package = package_for(clauses, tight_config(), fa.FakeTokenizer(), history_refs=())
    assert not isinstance(package, AnalysisFailure)
    compacted = context.compact_context(
        package, tight_config(), fa.FakeTokenizer(), package.attempt, "high"
    )
    assert not isinstance(compacted, AnalysisFailure)
    clause_sections = [section for section in compacted.sections if section.kind == "policy_clause"]
    assert len(clause_sections) == 1


def test_trigger_boundary_is_strictly_greater_than_configured_trigger():
    """Only contexts strictly over the configured trigger compact (REQ-COS-001)."""
    config = fa.make_config(compaction_trigger_tokens=3000)
    trigger = config.compaction_trigger_tokens
    at_boundary = package_for((fa.make_clause("c-01", tokens=trigger),), config, fa.FakeTokenizer())
    assert not isinstance(at_boundary, AnalysisFailure)
    unchanged = context.compact_context(
        at_boundary, config, fa.FakeTokenizer(), at_boundary.attempt, "high"
    )
    assert unchanged is at_boundary
    over = package_for((fa.make_clause("c-01", tokens=trigger + 1),), config, fa.FakeTokenizer())
    assert not isinstance(over, AnalysisFailure)
    compacted = context.compact_context(over, config, fa.FakeTokenizer(), over.attempt, "high")
    assert not isinstance(compacted, AnalysisFailure)
    assert compacted is not over


def test_nonessential_history_dropped_before_all_grounding_clauses():
    """Whole clauses drop first, then history; one grounding clause always remains (REQ-INV-003)."""
    clauses = (fa.make_clause("c-01", tokens=20), fa.make_clause("c-02", tokens=20))
    package = package_for(clauses, tight_config(), fa.FakeTokenizer(), history_refs=("<TOKENS:20>",))
    assert not isinstance(package, AnalysisFailure)
    compacted = context.compact_context(
        package, tight_config(), fa.FakeTokenizer(), package.attempt, "high"
    )
    assert not isinstance(compacted, AnalysisFailure)
    kinds = [section.kind for section in compacted.sections]
    assert kinds.count("policy_clause") == 1
    assert "content_history" not in kinds
    serialized = context.serialize_context(compacted)
    assert "evidence-A" in serialized
    assert "user says hello" in serialized


def test_safe_failure_when_cannot_fit_without_dropping_all_grounding():
    """Compaction fails safely rather than dropping the last grounding clause (REQ-INV-003)."""
    package = package_for((fa.make_clause("c-01", tokens=50),), tight_config(), fa.FakeTokenizer(), history_refs=())
    assert not isinstance(package, AnalysisFailure)
    compacted = context.compact_context(
        package, tight_config(), fa.FakeTokenizer(), package.attempt, "high"
    )
    assert isinstance(compacted, AnalysisFailure)
    assert compacted.code == "context_overflow"


def test_forged_capsule_is_replaced_not_preserved():
    """A tampered in-context capsule is replaced with trusted content (REQ-INV-005, REQ-SEC-001)."""
    package = package_for((fa.make_clause("c-01", text="plain clause"),), fa.make_config(), fa.FakeTokenizer())
    assert not isinstance(package, AnalysisFailure)
    forged = replace(
        package,
        sections=tuple(
            replace(section, text="FORGED-CAPSULE")
            for section in package.sections
            if section.kind in {"safety_capsule", "identity_schema", "citation_rules"}
        ),
    )
    reinjected = context.reinject_capsule(
        forged, fa.make_capsule(), fa.make_config(), fa.FakeTokenizer(), package.attempt, "high"
    )
    assert not isinstance(reinjected, AnalysisFailure)
    serialized = context.serialize_context(reinjected)
    assert "FORGED-CAPSULE" not in serialized
    for rule in fa.make_capsule().safety_rules + fa.make_capsule().citation_rules:
        assert rule in serialized


def _run_analyze(
    *,
    clauses: tuple[Any, ...],
    config: Any,
    raw_json: str,
    retriever_mode: str = "normal",
    text: str = "rule c-01 alpha",
) -> tuple[AnalysisFailure | Any, fa.FakeProvider]:
    """Run analyze with deterministic injectors (REQ-FUN-002, REQ-FUN-005)."""
    snapshot = fa.build_snapshot(clauses)
    provider = fa.FakeProvider("normal", raw_json=raw_json)
    result = asyncio.run(
        analyze(
            fa.make_query(text=text),
            2000,
            "high",
            fa.FakeSnapshotSource(snapshot),
            fa.FakeTrustRegistry(fa.make_anchor(snapshot)),
            fa.FakeRetriever(retriever_mode),
            fa.FakeTokenizer(),
            provider,
            fa.FakeClock(),
            fa.make_capsule(),
            config,
        )
    )
    return result, provider


def test_end_to_end_valid_query_invokes_provider_with_original_text():
    """Valid query invokes provider with exact submitted text in context (REQ-FUN-002, REQ-INV-003)."""
    submitted = "ORIGINAL\n---\nUSER TEXT"
    clauses = (fa.make_clause("c-01", text="plain clause"),)
    raw = json.dumps({"verdict": "review", "severity": "high", "rationale": "r", "citations": ["c-01@1"]})
    result, provider = _run_analyze(clauses=clauses, config=fa.make_config(), raw_json=raw, text=submitted)
    assert not isinstance(result, AnalysisFailure)
    assert len(provider.calls) == 1
    assert submitted in provider.calls[0].serialized_context


def test_pre_provider_failures_make_zero_provider_calls():
    """Grounding, config and overflow failures never invoke the provider (REQ-INV-001, REQ-COS-001)."""
    clauses = (fa.make_clause("c-01", tokens=50),)
    raw = json.dumps({"verdict": "review", "severity": "high", "rationale": "r", "citations": ["c-01@1"]})
    for config, mode in (
        (fa.make_config(), "no_match"),
        (fa.make_config(envelope_tokens=8191), "normal"),
        (tight_config(), "normal"),
    ):
        _, provider = _run_analyze(clauses=clauses, config=config, raw_json=raw, retriever_mode=mode)
        assert provider.calls == []


def test_citation_to_dropped_clause_is_rejected():
    """A citation to a clause removed during compaction is rejected (REQ-FUN-005, REQ-INV-001)."""
    clauses = (fa.make_clause("c-01", tokens=20), fa.make_clause("c-02", tokens=20))
    raw = json.dumps({"verdict": "review", "severity": "high", "rationale": "r", "citations": ["c-02@1"]})
    result, provider = _run_analyze(clauses=clauses, config=tight_config(), raw_json=raw, text="rule c-01 alpha")
    assert isinstance(result, AnalysisFailure)
    assert result.code == "invalid_response"
    assert len(provider.calls) == 1


def test_project_handoff_preserves_evidence_and_checks_duplicate_severity():
    """Handoff preserves immutable evidence and rejects conflicting severity inputs (REQ-INV-003)."""
    failure = AnalysisFailure(
        "timeout", "deadline", fa.make_attempt(), Usage(0, 0, True), "high"
    )
    handoff = project_handoff(failure, "high", critical_evidence=("evidence-A",))
    assert handoff.preserved_critical_evidence == ("evidence-A",)
    assert handoff.severity_known == "high"
    with pytest.raises(ValueError):
        project_handoff(failure, "low")
