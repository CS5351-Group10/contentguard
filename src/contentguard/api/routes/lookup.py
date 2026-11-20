"""Authorized case/audit lookup routes (ADR-001; REQ-FUN-001, REQ-SEC-004)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from ..authz import may_read_audit, may_read_case
from ..deps import require_actor
from ..intake_projection import committed_body, pending_body
from ..models import RequestContext


router = APIRouter(prefix="/v1")


@router.get("/cases/{case_id}")
def get_case(
    case_id: str,
    request: Request,
    actor: RequestContext = Depends(require_actor),
) -> JSONResponse:
    """Return an authorized case or a truthful API-owned reconciliation state."""

    repository = request.app.state.lookup_repository
    case = repository.get_case(case_id)
    if case is None:
        intent = request.app.state.intake_repository.get_intent(case_id)
        if intent is not None and intent.actor_id == actor.actor_id:
            if intent.result is not None and intent.result.status == "committed":
                return JSONResponse(status_code=200, content=committed_body(intent.result))
            return JSONResponse(status_code=202, content=pending_body(intent.handoff_id))
        raise HTTPException(status_code=404, detail="case not found")
    if not may_read_case(actor, case, repository):
        raise HTTPException(status_code=403, detail="forbidden")
    return JSONResponse(
        status_code=200,
        content={
            "case_id": case.case_id,
            "revision": case.revision,
            "status": case.status,
            "content_hash": case.content_hash,
            "policy_snapshot_id": case.policy_snapshot_id,
            "policy_snapshot_digest": case.policy_snapshot_digest,
            "audit_id": case.audit_id,
        },
    )


@router.get("/audits/{audit_id}")
def get_audit(
    audit_id: str,
    request: Request,
    actor: RequestContext = Depends(require_actor),
) -> JSONResponse:
    """Return immutable decision evidence after owner/grant authorization."""

    repository = request.app.state.lookup_repository
    audit = repository.get_audit(audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="audit not found")
    if not may_read_audit(actor, audit, repository):
        raise HTTPException(status_code=403, detail="forbidden")
    return JSONResponse(
        status_code=200,
        content={
            "audit_id": audit.audit_id,
            "decision_id": audit.decision_id,
            "case_id": audit.case_id,
            "case_revision": audit.case_revision,
            "outcome": audit.outcome,
            "policy_reason_id": audit.policy_reason_id,
            "policy_snapshot_id": audit.policy_snapshot_id,
            "policy_snapshot_digest": audit.policy_snapshot_digest,
        },
    )


__all__ = ["router"]
