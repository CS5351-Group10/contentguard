"""Authorized case/audit lookup routes (ADR-001; REQ-FUN-001, REQ-SEC-004)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from ..authz import may_read_audit, may_read_case
from ..deps import require_actor
from ..intake_projection import committed_body, pending_body
from ..schemas import ProcessingResult, RequestContext
from ..storage import StorageUnavailable

router = APIRouter(prefix="/v1")


def _terminal_intent_response(result: ProcessingResult) -> JSONResponse:
    """Project a terminal intake result truthfully — never as pending success."""

    if result.status == "conflict":
        raise HTTPException(status_code=409, detail=result.message)
    if result.status == "failed":
        raise HTTPException(status_code=503, detail=result.message)
    raise ValueError(f"unexpected terminal intake status: {result.status}")


@router.get("/cases/{case_id}")
def get_case(
    case_id: str,
    request: Request,
    actor: Annotated[RequestContext, Depends(require_actor)],
) -> JSONResponse:
    """Return an authorized case or a truthful API-owned reconciliation state."""

    repository = request.app.state.lookup_repository
    try:
        case = repository.get_case(case_id)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail="storage unavailable") from exc
    if case is None:
        intent = request.app.state.intake_repository.get_intent(case_id)
        if intent is not None and intent.actor_id == actor.actor_id:
            if intent.result is not None:
                if intent.result.status == "committed":
                    return JSONResponse(
                        status_code=200, content=committed_body(intent.result)
                    )
                if intent.result.status == "pending_unconfirmed":
                    return JSONResponse(
                        status_code=202, content=pending_body(intent.handoff_id)
                    )
                # Terminal failed/conflict results are durable outcomes, not
                # pending state: projecting them as 202 would claim that work is
                # still reconciling (REQ-FUN-001, REQ-INV-004).
                _terminal_intent_response(intent.result)
            return JSONResponse(status_code=202, content=pending_body(intent.handoff_id))
        raise HTTPException(status_code=404, detail="case not found")
    try:
        readable = may_read_case(actor, case, repository)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail="storage unavailable") from exc
    if not readable:
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
    actor: Annotated[RequestContext, Depends(require_actor)],
) -> JSONResponse:
    """Return immutable decision evidence after owner/grant authorization."""

    repository = request.app.state.lookup_repository
    try:
        audit = repository.get_audit(audit_id)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail="storage unavailable") from exc
    if audit is None:
        raise HTTPException(status_code=404, detail="audit not found")
    try:
        readable = may_read_audit(actor, audit, repository)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail="storage unavailable") from exc
    if not readable:
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
