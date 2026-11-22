"""Shared synchronous/worker intake reconciliation (ADR-001; REQ-INV-002/004)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from .config import ApiConfig
from .logging import log_event
from .schemas import ProcessingResult, ProcessingUnavailable
from .storage import IntakeIntent, IntakeRepository


class SubmissionProcessor(Protocol):
    def process(
        self,
        *,
        handoff_id: str,
        actor_id: str,
        text: str,
        effective_flags: Mapping[str, bool],
    ) -> ProcessingResult: ...


def reconcile(
    intent: IntakeIntent,
    *,
    repository: IntakeRepository,
    processor: SubmissionProcessor,
    config: ApiConfig,
) -> ProcessingResult | None:
    """Acquire one reservation, run processing, and persist only truthful state."""

    if intent.result is not None:
        return intent.result
    if not repository.acquire_lease(intent.handoff_id, config.lease_seconds):
        return None
    try:
        result = processor.process(
            handoff_id=intent.handoff_id,
            actor_id=intent.actor_id,
            text=intent.content_text,
            # The flags pinned at intake time — never the current runtime
            # configuration — decide the processing behavior, so a replay after a
            # runtime feature-configuration change processes under the original
            # effective flags (REQ-FUN-007, REQ-INV-001).
            effective_flags=dict(intent.effective_flags),
        )
    except ProcessingUnavailable as exc:
        repository.release_pending(intent.handoff_id)
        repository.record_event(
            "processing_unavailable",
            actor_id=intent.actor_id,
            handoff_id=intent.handoff_id,
            details={"failure_code": exc.code},
        )
        log_event(
            "processing_unavailable",
            actor_id=intent.actor_id,
            handoff_id=intent.handoff_id,
            failure_code=exc.code,
        )
        return None
    repository.save_result(intent.handoff_id, result)
    return result


def recover_pending(
    intent: IntakeIntent,
    *,
    repository: IntakeRepository,
    processor: SubmissionProcessor,
    config: ApiConfig,
) -> ProcessingResult | None:
    """Probe one expired reservation once through the shared reconciliation path."""

    if intent.result is not None:
        return intent.result
    repository.record_event(
        "pending_recovery_attempt",
        actor_id=intent.actor_id,
        handoff_id=intent.handoff_id,
        details={"state": intent.state},
    )
    result = reconcile(intent, repository=repository, processor=processor, config=config)
    log_event(
        "pending_recovery_attempt",
        actor_id=intent.actor_id,
        handoff_id=intent.handoff_id,
        outcome="probed" if result is not None else "deferred",
    )
    return result


__all__ = ["SubmissionProcessor", "reconcile", "recover_pending"]
