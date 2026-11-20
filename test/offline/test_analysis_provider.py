"""Provider timeout and budget tests for ADR-001, REQ-COS-001, REQ-INV-001/002."""

from __future__ import annotations

import asyncio

import pytest
from fakes import analysis as fa

from contentguard.analysis import provider
from contentguard.analysis.contracts import (
    AnalysisFailure,
    ProviderRequest,
    ProviderResponse,
)


def request() -> ProviderRequest:
    """Build a bounded provider request (REQ-COS-001)."""
    return ProviderRequest(fa.make_attempt(), "serialized context", 1024)


def test_remaining_budget_recomputed_from_absolute_deadline():
    """Remaining budget uses absolute deadline and per-call cap, not stale total (REQ-COS-001)."""
    value = provider.remaining_ms(1000, 30, 20, 1100)
    assert value == 20


def test_normal_provider_response():
    """A suite-owned provider response is accepted (REQ-FUN-002, REQ-SEC-001)."""
    response = asyncio.run(
        provider.invoke_provider(request(), 1200, fa.FakeClock(), fa.FakeProvider(), fa.make_config())
    )
    assert not isinstance(response, AnalysisFailure)
    assert response.usage.input_tokens == 3


def test_provider_unavailable_maps_to_typed_failure():
    """Provider unavailability maps to provider_unavailable (REQ-INV-002)."""
    result = asyncio.run(
        provider.invoke_provider(request(), 1200, fa.FakeClock(), fa.FakeProvider("unavailable"), fa.make_config())
    )
    assert isinstance(result, AnalysisFailure)
    assert result.code == "provider_unavailable"


def test_timeout_discards_suppressed_late_result():
    """Cancelled provider result is discarded even if cancellation is suppressed (REQ-INV-001)."""
    fake = fa.FakeProvider("cancel_suppressing")
    result = asyncio.run(
        provider.invoke_provider(request(), 1010, fa.FakeClock(), fake, fa.make_config())
    )
    assert isinstance(result, AnalysisFailure)
    assert result.code == "timeout"
    assert len(fake.calls) == 1
    assert result.usage.usage_unknown is True


def test_unknown_usage_flag_is_preserved():
    """Unknown provider usage remains explicitly unknown (REQ-COS-001)."""
    response = asyncio.run(
        provider.invoke_provider(request(), 1200, fa.FakeClock(), fa.FakeProvider("unknown_usage"), fa.make_config())
    )
    assert isinstance(response, ProviderResponse)
    assert response.usage.usage_unknown is True


@pytest.mark.parametrize("mode", ["wrong_type", "wrong_identity", "exception"])
def test_invalid_provider_shape_or_identity_is_typed_failure(mode):
    """Wrong type, identity or raised exception yields a typed failure (REQ-INV-002, REQ-SEC-001)."""
    result = asyncio.run(
        provider.invoke_provider(request(), 1200, fa.FakeClock(), fa.FakeProvider(mode), fa.make_config())
    )
    assert isinstance(result, AnalysisFailure)
    assert result.code in {"invalid_response", "provider_unavailable"}
