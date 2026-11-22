"""Immutable API and persistence DTOs (ADR-001; REQ-FUN-001/003/004)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, field_validator

ProcessingStatus = Literal["committed", "pending_unconfirmed", "failed", "conflict"]


@dataclass(frozen=True)
class RequestContext:
    """Server-authenticated identity; never populated from request JSON (REQ-SEC-003)."""

    actor_id: str
    actor_type: Literal["submitter", "moderator"]
    scopes: frozenset[str]


@dataclass(frozen=True)
class ProcessingResult:
    """Result returned by the API's policy-coordination port (REQ-FUN-001)."""

    status: ProcessingStatus
    case_id: str | None
    case_revision: int | None
    decision_id: str | None
    audit_id: str | None
    outcome: str | None
    message: str


class ProcessingUnavailable(RuntimeError):
    """Typed transient processing failure that leaves durable intake pending."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class CaseView:
    """Authorized case lookup projection with immutable policy attribution."""

    case_id: str
    owner_id: str
    revision: int
    status: str
    content_hash: str
    policy_snapshot_id: str
    policy_snapshot_digest: str
    audit_id: str | None
    content_text: str | None = None


@dataclass(frozen=True)
class AuditView:
    """Authorized immutable decision-evidence projection (REQ-INV-004)."""

    audit_id: str
    decision_id: str
    case_id: str
    case_revision: int
    owner_id: str
    outcome: str
    policy_reason_id: str
    policy_snapshot_id: str
    policy_snapshot_digest: str


@dataclass(frozen=True)
class QueueView:
    """Read-only human-review queue projection (REQ-FUN-003)."""

    case_id: str
    case_revision: int
    outcome: str
    reason_id: str
    severity: str
    enqueued_at: str


class SubmissionRequest(BaseModel):
    """Strict text-only submission body (REQ-SEC-002)."""

    model_config = ConfigDict(extra="forbid", strict=True)
    text: StrictStr

    @field_validator("text")
    @classmethod
    def nonempty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class ReviewRequestBody(BaseModel):
    """Strict client review evidence; identity is deliberately absent (REQ-SEC-003)."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: StrictInt
    requested_outcome: Literal["approve", "reject"]
    rationale: StrictStr

    @field_validator("expected_revision")
    @classmethod
    def positive_revision(cls, value: int) -> int:
        if value < 1:
            raise ValueError("expected_revision must be positive")
        return value

    @field_validator("rationale")
    @classmethod
    def nonempty_rationale(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("rationale must not be blank")
        return value


__all__ = [
    "AuditView",
    "CaseView",
    "ProcessingResult",
    "ProcessingUnavailable",
    "QueueView",
    "RequestContext",
    "ReviewRequestBody",
    "SubmissionRequest",
]
