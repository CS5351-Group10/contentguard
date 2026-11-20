"""S2 closed feature-flag tests (ADR-001; REQ-FUN-007, REQ-INV-001).

The only MVP flag is advisory reconsideration.  Effective values are trusted
configuration, never client authority, and no flag state bypasses policy mediation.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from contentguard.api.app import create_app
from contentguard.api.config import (
    ActorConfig,
    ApiConfig,
    ConfigurationError,
    FeatureFlags,
)
from contentguard.api.models import ProcessingResult


TOKEN = "flag-test-token"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _config(tmp_path: Path, flags: FeatureFlags) -> ApiConfig:
    return ApiConfig(
        database_path=tmp_path / "flags.sqlite3",
        api_tokens={
            _digest(TOKEN): ActorConfig(
                actor_id="submitter-1",
                actor_type="submitter",
                scopes=frozenset({"submission:create"}),
            )
        },
        intake_max_bytes=16_384,
        lease_seconds=30,
        recovery_interval_seconds=5,
        max_attempts=5,
        start_recovery_worker=False,
        feature_flags=flags,
    )


def _headers(key: str = "flags-idem") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Idempotency-Key": key,
    }


def _committed() -> ProcessingResult:
    return ProcessingResult(
        status="committed",
        case_id="case-flags",
        case_revision=2,
        decision_id="decision-flags",
        audit_id="audit-flags",
        outcome="hold",
        message="committed",
    )


@dataclass
class FakeProcessor:
    """Represents the mandatory API-to-policy mediation boundary."""

    calls: list[dict[str, object]] = field(default_factory=list)

    def process(self, **kwargs: object) -> ProcessingResult:
        self.calls.append(kwargs)
        return _committed()


def test_only_reconsideration_flag_is_accepted() -> None:
    """REQ-FUN-007: the closed allowlist accepts its one documented flag."""

    flags = FeatureFlags.from_mapping(
        {"analysis.reconsideration_enabled": True}
    )

    assert flags.reconsideration_enabled is True
    assert flags.as_dict() == {"analysis.reconsideration_enabled": True}


@pytest.mark.parametrize(
    "mapping",
    [
        {"analysis.unknown": True},
        {"policy.disabled": True},
        {"analysis.reconsideration_enabled": "true"},
        {"analysis.reconsideration_enabled": 1},
        {"analysis.reconsideration_enabled": None},
    ],
)
def test_unknown_or_invalid_flags_fail_closed(mapping: dict[str, object]) -> None:
    """REQ-FUN-007/REQ-INV-001 negative: unknown or non-boolean flags are rejected."""

    with pytest.raises(ConfigurationError):
        FeatureFlags.from_mapping(mapping)


def test_client_cannot_override_effective_flags(tmp_path: Path) -> None:
    """REQ-INV-001 negative: submitted text cannot select trusted runtime flags."""

    processor = FakeProcessor()
    config = _config(tmp_path, FeatureFlags(reconsideration_enabled=False))
    with TestClient(create_app(config=config, processor=processor)) as client:
        response = client.post(
            "/v1/submissions",
            headers=_headers(),
            json={
                "text": "ordinary content",
                "flags": {"analysis.reconsideration_enabled": True},
            },
        )

    assert response.status_code == 422
    assert processor.calls == []


def test_effective_flag_is_pinned_in_intake_and_operational_audit(
    tmp_path: Path,
) -> None:
    """REQ-FUN-007: effective configuration is pinned to durable request evidence."""

    flags = FeatureFlags(reconsideration_enabled=True)
    processor = FakeProcessor()
    config = _config(tmp_path, flags)
    with TestClient(create_app(config=config, processor=processor)) as client:
        response = client.post(
            "/v1/submissions",
            headers=_headers(),
            json={"text": "content with configured reconsideration"},
        )
        assert client.app.state.api_config.feature_flags.as_dict() == flags.as_dict()

    assert response.status_code == 201
    with sqlite3.connect(config.database_path) as conn:
        intent_flags = conn.execute(
            "SELECT effective_flags FROM intake_intents WHERE actor_id = ?",
            ("submitter-1",),
        ).fetchone()
        event_details = conn.execute(
            "SELECT details_json FROM api_events "
            "WHERE event_type = 'submission_accepted' ORDER BY event_id DESC LIMIT 1"
        ).fetchone()

    assert intent_flags is not None
    assert json.loads(str(intent_flags[0])) == flags.as_dict()
    assert event_details is not None
    assert json.loads(str(event_details[0]))["effective_flags"] == flags.as_dict()


@pytest.mark.parametrize("enabled", [False, True])
def test_no_flag_state_disables_policy_mediation(tmp_path: Path, enabled: bool) -> None:
    """REQ-INV-001 negative: both flag states still call the policy processor once."""

    processor = FakeProcessor()
    config = _config(
        tmp_path,
        FeatureFlags(reconsideration_enabled=enabled),
    )
    with TestClient(create_app(config=config, processor=processor)) as client:
        response = client.post(
            "/v1/submissions",
            headers=_headers(f"flags-{enabled}"),
            json={"text": "policy mediation remains mandatory"},
        )

    assert response.status_code == 201
    assert response.json()["audit_id"] == "audit-flags"
    assert len(processor.calls) == 1
