"""Read-only injected ports for ADR-001, REQ-FUN-002/005 and REQ-INV-001/002."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Protocol

from .contracts import (
    AnalysisFailure,
    PolicyClause,
    PolicySnapshot,
    ProviderRequest,
    ProviderResponse,
    RetrievalQuery,
    RetrievedClause,
    TrustAnchor,
)
from .errors import DomainValidationError


class SnapshotSourcePort(Protocol):
    """Read-only corpus loader (REQ-FUN-005, REQ-INV-002)."""

    def load(self, snapshot_id: str, revision: int) -> PolicySnapshot | DomainValidationError:
        ...


class TrustRegistryPort(Protocol):
    """Read-only synthetic trusted release registry (REQ-FUN-005, REQ-SEC-001)."""

    def lookup(self, corpus_id: str, corpus_revision: int) -> TrustAnchor | DomainValidationError:
        ...


class RetrieverPort(Protocol):
    """Pure local lexical retriever with no IO (REQ-FUN-005, REQ-INV-001)."""

    def retrieve(
        self, query: RetrievalQuery, clauses: tuple[PolicyClause, ...]
    ) -> tuple[RetrievedClause, ...] | AnalysisFailure:
        ...


class TokenizerPort(Protocol):
    """Pure deterministic token counter (REQ-COS-001, ADR-001)."""

    def count_tokens(self, text: str) -> int:
        ...


class ClockPort(Protocol):
    """Read-only monotonic clock; no mutation (REQ-COS-001, ADR-001)."""

    def monotonic_ms(self) -> int:
        ...


class ProviderPort(Protocol):
    """Nonblocking advisory invocation port with no tools or cancel method (REQ-SEC-001)."""

    def invoke(self, request: ProviderRequest) -> Awaitable[ProviderResponse | AnalysisFailure]:
        ...
