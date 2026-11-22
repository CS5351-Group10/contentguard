"""Human review queue and transition routes (ADR-001; REQ-FUN-003, REQ-INV-003)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from ..authz import may_review_case
from ..deps import require_actor
from ..errors import MandatoryRuleViolation
from ..intake_projection import committed_body
from ..schemas import RequestContext, ReviewRequestBody
from ..storage import StorageUnavailable

router = APIRouter(prefix="/v1")


@router.get("/review-queue")
def list_review_queue(
    request: Request,
    actor: Annotated[RequestContext, Depends(require_actor)],
) -> JSONResponse:
    """List only queue entries granted to the authenticated moderator."""

    if actor.actor_type != "moderator" or "review-queue:read" not in actor.scopes:
        raise HTTPException(status_code=403, detail="forbidden")
    repository = request.app.state.review_repository
    try:
        open_items = repository.list_open_queue()
        items = [
            item
            for item in open_items
            if repository.has_case_grant(item.case_id, actor.actor_id)
        ]
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail="storage unavailable") from exc
    return JSONResponse(
        status_code=200,
        content=[
            {
                "case_id": item.case_id,
                "case_revision": item.case_revision,
                "outcome": item.outcome,
                "reason_id": item.reason_id,
                "severity": item.severity,
                "enqueued_at": item.enqueued_at,
            }
            for item in items
        ],
    )


@router.post("/cases/{case_id}/reviews")
def review_case(
    case_id: str,
    body: ReviewRequestBody,
    request: Request,
    actor: Annotated[RequestContext, Depends(require_actor)],
) -> JSONResponse:
    """Submit current human evidence to the policy-owned review entry point."""

    repository = request.app.state.review_repository
    case = repository.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")
    try:
        reviewable = may_review_case(actor, case_id, repository)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail="storage unavailable") from exc
    if not reviewable:
        raise HTTPException(status_code=403, detail="forbidden")
    if body.expected_revision != case.revision:
        raise HTTPException(status_code=409, detail="stale case revision")
    policy = request.app.state.review_policy
    if policy is None:
        raise HTTPException(status_code=503, detail="review policy unavailable")
    try:
        result = policy.review_and_commit(
            case=case,
            reviewer_id=actor.actor_id,
            expected_revision=body.expected_revision,
            requested_outcome=body.requested_outcome,
            rationale=body.rationale,
        )
    except MandatoryRuleViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result.status == "committed":
        return JSONResponse(status_code=200, content=committed_body(result))
    if result.status == "conflict":
        raise HTTPException(status_code=409, detail=result.message)
    raise HTTPException(status_code=503, detail=result.message)


__all__ = ["router"]
