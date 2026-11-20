"""Deterministic offline fakes for ADR-001, REQ-FUN-002/005 and REQ-COS-001."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, cast

from contentguard.analysis import contracts as c
from contentguard.analysis.errors import DomainValidationError
from contentguard.analysis.snapshot import canonical_clause_digest

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "analysis"
_TOKEN_RE = re.compile(r"<TOKENS:(\d+)>")


def load_fixture(name: str) -> Any:
    """Load a pinned offline fixture document (REQ-FUN-005, ADR-001)."""
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def canonical_digest(text: str) -> str:
    """Compute a stable canonical clause digest proposal (REQ-FUN-005, ADR-001)."""
    return canonical_clause_digest(text)


def corpus_digest(clauses: tuple[c.PolicyClause, ...]) -> str:
    """Compute the canonical corpus digest proposal (REQ-FUN-005, ADR-001)."""
    payload = "\n".join(
        f"{clause.clause_id}@{clause.clause_revision}:{clause.clause_digest}"
        for clause in sorted(clauses, key=lambda item: (item.clause_id, item.clause_revision))
    )
    return canonical_digest(payload)


def make_clause(clause_id: str, tokens: int = 8, text: str | None = None) -> c.PolicyClause:
    """Create a pinned clause with deterministic digest (REQ-FUN-005, ADR-001)."""
    body = text or f"rule {clause_id} <TOKENS:{tokens}>"
    return c.PolicyClause(
        clause_id=clause_id,
        clause_revision=1,
        text=body,
        category="safety",
        severity_hint="medium",
        source_ref=f"synthetic://clauses/{clause_id}/1",
        clause_digest=canonical_digest(body),
    )


def build_snapshot(clauses: tuple[c.PolicyClause, ...], status: c.ApprovalStatus = "approved") -> c.PolicySnapshot:
    """Build a synthetic snapshot with explicit approval status (REQ-FUN-005, REQ-SEC-001)."""
    return c.PolicySnapshot(
        snapshot_id="snap-synthetic-v1",
        revision=1,
        corpus_id="corpus-synthetic",
        approval=c.ApprovalRecord(
            status=status,
            approver_ref="synthetic-approver",
            approval_revision="ar-1",
            evidence_ref="approval://synthetic/1",
            approved_at="2026-01-01T00:00:00Z",
        ),
        corpus_digest=corpus_digest(clauses),
        clauses=clauses,
    )


def make_anchor(snapshot: c.PolicySnapshot, status: c.ApprovalStatus = "approved") -> c.TrustAnchor:
    """Build a synthetic release binding for a snapshot (REQ-FUN-005, ADR-001)."""
    return c.TrustAnchor(
        corpus_id=snapshot.corpus_id,
        corpus_revision=snapshot.revision,
        approved_corpus_digest=snapshot.corpus_digest,
        approval_reference=snapshot.approval.approval_revision,
        status=status,
        policy_snapshot_id=snapshot.snapshot_id,
        policy_snapshot_digest=snapshot.corpus_digest,
        approved_by=snapshot.approval.approver_ref,
        approved_at=snapshot.approval.approved_at,
        registry_version="reg-v1",
    )


def make_attempt(**overrides: Any) -> c.AttemptIdentity:
    """Build adapter-owned attempt identity for offline tests (REQ-SEC-001, ADR-001)."""
    values: dict[str, Any] = {
        "attempt_id": "attempt-1",
        "case_id": "case-1",
        "case_revision": 7,
        "snapshot_id": "snap-synthetic-v1",
        "snapshot_revision": 1,
        "prompt_version": "pv-1",
        "model_id": "offline-model",
        "model_version": "1.0",
        "tokenizer_id": "fake-tokenizer-v1",
        "contract_version": "advisory-v1",
        "role": "initial_review",
    }
    values.update(overrides)
    return c.AttemptIdentity(**values)


def make_query(text: str = "benign text", **overrides: Any) -> c.RetrievalQuery:
    """Build a retrieval query with trusted severity and evidence (REQ-FUN-005, REQ-INV-003)."""
    values: dict[str, Any] = {
        "attempt": make_attempt(),
        "text": text,
        "snapshot_id": "snap-synthetic-v1",
        "snapshot_revision": 1,
        "corpus_id": "corpus-synthetic",
        "corpus_revision": 1,
        "known_severity": "high",
        "critical_evidence": ("evidence-A",),
        "history_refs": ("h-1",),
    }
    values.update(overrides)
    return c.RetrievalQuery(**values)


def make_config(**overrides: Any) -> c.ContextConfig:
    """Build provisional offline context settings (ADR-001, REQ-COS-001)."""
    values: dict[str, Any] = {
        "envelope_tokens": 8192,
        "input_cap_tokens": 6144,
        "compaction_trigger_tokens": 4608,
        "safety_schema_tokens": 1024,
        "output_tokens": 1024,
        "reserve_tokens": 1024,
        "policy_tokens": 2048,
        "content_history_tokens": 2048,
        "state_tokens": 512,
        "delimiter_tokens": 512,
        "max_complete_clauses": 5,
        "per_call_cap_ms": 20000,
        "provider_context_limit_tokens": 8192,
    }
    values.update(overrides)
    return c.ContextConfig(**values)


def make_capsule() -> c.TrustedCapsule:
    """Build the immutable behavior-affecting capsule (REQ-INV-005, ADR-001)."""
    return c.TrustedCapsule(
        version="capsule-v1",
        identity_schema=("role", "case_id", "case_revision", "snapshot_id"),
        safety_rules=("no-enforcement-fields", "no-tool-use", "no-audit-ids"),
        citation_rules=("known-clause-only", "pinned-revision-only", "digest-required"),
    )


class FakeSnapshotSource:
    """Read-only snapshot map with typed misses (REQ-FUN-005, REQ-INV-002)."""

    def __init__(self, snapshot: c.PolicySnapshot) -> None:
        self.snapshot = snapshot
        self.calls: list[tuple[str, int]] = []

    def load(self, snapshot_id: str, revision: int) -> c.PolicySnapshot | DomainValidationError:
        """Return the pinned snapshot or a domain error (REQ-FUN-005)."""
        self.calls.append((snapshot_id, revision))
        if snapshot_id != self.snapshot.snapshot_id or revision != self.snapshot.revision:
            return DomainValidationError("stale_snapshot", "snapshot mismatch", snapshot_id, revision)
        return self.snapshot


class SwappingSnapshotSource(FakeSnapshotSource):
    """Snapshot source that swaps the second load to model TOCTOU (REQ-SEC-001)."""

    def __init__(self, first: c.PolicySnapshot, second: c.PolicySnapshot) -> None:
        super().__init__(first)
        self.second = second

    def load(self, snapshot_id: str, revision: int) -> c.PolicySnapshot | DomainValidationError:
        """Return the first snapshot once, then the swapped artifact (REQ-FUN-005, REQ-SEC-001)."""
        if len(self.calls) == 1:
            self.calls.append((snapshot_id, revision))
            if snapshot_id != self.second.snapshot_id or revision != self.second.revision:
                return DomainValidationError("stale_snapshot", "snapshot mismatch", snapshot_id, revision)
            return self.second
        return super().load(snapshot_id, revision)


class FakeTrustRegistry:
    """Read-only synthetic registry with configurable failure modes (REQ-SEC-001)."""

    def __init__(self, anchor: c.TrustAnchor, mode: str = "approved") -> None:
        self.anchor = anchor
        self.mode = mode
        self.calls: list[tuple[str, int]] = []

    def lookup(self, corpus_id: str, corpus_revision: int) -> c.TrustAnchor | DomainValidationError:
        """Return the trusted release binding or a domain error (REQ-FUN-005)."""
        self.calls.append((corpus_id, corpus_revision))
        if self.mode == "missing":
            return DomainValidationError("missing_approval", "no binding", corpus_id, corpus_revision)
        if corpus_id != self.anchor.corpus_id or corpus_revision != self.anchor.corpus_revision:
            return DomainValidationError("stale_snapshot", "binding mismatch", corpus_id, corpus_revision)
        if self.mode == "unapproved":
            return c.TrustAnchor(**{**self.anchor.__dict__, "status": "unapproved"})
        if self.mode == "conflicting":
            return c.TrustAnchor(
                **{**self.anchor.__dict__, "approved_corpus_digest": "sha256:conflict"}
            )
        return self.anchor


class FakeTokenizer:
    """Marker-aware token counter; markers are not accuracy evidence (REQ-COS-001, ADR-001)."""

    def count_tokens(self, text: str) -> int:
        """Count marker tokens when present, otherwise whitespace tokens (REQ-COS-001)."""
        matches = _TOKEN_RE.findall(text)
        if matches:
            return sum(int(value) for value in matches)
        return len(text.split())


class FakeNonAdditiveTokenizer(FakeTokenizer):
    """Nonadditive counter proving the runtime counts serialized delimiters (REQ-COS-001)."""

    def count_tokens(self, text: str) -> int:
        """Add framing overhead so summed section counts cannot pass (REQ-COS-001)."""
        return super().count_tokens(text) + text.count("\n---\n") * 7 + text.count("<CONTEXT>") * 3


class FakeClock:
    """Manual monotonic clock for deterministic absolute deadlines (REQ-COS-001)."""

    def __init__(self, start_ms: int = 1000) -> None:
        self.now = start_ms

    def monotonic_ms(self) -> int:
        """Return current monotonic time without mutation (REQ-COS-001)."""
        return self.now

    def advance(self, delta_ms: int) -> None:
        """Advance the fake clock (REQ-COS-001)."""
        self.now += delta_ms


class FakeRetriever:
    """Pure retriever with deterministic lexical ranking and error modes (REQ-FUN-005)."""

    def __init__(self, mode: str = "normal") -> None:
        self.mode = mode
        self.calls = 0

    def retrieve(
        self, query: c.RetrievalQuery, clauses: tuple[c.PolicyClause, ...]
    ) -> tuple[c.RetrievedClause, ...] | c.AnalysisFailure:
        """Return ranked clauses or a typed grounding failure (REQ-FUN-005, REQ-INV-002)."""
        self.calls += 1
        if self.mode == "exception":
            raise RuntimeError("retriever exploded")
        if self.mode == "timeout":
            return c.AnalysisFailure(
                "timeout", "retriever timeout", query.attempt, c.Usage(0, 0, True), query.known_severity
            )
        if self.mode == "no_match":
            return ()
        if self.mode == "forged_failure":
            return c.AnalysisFailure(
                "grounding_unavailable", "forged failure", make_attempt(attempt_id="forged"), c.Usage(0, 0, True), "unknown"
            )
        ranked = []
        for clause in clauses:
            score = float(sum(1 for word in query.text.lower().split() if word in clause.text.lower()))
            ranked.append(c.RetrievedClause(clause=clause, lexical_score=score))
        ranked.sort(key=lambda item: (-item.lexical_score, item.clause.clause_id))
        return tuple(ranked)


class TamperingRetriever(FakeRetriever):
    """Retriever that mutates one returned clause while the snapshot stays pinned (REQ-SEC-001)."""

    def __init__(self, tamper: str) -> None:
        super().__init__("normal")
        self.tamper = tamper

    def retrieve(
        self, query: c.RetrievalQuery, clauses: tuple[c.PolicyClause, ...]
    ) -> tuple[c.RetrievedClause, ...] | c.AnalysisFailure:
        """Return one clause altered by the declared mutation (REQ-FUN-005, REQ-SEC-001)."""
        ranked = super().retrieve(query, clauses)
        if isinstance(ranked, c.AnalysisFailure) or not ranked:
            return ranked
        clause = ranked[0].clause
        if self.tamper == "digest":
            altered = c.PolicyClause(**{**clause.__dict__, "clause_digest": "sha256:bad"})
        elif self.tamper == "revision":
            altered = c.PolicyClause(**{**clause.__dict__, "clause_revision": 99})
        elif self.tamper == "text":
            altered = c.PolicyClause(**{**clause.__dict__, "text": "forged text", "clause_digest": clause.clause_digest})
        elif self.tamper == "source_ref":
            altered = c.PolicyClause(**{**clause.__dict__, "source_ref": "forged://source"})
        elif self.tamper == "category":
            altered = c.PolicyClause(**{**clause.__dict__, "category": "forged"})
        elif self.tamper == "severity_hint":
            altered = c.PolicyClause(**{**clause.__dict__, "severity_hint": "low"})
        else:
            raise AssertionError(f"unknown tamper mode: {self.tamper}")
        return (c.RetrievedClause(altered, ranked[0].lexical_score),)


class FakeProvider:
    """Async advisory provider with normal, unavailable and cancel-suppressing modes (REQ-SEC-001)."""

    def __init__(self, mode: str = "normal", raw_json: str | None = None) -> None:
        self.mode = mode
        self.raw_json = raw_json or json.dumps(
            {
                "verdict": "review",
                "severity": "high",
                "rationale": "grounded rationale",
                "citations": ["c-01@1"],
            }
        )
        self.calls: list[c.ProviderRequest] = []
        self.late_result_seen = False

    async def invoke(self, request: c.ProviderRequest) -> c.ProviderResponse | c.AnalysisFailure:
        """Return a response or typed failure without tools (REQ-FUN-002, REQ-INV-002)."""
        self.calls.append(request)
        if self.mode == "exception":
            raise RuntimeError("provider exploded")
        if self.mode == "wrong_type":
            return cast(c.ProviderResponse | c.AnalysisFailure, object())
        if self.mode == "wrong_identity":
            return c.ProviderResponse(
                attempt=make_attempt(attempt_id="other-attempt"),
                raw_json=self.raw_json,
                usage=c.Usage(1, 1, False),
            )
        if self.mode == "forged_failure":
            return c.AnalysisFailure(
                "provider_unavailable", "forged failure", make_attempt(attempt_id="other-attempt"), c.Usage(0, 0, True), "unknown"
            )
        if self.mode == "unavailable":
            return c.AnalysisFailure(
                "provider_unavailable", "offline provider down", request.attempt, c.Usage(0, 0, True), "unknown"
            )
        if self.mode == "invalid":
            return c.ProviderResponse(
                attempt=request.attempt, raw_json='{"unexpected": true}', usage=c.Usage(1, 1, False)
            )
        if self.mode == "cancel_suppressing":
            try:
                await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                await asyncio.sleep(0.005)
                self.late_result_seen = True
                return self._response(request)
        else:
            await asyncio.sleep(0)
        return self._response(request)

    def _response(self, request: c.ProviderRequest) -> c.ProviderResponse:
        """Build a valid suite-owned response (REQ-FUN-002, REQ-SEC-001)."""
        usage = c.Usage(0, 0, True) if self.mode == "unknown_usage" else c.Usage(3, 2, False)
        return c.ProviderResponse(attempt=request.attempt, raw_json=self.raw_json, usage=usage)
