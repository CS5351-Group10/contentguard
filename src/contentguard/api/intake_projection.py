"""Truthful HTTP projection of intake state (ADR-001; REQ-FUN-001, REQ-INV-004)."""

from __future__ import annotations

from .schemas import ProcessingResult


def committed_body(result: ProcessingResult) -> dict[str, object]:
    """Expose a committed result only when its resolvable audit fields exist."""

    if result.status != "committed" or not result.audit_id or not result.case_id:
        raise ValueError("only a committed result with case and audit IDs is successful")
    return {
        "status": "committed",
        "case_id": result.case_id,
        "case_revision": result.case_revision,
        "decision_id": result.decision_id,
        "audit_id": result.audit_id,
        "outcome": result.outcome,
    }


def pending_body(handoff_id: str) -> dict[str, str]:
    """Return a durable 202 projection without outcome or committed audit claims."""

    return {
        "status": "pending_unconfirmed",
        "handoff_id": handoff_id,
        "reconciliation_url": f"/v1/cases/{handoff_id}",
    }


__all__ = ["committed_body", "pending_body"]
