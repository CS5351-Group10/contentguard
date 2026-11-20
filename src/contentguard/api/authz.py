"""Central API authorization matrix (ADR-001; REQ-SEC-003/004)."""

from __future__ import annotations

from typing import Protocol

from .models import AuditView, CaseView, RequestContext


class GrantReader(Protocol):
    def has_case_grant(self, case_id: str, actor_id: str) -> bool: ...


def may_read_case(actor: RequestContext, case: CaseView, grants: GrantReader) -> bool:
    """Allow the submitter owner or a moderator explicitly granted this case."""

    if actor.actor_type == "submitter":
        return actor.actor_id == case.owner_id and "case:read-own" in actor.scopes
    return (
        "case:read-granted" in actor.scopes
        and grants.has_case_grant(case.case_id, actor.actor_id)
    )


def may_read_audit(actor: RequestContext, audit: AuditView, grants: GrantReader) -> bool:
    """Apply the same case-scoped matrix to immutable audit evidence."""

    if actor.actor_type == "submitter":
        return actor.actor_id == audit.owner_id and "audit:read-own" in actor.scopes
    return (
        "audit:read-granted" in actor.scopes
        and grants.has_case_grant(audit.case_id, actor.actor_id)
    )


def may_review_case(actor: RequestContext, case_id: str, grants: GrantReader) -> bool:
    """Require moderator role, review scope, and a current case grant."""

    return (
        actor.actor_type == "moderator"
        and "review:create" in actor.scopes
        and grants.has_case_grant(case_id, actor.actor_id)
    )


__all__ = ["may_read_audit", "may_read_case", "may_review_case"]
