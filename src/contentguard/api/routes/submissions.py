"""Submission/intake route (ADR-001; REQ-FUN-001, REQ-SEC-002)."""

from __future__ import annotations

import hashlib
import sqlite3
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from ..deps import require_actor
from ..intake_projection import committed_body, pending_body
from ..logging import log_event
from ..models import RequestContext, SubmissionRequest
from ..reconciliation import reconcile
from ..storage import IdempotencyConflict


router = APIRouter(prefix="/v1")


@router.post("/submissions")
def submit(
    body: SubmissionRequest,
    request: Request,
    actor: RequestContext = Depends(require_actor),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
) -> JSONResponse:
    """Accept text, reconcile replay, and report only durable confirmed state."""

    started = time.monotonic()
    repository = request.app.state.intake_repository
    config = request.app.state.api_config
    size = len(body.text.encode("utf-8"))
    if size > config.intake_max_bytes:
        repository.record_event(
            "submission_too_large",
            actor_id=actor.actor_id,
            details={"byte_count": size, "limit": config.intake_max_bytes},
        )
        raise HTTPException(
            status_code=413,
            detail=f"submission exceeds {config.intake_max_bytes} UTF-8 bytes",
        )

    payload_hash = hashlib.sha256(body.text.encode("utf-8")).hexdigest()
    try:
        intent, created = repository.create_intent(
            actor_id=actor.actor_id,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            content_text=body.text,
            effective_flags=config.feature_flags.as_dict(),
        )
    except IdempotencyConflict as exc:
        raise HTTPException(
            status_code=409, detail="idempotency key payload conflict"
        ) from exc
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503, detail="intake persistence unavailable"
        ) from exc

    if created:
        repository.record_event(
            "submission_accepted",
            actor_id=actor.actor_id,
            handoff_id=intent.handoff_id,
            details={"effective_flags": config.feature_flags.as_dict()},
        )

    if intent.result is not None:
        return _result_response(intent.result, replay=True)

    try:
        result = reconcile(
            intent,
            repository=repository,
            processor=request.app.state.processor,
            config=config,
        )
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="intake persistence unavailable") from exc

    latency_ms = round((time.monotonic() - started) * 1000, 3)
    log_event(
        "submission_result",
        actor_id=actor.actor_id,
        handoff_id=intent.handoff_id,
        case_id=None if result is None else result.case_id,
        latency_ms=latency_ms,
    )
    if result is None:
        return JSONResponse(status_code=202, content=pending_body(intent.handoff_id))
    return _result_response(result, replay=not created)


def _result_response(result: object, *, replay: bool) -> JSONResponse:
    status = getattr(result, "status")
    if status == "committed":
        return JSONResponse(
            status_code=200 if replay else 201,
            content=committed_body(result),
        )
    if status == "conflict":
        raise HTTPException(status_code=409, detail=getattr(result, "message"))
    raise HTTPException(status_code=503, detail=getattr(result, "message"))


__all__ = ["router"]
