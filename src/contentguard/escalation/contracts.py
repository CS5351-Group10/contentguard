"""Escalation queue DTO — minimal, transaction-enlisted (REQ-INV-003/004).

S1 needs only a queue entry so the policy kernel can prove an atomic
case+queue+audit commit; the repository, intake, views and duplicate-delivery handling
are S2-owned. This module must not import ``contentguard.policy``.

CP1 defines the DTO only; the repository arrives in the persistence slice.
"""

from __future__ import annotations

from dataclasses import dataclass

QUEUE_OUTCOMES: frozenset[str] = frozenset({"hold", "escalate"})


def _require_nonempty(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True)
class QueueEntry:
    """One hold/escalate queue entry, identified by ``(case_id, case_revision)``."""

    case_id: str
    case_revision: int
    outcome: str  # hold / escalate
    reason_id: str
    enqueued_at: str

    def __post_init__(self) -> None:
        _require_nonempty(self.case_id, "case_id")
        _require_nonempty(self.reason_id, "reason_id")
        _require_nonempty(self.enqueued_at, "enqueued_at")
        if not isinstance(self.case_revision, int) or self.case_revision < 1:
            raise ValueError("case_revision must be an int >= 1")
        if self.outcome not in QUEUE_OUTCOMES:
            raise ValueError(f"outcome {self.outcome!r} not in {sorted(QUEUE_OUTCOMES)}")


__all__ = ["QUEUE_OUTCOMES", "QueueEntry"]
