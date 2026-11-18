"""Audit record schema — exactly one row per decision (REQ-INV-004).

Structural rule 5: this module must not import ``contentguard.policy``. It therefore
validates against local value sets (``VALID_OUTCOMES`` / ``VALID_VERDICTS`` /
``VALID_FAILURE_CODES``) that a test keeps in lockstep with the policy enums, so the
duplication cannot silently drift.

CP1 defines the record schema only; the repository and its lockstep test arrive in the
persistence slice.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .errors import AuditValidationError

VALID_OUTCOMES: frozenset[str] = frozenset({"approve", "hold", "reject", "escalate"})
VALID_VERDICTS: frozenset[str] = frozenset({"allow", "review", "violate"})
VALID_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "provider_unavailable",
        "timeout",
        "invalid_response",
        "grounding_unavailable",
        "context_overflow",
    }
)

HUMAN_REVIEW_REASON_ID = "RULE-HUMAN-REVIEW"

REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "decision_id",
        "case_id",
        "case_revision",
        "content_hash",
        "ai_verdict",
        "analysis_failure_code",
        "policy_reason_id",
        "policy_snapshot_id",
        "policy_snapshot_digest",
        "outcome",
        "actor_ids",
        "decided_at",
    }
)


def _require_nonempty(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuditValidationError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True)
class AuditRecord:
    """Immutable audit row for one committed decision (interface-contracts "Audit: append").

    Validation: string fields non-empty; ``case_revision >= 1``; ``outcome`` in
    ``VALID_OUTCOMES``; ``ai_verdict`` (when non-null) in ``VALID_VERDICTS``; **exactly
    one of** ``ai_verdict`` / ``analysis_failure_code`` is non-null (a typed failure is
    not a fabricated verdict); ``actor_ids`` non-empty and contains ``"policy"``, an
    ``ai:<model>`` actor whenever ``ai_verdict`` is set, and a ``reviewer:<id>`` actor
    when ``policy_reason_id == RULE-HUMAN-REVIEW``; ``decided_at`` parses as a
    timezone-aware ISO-8601 string.
    """

    decision_id: str
    case_id: str
    case_revision: int
    content_hash: str
    ai_verdict: str | None
    analysis_failure_code: str | None
    policy_reason_id: str
    policy_snapshot_id: str
    policy_snapshot_digest: str
    outcome: str
    actor_ids: tuple[str, ...]
    decided_at: str

    def __post_init__(self) -> None:
        _require_nonempty(self.decision_id, "decision_id")
        _require_nonempty(self.case_id, "case_id")
        _require_nonempty(self.content_hash, "content_hash")
        _require_nonempty(self.policy_reason_id, "policy_reason_id")
        _require_nonempty(self.policy_snapshot_id, "policy_snapshot_id")
        _require_nonempty(self.policy_snapshot_digest, "policy_snapshot_digest")

        if not isinstance(self.case_revision, int) or self.case_revision < 1:
            raise AuditValidationError("case_revision must be an int >= 1")

        if self.outcome not in VALID_OUTCOMES:
            raise AuditValidationError(
                f"outcome {self.outcome!r} not in {sorted(VALID_OUTCOMES)}"
            )

        if self.ai_verdict is not None and self.ai_verdict not in VALID_VERDICTS:
            raise AuditValidationError(
                f"ai_verdict {self.ai_verdict!r} not in {sorted(VALID_VERDICTS)}"
            )
        if (
            self.analysis_failure_code is not None
            and self.analysis_failure_code not in VALID_FAILURE_CODES
        ):
            raise AuditValidationError(
                f"analysis_failure_code {self.analysis_failure_code!r} not in "
                f"{sorted(VALID_FAILURE_CODES)}"
            )

        has_verdict = self.ai_verdict is not None
        has_failure = self.analysis_failure_code is not None
        if has_verdict == has_failure:
            raise AuditValidationError(
                "exactly one of ai_verdict / analysis_failure_code must be non-null"
            )

        if not isinstance(self.actor_ids, tuple) or not self.actor_ids:
            raise AuditValidationError("actor_ids must be a non-empty tuple")
        for actor in self.actor_ids:
            _require_nonempty(actor, "actor_ids entry")
        if "policy" not in self.actor_ids:
            raise AuditValidationError("actor_ids must contain 'policy'")
        if has_verdict and not any(a.startswith("ai:") for a in self.actor_ids):
            raise AuditValidationError("a record with ai_verdict requires an 'ai:<model>' actor")
        if self.policy_reason_id == HUMAN_REVIEW_REASON_ID and not any(
            a.startswith("reviewer:") for a in self.actor_ids
        ):
            raise AuditValidationError(
                "a RULE-HUMAN-REVIEW record requires a 'reviewer:<id>' actor"
            )

        _require_nonempty(self.decided_at, "decided_at")
        parsed = _parse_aware_iso(self.decided_at)
        if parsed is None:
            raise AuditValidationError(
                "decided_at must be a timezone-aware ISO-8601 datetime"
            )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> AuditRecord:
        """Build a record from a mapping, rejecting missing/unknown keys and bad types."""
        if not isinstance(payload, Mapping):
            raise AuditValidationError("audit payload must be a mapping")
        keys = set(payload)
        unknown = keys - REQUIRED_KEYS
        if unknown:
            raise AuditValidationError(f"audit payload has unexpected keys: {sorted(unknown)}")
        missing = REQUIRED_KEYS - keys
        if missing:
            raise AuditValidationError(f"audit payload missing keys: {sorted(missing)}")

        actor_ids_raw = payload["actor_ids"]
        if not isinstance(actor_ids_raw, (list, tuple)):
            raise AuditValidationError("actor_ids must be a list or tuple")
        return cls(
            decision_id=payload["decision_id"],
            case_id=payload["case_id"],
            case_revision=payload["case_revision"],
            content_hash=payload["content_hash"],
            ai_verdict=payload["ai_verdict"],
            analysis_failure_code=payload["analysis_failure_code"],
            policy_reason_id=payload["policy_reason_id"],
            policy_snapshot_id=payload["policy_snapshot_id"],
            policy_snapshot_digest=payload["policy_snapshot_digest"],
            outcome=payload["outcome"],
            actor_ids=tuple(actor_ids_raw),
            decided_at=payload["decided_at"],
        )


def _parse_aware_iso(value: str) -> datetime | None:
    """Parse an ISO-8601 timestamp, returning ``None`` unless it is timezone-aware."""
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


__all__ = [
    "HUMAN_REVIEW_REASON_ID",
    "REQUIRED_KEYS",
    "VALID_FAILURE_CODES",
    "VALID_OUTCOMES",
    "VALID_VERDICTS",
    "AuditRecord",
]
