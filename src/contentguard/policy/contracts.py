"""Policy data contracts — enums and frozen DTOs (REQ-INV-001/003/004, FUN-004, QUA-001).

Names and required fields follow ``docs/architecture/interface-contracts.md``
("Common data"). Every record here is an immutable ``@dataclass(frozen=True)``; inbound
records that accept client JSON do so only via an explicit ``from_payload`` that rejects
unknown and privileged keys. Actor identity always comes from a server-authenticated
:class:`RequestContext`, never from client-supplied fields.

CP1 defines the contracts only. The engine, snapshot and store arrive in later slices.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any


class Verdict(StrEnum):
    """Advisory verdict produced by the analysis component (advisory only)."""

    ALLOW = "allow"
    REVIEW = "review"
    VIOLATE = "violate"


class Severity(str, Enum):
    """Advisory / effective severity.

    Ordering uses :attr:`RANK`, never the string value: ``"low" > "high"`` and
    ``"medium" > "high"`` lexically, so a ``max()`` over the strings would silently
    invert REQ-INV-003. Use :func:`effective_severity` instead.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def RANK(self) -> int:
        """Numeric rank: low=1, medium=2, high=3."""
        return _SEVERITY_RANK[self]


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
}


def effective_severity(*severities: Severity | None) -> Severity | None:
    """Return the highest severity by explicit rank, ignoring ``None``.

    This is the single comparison point for severities (S1 plan §3.5 step 5). Returns
    ``None`` only when every input is ``None`` (e.g. AI severity unknown on a typed
    analysis failure with a non-high prefilter).
    """
    present = [s for s in severities if s is not None]
    if not present:
        return None
    return max(present, key=lambda s: s.RANK)


class Outcome(StrEnum):
    """Policy enforcement outcome (authoritative)."""

    APPROVE = "approve"
    HOLD = "hold"
    REJECT = "reject"
    ESCALATE = "escalate"


class CaseStatus(StrEnum):
    """Case lifecycle state (``docs/architecture/interface-contracts.md`` §State)."""

    ACCEPTED = "accepted"
    ANALYZING = "analyzing"
    HELD = "held"
    ESCALATED = "escalated"
    APPROVED = "approved"
    REJECTED = "rejected"


class FailureCode(StrEnum):
    """Typed analysis failure codes — no invented verdict accompanies a failure."""

    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"
    GROUNDING_UNAVAILABLE = "grounding_unavailable"
    CONTEXT_OVERFLOW = "context_overflow"


class CommitStatus(StrEnum):
    """Commit result status (``docs/architecture/interface-contracts.md`` "Commit result")."""

    COMMITTED = "committed"
    PENDING_UNCONFIRMED = "pending_unconfirmed"
    FAILED = "failed"
    CONFLICT = "conflict"


class _ContractError(ValueError):
    """Raised when a policy DTO is constructed from invalid data."""


ACTOR_ROLES: frozenset[str] = frozenset({"submitter", "moderator", "system", "policy"})
ADVISORY_ROLES: frozenset[str] = frozenset({"initial_review", "reconsideration"})
REVIEW_OUTCOMES: frozenset[Outcome] = frozenset({Outcome.APPROVE, Outcome.REJECT})
FINAL_STATUSES: frozenset[CaseStatus] = frozenset({CaseStatus.APPROVED, CaseStatus.REJECTED})
REVIEWABLE_STATUSES: frozenset[CaseStatus] = frozenset({CaseStatus.HELD, CaseStatus.ESCALATED})

_FORBIDDEN_ADVISORY_KEYS: frozenset[str] = frozenset(
    {"action", "outcome", "enforcement", "actor", "privileges", "tools"}
)
_FORBIDDEN_REVIEW_IDENTITY_KEYS: frozenset[str] = frozenset(
    {"reviewer", "actor", "actor_id", "role", "privileges", "admin"}
)


def _require_nonempty(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _ContractError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True)
class RequestContext:
    """Server-authenticated request context; the sole source of actor identity."""

    actor_id: str
    role: str
    idempotency_key: str

    def __post_init__(self) -> None:
        _require_nonempty(self.actor_id, "actor_id")
        _require_nonempty(self.idempotency_key, "idempotency_key")
        if self.role not in ACTOR_ROLES:
            raise _ContractError(f"role {self.role!r} not in {sorted(ACTOR_ROLES)}")


@dataclass(frozen=True)
class ActorRef:
    """A resolved actor reference (id + authorized role)."""

    actor_id: str
    role: str

    def __post_init__(self) -> None:
        _require_nonempty(self.actor_id, "actor_id")
        if self.role not in ACTOR_ROLES:
            raise _ContractError(f"role {self.role!r} not in {sorted(ACTOR_ROLES)}")


@dataclass(frozen=True)
class Usage:
    """Per-attempt provider usage; never coerced to zero when unknown."""

    input_tokens: int
    output_tokens: int
    usage_unknown: bool

    def __post_init__(self) -> None:
        if not isinstance(self.input_tokens, int) or self.input_tokens < 0:
            raise _ContractError("input_tokens must be a non-negative int")
        if not isinstance(self.output_tokens, int) or self.output_tokens < 0:
            raise _ContractError("output_tokens must be a non-negative int")
        if not isinstance(self.usage_unknown, bool):
            raise _ContractError("usage_unknown must be a bool")
        if self.usage_unknown and (self.input_tokens != 0 or self.output_tokens != 0):
            raise _ContractError("usage_unknown=True must not carry token counts")


@dataclass(frozen=True)
class AdvisoryResult:
    """Validated advisory output from the analysis component (never authoritative).

    ``role`` is the LLM role (``initial_review`` / ``reconsideration``), not an actor
    privilege. ``from_payload`` accepts exactly the documented key set and rejects any
    privileged/action key, so a model cannot smuggle enforcement authority.
    """

    role: str
    verdict: Verdict
    severity: Severity
    rationale: str
    citations: tuple[str, ...]
    prompt_version: str
    model_id: str
    model_version: str
    usage: Usage

    def __post_init__(self) -> None:
        if self.role not in ADVISORY_ROLES:
            raise _ContractError(f"role {self.role!r} not in {sorted(ADVISORY_ROLES)}")
        _require_nonempty(self.rationale, "rationale")
        _require_nonempty(self.prompt_version, "prompt_version")
        _require_nonempty(self.model_id, "model_id")
        _require_nonempty(self.model_version, "model_version")

    _PAYLOAD_KEYS: frozenset[str] = frozenset(
        {
            "role",
            "verdict",
            "severity",
            "rationale",
            "citations",
            "prompt_version",
            "model_id",
            "model_version",
            "usage",
        }
    )

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> AdvisoryResult:
        """Build an advisory result from exactly the documented key set.

        Rejects privileged/action keys (``action``/``outcome``/``enforcement``/``actor``/
        ``privileges``/``tools``) and any unknown key (REQ-INV-001).
        """
        unknown = set(payload) - cls._PAYLOAD_KEYS
        if unknown:
            raise _ContractError(f"advisory payload has unexpected keys: {sorted(unknown)}")
        missing = cls._PAYLOAD_KEYS - set(payload)
        if missing:
            raise _ContractError(f"advisory payload missing keys: {sorted(missing)}")

        usage_payload = payload["usage"]
        if not isinstance(usage_payload, Mapping):
            raise _ContractError("usage must be a mapping")
        usage = Usage(
            input_tokens=int(usage_payload["input_tokens"]),
            output_tokens=int(usage_payload["output_tokens"]),
            usage_unknown=bool(usage_payload["usage_unknown"]),
        )
        citations = payload["citations"]
        if not isinstance(citations, (list, tuple)):
            raise _ContractError("citations must be a list or tuple")
        return cls(
            role=str(payload["role"]),
            verdict=Verdict(payload["verdict"]),
            severity=Severity(payload["severity"]),
            rationale=str(payload["rationale"]),
            citations=tuple(str(c) for c in citations),
            prompt_version=str(payload["prompt_version"]),
            model_id=str(payload["model_id"]),
            model_version=str(payload["model_version"]),
            usage=usage,
        )


@dataclass(frozen=True)
class AnalysisFailure:
    """Typed analysis failure; carries no verdict (REQ-INV-002 boundary)."""

    code: FailureCode
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, FailureCode):
            raise _ContractError("code must be a FailureCode")
        _require_nonempty(self.detail, "detail")


@dataclass(frozen=True)
class CaseSnapshot:
    """Immutable case state pinned to a policy snapshot (interface-contracts "Case snapshot").

    Cross-field advisory rule (S1 plan §3.2): a verdict requires severity + model id +
    model version and forbids a failure code; a failure code forbids all advisory fields;
    both null is allowed only before analysis. This keeps ``Severity.RANK[None]``
    unreachable.
    """

    case_id: str
    revision: int
    status: CaseStatus
    content_hash: str
    policy_snapshot_id: str
    policy_snapshot_digest: str
    advisory_verdict: Verdict | None = None
    advisory_severity: Severity | None = None
    advisory_model_id: str | None = None
    advisory_model_version: str | None = None
    analysis_failure_code: FailureCode | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.case_id, "case_id")
        _require_nonempty(self.content_hash, "content_hash")
        _require_nonempty(self.policy_snapshot_id, "policy_snapshot_id")
        _require_nonempty(self.policy_snapshot_digest, "policy_snapshot_digest")
        if not isinstance(self.revision, int) or self.revision < 1:
            raise _ContractError("revision must be an int >= 1")
        if not isinstance(self.status, CaseStatus):
            raise _ContractError("status must be a CaseStatus")

        advisory_fields = (
            self.advisory_severity,
            self.advisory_model_id,
            self.advisory_model_version,
        )
        has_verdict = self.advisory_verdict is not None
        has_failure = self.analysis_failure_code is not None
        any_advisory = has_verdict or any(f is not None for f in advisory_fields)

        if has_failure:
            if self.analysis_failure_code is not None and not isinstance(
                self.analysis_failure_code, FailureCode
            ):
                raise _ContractError("analysis_failure_code must be a FailureCode")
            if any_advisory:
                raise _ContractError(
                    "a case with an analysis failure cannot also carry advisory fields"
                )
        elif has_verdict:
            if not isinstance(self.advisory_verdict, Verdict):
                raise _ContractError("advisory_verdict must be a Verdict")
            if self.advisory_severity is None:
                raise _ContractError("a verdict requires advisory_severity")
            if not isinstance(self.advisory_severity, Severity):
                raise _ContractError("advisory_severity must be a Severity")
            _require_nonempty(self.advisory_model_id, "advisory_model_id")
            _require_nonempty(self.advisory_model_version, "advisory_model_version")
        else:
            if any(f is not None for f in advisory_fields):
                raise _ContractError(
                    "advisory fields require an advisory_verdict"
                )


@dataclass(frozen=True)
class ReviewRequest:
    """An authorized human review of a held/escalated case (REQ-INV-003/004).

    Reviewer identity comes from the server-authenticated ``RequestContext`` via
    ``from_payload``; callers cannot self-assert a reviewer or privilege. The engine
    separately checks revision / snapshot / digest / content-hash currency and that the
    reviewer role is ``moderator``.
    """

    reviewer: ActorRef
    case_id: str
    expected_revision: int
    requested_outcome: Outcome
    rationale: str
    policy_snapshot_id: str
    policy_snapshot_digest: str
    content_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.reviewer, ActorRef):
            raise _ContractError("reviewer must be an ActorRef")
        _require_nonempty(self.case_id, "case_id")
        _require_nonempty(self.rationale, "rationale")
        _require_nonempty(self.policy_snapshot_id, "policy_snapshot_id")
        _require_nonempty(self.policy_snapshot_digest, "policy_snapshot_digest")
        _require_nonempty(self.content_hash, "content_hash")
        if not isinstance(self.expected_revision, int) or self.expected_revision < 1:
            raise _ContractError("expected_revision must be an int >= 1")
        if self.requested_outcome not in REVIEW_OUTCOMES:
            raise _ContractError(
                f"requested_outcome {self.requested_outcome!r} not in "
                f"{sorted(o.value for o in REVIEW_OUTCOMES)}"
            )

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
        context: RequestContext,
    ) -> ReviewRequest:
        """Build a review from client fields plus the authenticated context.

        ``payload`` must not carry reviewer/identity/privilege keys; those are taken only
        from ``context``. ``requested_outcome`` is limited to approve/reject.
        """
        forbidden = set(payload) & _FORBIDDEN_REVIEW_IDENTITY_KEYS
        if forbidden:
            raise _ContractError(
                f"review payload must not supply identity/privilege keys: {sorted(forbidden)}"
            )
        allowed = {
            "case_id",
            "expected_revision",
            "requested_outcome",
            "rationale",
            "policy_snapshot_id",
            "policy_snapshot_digest",
            "content_hash",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise _ContractError(f"review payload has unexpected keys: {sorted(unknown)}")
        missing = allowed - set(payload)
        if missing:
            raise _ContractError(f"review payload missing keys: {sorted(missing)}")

        return cls(
            reviewer=ActorRef(actor_id=context.actor_id, role=context.role),
            case_id=str(payload["case_id"]),
            expected_revision=int(payload["expected_revision"]),
            requested_outcome=Outcome(payload["requested_outcome"]),
            rationale=str(payload["rationale"]),
            policy_snapshot_id=str(payload["policy_snapshot_id"]),
            policy_snapshot_digest=str(payload["policy_snapshot_digest"]),
            content_hash=str(payload["content_hash"]),
        )


@dataclass(frozen=True)
class PolicyDecision:
    """A proposed enforcement decision (authoritative once committed).

    ``decision_id`` is a sha256 digest of the complete input/state tuple (excluding
    ``decided_at`` and ``_authority_token``), so it is deterministic and cannot collide
    across a re-pin or a re-analysis with a different model/severity (QUA-001).

    ``_authority_token`` is ``None`` unless minted by the engine; a directly constructed
    decision is rejected by ``EnforcementAuthority.commit`` with
    :class:`ForbiddenAuthorityError`.
    """

    decision_id: str
    case_id: str
    case_revision: int
    outcome: Outcome
    reason_id: str
    reason_text: str
    severity: Severity | None
    advisory_verdict: Verdict | None
    advisory_severity: Severity | None
    advisory_model_id: str | None
    advisory_model_version: str | None
    analysis_failure_code: FailureCode | None
    policy_snapshot_id: str
    policy_snapshot_digest: str
    content_hash: str
    requires_human_review: bool
    actor_ids: tuple[str, ...]
    decided_at: datetime
    _authority_token: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.decision_id, "decision_id")
        _require_nonempty(self.case_id, "case_id")
        _require_nonempty(self.reason_id, "reason_id")
        _require_nonempty(self.reason_text, "reason_text")
        _require_nonempty(self.policy_snapshot_id, "policy_snapshot_id")
        _require_nonempty(self.policy_snapshot_digest, "policy_snapshot_digest")
        _require_nonempty(self.content_hash, "content_hash")
        if not isinstance(self.case_revision, int) or self.case_revision < 1:
            raise _ContractError("case_revision must be an int >= 1")
        if not isinstance(self.outcome, Outcome):
            raise _ContractError("outcome must be an Outcome")
        if not isinstance(self.requires_human_review, bool):
            raise _ContractError("requires_human_review must be a bool")
        if not self.actor_ids:
            raise _ContractError("actor_ids must be non-empty")
        if not isinstance(self.decided_at, datetime):
            raise _ContractError("decided_at must be a datetime")


@dataclass(frozen=True)
class ReplayKey:
    """Replay identity: authenticated actor + idempotency key (bound to payload hash)."""

    actor_id: str
    idempotency_key: str

    def __post_init__(self) -> None:
        _require_nonempty(self.actor_id, "actor_id")
        _require_nonempty(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True)
class CommitResult:
    """Outcome of a policy commit attempt (interface-contracts "Commit result").

    ``COMMITTED`` carries a resolvable ``audit_id``; ``FAILED``/``CONFLICT`` make no
    success claim.
    """

    status: CommitStatus
    decision_id: str
    audit_id: str | None
    case_revision: int | None
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.status, CommitStatus):
            raise _ContractError("status must be a CommitStatus")
        if self.status is CommitStatus.COMMITTED:
            _require_nonempty(self.audit_id, "audit_id")
            if self.case_revision is None:
                raise _ContractError("COMMITTED must carry case_revision")
        elif self.status is CommitStatus.CONFLICT and self.audit_id is not None:
            raise _ContractError("CONFLICT must not carry an audit_id")


@dataclass(frozen=True)
class PrefilterResult:
    """Deterministic pre-filter output: sorted, case-folded labels."""

    labels: tuple[str, ...]
    high_severity: bool
    matched_terms: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.high_severity, bool):
            raise _ContractError("high_severity must be a bool")


def decision_payload(decision: PolicyDecision) -> dict[str, Any]:
    """Return the canonical input/state tuple used for ``decision_id`` and replay.

    Excludes ``decided_at`` and ``_authority_token`` (operational metadata, QUA-001).
    """
    return {
        "case_id": decision.case_id,
        "case_revision": decision.case_revision,
        "content_hash": decision.content_hash,
        "policy_snapshot_id": decision.policy_snapshot_id,
        "policy_snapshot_digest": decision.policy_snapshot_digest,
        "advisory_verdict": (
            decision.advisory_verdict.value if decision.advisory_verdict is not None else None
        ),
        "advisory_severity": (
            decision.advisory_severity.value if decision.advisory_severity is not None else None
        ),
        "advisory_model_id": decision.advisory_model_id,
        "advisory_model_version": decision.advisory_model_version,
        "analysis_failure_code": (
            decision.analysis_failure_code.value
            if decision.analysis_failure_code is not None
            else None
        ),
        "outcome": decision.outcome.value,
        "reason_id": decision.reason_id,
        "requires_human_review": decision.requires_human_review,
        "actor_ids": sorted(decision.actor_ids),
    }


def canonical_json(payload: Mapping[str, Any]) -> str:
    """Stable canonical JSON encoding used for every digest in the policy domain."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def decision_payload_from_fields(
    *,
    case_id: str,
    case_revision: int,
    content_hash: str,
    policy_snapshot_id: str,
    policy_snapshot_digest: str,
    advisory_verdict: Verdict | None,
    advisory_severity: Severity | None,
    advisory_model_id: str | None,
    advisory_model_version: str | None,
    analysis_failure_code: FailureCode | None,
    outcome: Outcome,
    reason_id: str,
    requires_human_review: bool,
    actor_ids: tuple[str, ...],
) -> dict[str, Any]:
    """Canonical decision identity tuple assembled from raw fields (QUA-001).

    Kept in sync with :func:`decision_payload`; used by the engine on pre-construction
    field values so ``decision_id`` is filled before the frozen DTO is built.
    """
    return {
        "case_id": case_id,
        "case_revision": case_revision,
        "content_hash": content_hash,
        "policy_snapshot_id": policy_snapshot_id,
        "policy_snapshot_digest": policy_snapshot_digest,
        "advisory_verdict": advisory_verdict.value if advisory_verdict is not None else None,
        "advisory_severity": (
            advisory_severity.value if advisory_severity is not None else None
        ),
        "advisory_model_id": advisory_model_id,
        "advisory_model_version": advisory_model_version,
        "analysis_failure_code": (
            analysis_failure_code.value if analysis_failure_code is not None else None
        ),
        "outcome": outcome.value,
        "reason_id": reason_id,
        "requires_human_review": requires_human_review,
        "actor_ids": sorted(actor_ids),
    }


def digest_of(payload: Mapping[str, Any]) -> str:
    """Return the sha256 hex digest of :func:`canonical_json` for ``payload``."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def bind_decision_id(values: Mapping[str, Any]) -> str:
    """Compose and hash a ``decision_id`` from the complete input/state tuple."""
    return digest_of(values)


def is_frozen_dto(obj: object) -> bool:
    """Return True when ``obj`` is a frozen dataclass (used by contract tests)."""
    if not dataclasses.is_dataclass(obj):
        return False
    params = getattr(type(obj), "__dataclass_params__", None)
    return bool(getattr(params, "frozen", False))


__all__ = [
    "ACTOR_ROLES",
    "ADVISORY_ROLES",
    "FINAL_STATUSES",
    "REVIEWABLE_STATUSES",
    "REVIEW_OUTCOMES",
    "ActorRef",
    "AdvisoryResult",
    "AnalysisFailure",
    "CaseSnapshot",
    "CaseStatus",
    "CommitResult",
    "CommitStatus",
    "FailureCode",
    "Outcome",
    "PolicyDecision",
    "PrefilterResult",
    "ReplayKey",
    "RequestContext",
    "ReviewRequest",
    "Severity",
    "Usage",
    "Verdict",
    "bind_decision_id",
    "canonical_json",
    "decision_payload",
    "decision_payload_from_fields",
    "digest_of",
    "effective_severity",
    "is_frozen_dto",
]
