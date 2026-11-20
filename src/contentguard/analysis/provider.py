"""Bounded nonblocking provider invocation (ADR-001, REQ-COS-001, REQ-INV-001/002).

Every public function cites its governing requirements.
"""

from __future__ import annotations

import asyncio

from .contracts import (
    AnalysisFailure,
    ContextConfig,
    ProviderRequest,
    ProviderResponse,
    Usage,
)
from .ports import ClockPort, ProviderPort


def remaining_ms(started_ms: int, elapsed_ms: int, per_call_cap_ms: int, deadline_ms: int) -> int:
    """Recompute remaining absolute and per-call budget without stale totals (REQ-COS-001)."""
    remaining = deadline_ms - (started_ms + elapsed_ms)
    return max(0, min(per_call_cap_ms, remaining))


def _consume_late_result(task: asyncio.Task[object]) -> None:
    """Retrieve late task exceptions without applying their results (REQ-INV-001)."""
    if task.done() and not task.cancelled():
        task.exception()


async def invoke_provider(
    request: ProviderRequest,
    deadline_ms: int,
    clock: ClockPort,
    provider: ProviderPort,
    config: ContextConfig,
) -> ProviderResponse | AnalysisFailure:
    """Invoke provider with asyncio.wait; cancel without awaiting suppression (REQ-INV-001)."""
    started = clock.monotonic_ms()
    budget = remaining_ms(started, 0, config.per_call_cap_ms, deadline_ms)
    if budget <= 0:
        return AnalysisFailure("timeout", "provider deadline exhausted", request.attempt, Usage(0, 0, True), "unknown")
    task = asyncio.ensure_future(provider.invoke(request))
    done, _ = await asyncio.wait({task}, timeout=budget / 1000, return_when=asyncio.FIRST_COMPLETED)
    if not done:
        task.cancel()
        task.add_done_callback(_consume_late_result)
        return AnalysisFailure("timeout", "provider timeout", request.attempt, Usage(0, 0, True), "unknown")
    if task.cancelled():
        return AnalysisFailure(
            "provider_unavailable", "provider cancelled", request.attempt, Usage(0, 0, True), "unknown"
        )
    error = task.exception()
    if error is not None:
        return AnalysisFailure(
            "provider_unavailable", f"provider error: {type(error).__name__}", request.attempt, Usage(0, 0, True), "unknown"
        )
    result = task.result()
    if not isinstance(result, (ProviderResponse, AnalysisFailure)):
        return AnalysisFailure(
            "invalid_response", "invalid provider response type", request.attempt, Usage(0, 0, True), "unknown"
        )
    if isinstance(result, AnalysisFailure):
        if result.attempt != request.attempt:
            return AnalysisFailure(
                result.code, "failure identity mismatch", request.attempt, result.usage, "unknown"
            )
        return result
    if result.attempt != request.attempt:
        return AnalysisFailure(
            "invalid_response", "provider attempt mismatch", request.attempt, Usage(0, 0, True), "unknown"
        )
    return result
