"""S2 submission/intake API tests (ADR-001; REQ-FUN-001, REQ-SEC-002).

These black-box tests also cover the durable recovery and no-duplicate-effect
boundaries in REQ-INV-002, REQ-INV-004, and REQ-QUA-002.  The API package is
deliberately absent at the RED checkpoint.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections import deque
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from contentguard.api.app import create_app
from contentguard.api.config import ActorConfig, ApiConfig
from contentguard.api.reconciliation import recover_pending
from contentguard.api.schemas import ProcessingResult, ProcessingUnavailable
from contentguard.api.storage import IntakeIntent, IntakeRepository

TOKEN = "submitter-secret-token"
ACTOR_ID = "submitter-1"


def _token_digest(token: str = TOKEN) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class FakeProcessor:
    """Deterministic S3-to-S1 boundary fake; it never executes policy itself."""

    results: deque[ProcessingResult | Exception]
    calls: list[tuple[str, str, str, dict[str, bool]]] = field(default_factory=list)

    def process(
        self,
        *,
        handoff_id: str,
        actor_id: str,
        text: str,
        effective_flags: Mapping[str, bool],
    ) -> ProcessingResult:
        self.calls.append((handoff_id, actor_id, text, dict(effective_flags)))
        result = self.results.popleft()
        if isinstance(result, Exception):
            raise result
        return result


def _committed_result() -> ProcessingResult:
    return ProcessingResult(
        status="committed",
        case_id="case-1",
        case_revision=2,
        decision_id="decision-1",
        audit_id="audit-1",
        outcome="hold",
        message="committed",
    )


def _config(
    tmp_path: Path,
    *,
    intake_max_bytes: int = 16_384,
) -> ApiConfig:
    return ApiConfig(
        database_path=tmp_path / "contentguard.sqlite3",
        api_tokens={
            _token_digest(): ActorConfig(
                actor_id=ACTOR_ID,
                actor_type="submitter",
                scopes=frozenset({"submission:create", "case:read-own"}),
            )
        },
        intake_max_bytes=intake_max_bytes,
        lease_seconds=30,
        recovery_interval_seconds=5,
        max_attempts=5,
        start_recovery_worker=False,
    )


def _headers(key: str = "idem-1") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Idempotency-Key": key,
    }


@pytest.fixture
def client_factory(
    tmp_path: Path,
) -> Iterator[
    tuple[
        Callable[[FakeProcessor], TestClient],
        ApiConfig,
    ]
]:
    """Build a no-worker test app with a real temporary SQLite intake store."""

    config = _config(tmp_path)
    clients: list[TestClient] = []

    def build(processor: FakeProcessor) -> TestClient:
        client = TestClient(create_app(config=config, processor=processor))
        clients.append(client)
        return client

    yield build, config
    for client in clients:
        client.close()


def test_new_submission_commits_and_replay_is_idempotent(
    client_factory: tuple[Callable[[FakeProcessor], TestClient], ApiConfig],
) -> None:
    """REQ-FUN-001/REQ-INV-004: 201 commits once; replay is 200 with one effect."""

    build, _ = client_factory
    processor = FakeProcessor(deque([_committed_result()]))
    client = build(processor)

    created = client.post(
        "/v1/submissions",
        headers=_headers(),
        json={"text": "please review this text"},
    )
    replayed = client.post(
        "/v1/submissions",
        headers=_headers(),
        json={"text": "please review this text"},
    )

    assert created.status_code == 201
    assert created.json() == {
        "status": "committed",
        "case_id": "case-1",
        "case_revision": 2,
        "decision_id": "decision-1",
        "audit_id": "audit-1",
        "outcome": "hold",
    }
    assert replayed.status_code == 200
    assert replayed.json() == created.json()
    assert len(processor.calls) == 1


def test_idempotency_key_payload_conflict_has_no_second_effect(
    client_factory: tuple[Callable[[FakeProcessor], TestClient], ApiConfig],
) -> None:
    """REQ-FUN-001/REQ-QUA-002: one key bound to another payload returns 409."""

    build, _ = client_factory
    processor = FakeProcessor(deque([_committed_result()]))
    client = build(processor)

    assert client.post(
        "/v1/submissions", headers=_headers(), json={"text": "first payload"}
    ).status_code == 201
    conflict = client.post(
        "/v1/submissions", headers=_headers(), json={"text": "different payload"}
    )

    assert conflict.status_code == 409
    assert conflict.json() == {"detail": "idempotency key payload conflict"}
    assert len(processor.calls) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"text": ""},
        {"text": "   "},
        {"text": 7},
        {"text": "valid", "actor_id": "forged"},
    ],
)
def test_invalid_input_is_422_before_processing(
    client_factory: tuple[Callable[[FakeProcessor], TestClient], ApiConfig],
    payload: dict[str, object],
) -> None:
    """REQ-SEC-002: Pydantic rejects malformed/privileged input with no model call."""

    build, _ = client_factory
    processor = FakeProcessor(deque([_committed_result()]))
    response = build(processor).post(
        "/v1/submissions", headers=_headers(), json=payload
    )

    assert response.status_code == 422
    assert processor.calls == []


def test_utf8_byte_limit_returns_413_and_records_one_event(tmp_path: Path) -> None:
    """REQ-SEC-002: content above the configured UTF-8 limit makes zero model calls."""

    config = _config(tmp_path, intake_max_bytes=8)
    processor = FakeProcessor(deque([_committed_result()]))
    with TestClient(create_app(config=config, processor=processor)) as client:
        response = client.post(
            "/v1/submissions",
            headers=_headers(),
            json={"text": "123456789"},
        )

    assert response.status_code == 413
    assert response.json() == {"detail": "submission exceeds 8 UTF-8 bytes"}
    assert processor.calls == []
    with sqlite3.connect(config.database_path) as conn:
        rows = conn.execute(
            "SELECT event_type, actor_id FROM api_events ORDER BY event_id"
        ).fetchall()
    assert rows == [("submission_too_large", ACTOR_ID)]


def test_provider_unavailable_returns_durable_202(
    client_factory: tuple[Callable[[FakeProcessor], TestClient], ApiConfig],
) -> None:
    """REQ-INV-002/REQ-FUN-001: unavailable processing leaves a durable 202 intent."""

    build, config = client_factory
    processor = FakeProcessor(
        deque([ProcessingUnavailable("provider_unavailable", "provider offline")])
    )
    response = build(processor).post(
        "/v1/submissions",
        headers=_headers(),
        json={"text": "retain me for recovery"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending_unconfirmed"
    assert body["handoff_id"]
    assert body["reconciliation_url"] == f"/v1/cases/{body['handoff_id']}"
    assert "outcome" not in body
    assert "audit_id" not in body
    with sqlite3.connect(config.database_path) as conn:
        row = conn.execute(
            "SELECT state, attempt_count FROM intake_reservations WHERE handoff_id = ?",
            (body["handoff_id"],),
        ).fetchone()
    assert row == ("pending", 1)


def test_pending_replay_probes_once_and_recovers_confirmed_result(
    client_factory: tuple[Callable[[FakeProcessor], TestClient], ApiConfig],
) -> None:
    """REQ-FUN-001/REQ-QUA-002: replay probes one pending handoff and returns 200."""

    build, _ = client_factory
    processor = FakeProcessor(
        deque(
            [
                ProcessingUnavailable("provider_unavailable", "temporary"),
                _committed_result(),
            ]
        )
    )
    client = build(processor)

    pending = client.post(
        "/v1/submissions", headers=_headers(), json={"text": "recoverable"}
    )
    recovered = client.post(
        "/v1/submissions", headers=_headers(), json={"text": "recoverable"}
    )

    assert pending.status_code == 202
    assert recovered.status_code == 200
    assert recovered.json()["audit_id"] == "audit-1"
    assert len(processor.calls) == 2
    assert processor.calls[0][0] == processor.calls[1][0]


def test_definitive_processing_failure_is_503_not_false_success(
    client_factory: tuple[Callable[[FakeProcessor], TestClient], ApiConfig],
) -> None:
    """REQ-FUN-001/REQ-INV-004: definitive failure returns 503 without success fields."""

    build, _ = client_factory
    processor = FakeProcessor(
        deque(
            [
                ProcessingResult(
                    status="failed",
                    case_id=None,
                    case_revision=None,
                    decision_id=None,
                    audit_id=None,
                    outcome=None,
                    message="policy persistence failed",
                )
            ]
        )
    )
    response = build(processor).post(
        "/v1/submissions", headers=_headers(), json={"text": "cannot commit"}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "policy persistence failed"}
    assert "audit_id" not in response.json()
    assert "outcome" not in response.json()


def test_intake_persistence_failure_is_503_before_processing(
    client_factory: tuple[Callable[[FakeProcessor], TestClient], ApiConfig],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-FUN-001/REQ-INV-004: an intake write failure is 503 with no model call."""

    build, _ = client_factory
    processor = FakeProcessor(deque([_committed_result()]))

    def fail_create(*args: object, **kwargs: object) -> object:
        raise sqlite3.OperationalError("injected intake failure")

    monkeypatch.setattr(IntakeRepository, "create_intent", fail_create)
    response = build(processor).post(
        "/v1/submissions", headers=_headers(), json={"text": "write must fail"}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "intake persistence unavailable"}
    assert processor.calls == []


def _pending_intent(
    repository: IntakeRepository,
    idempotency_key: str,
    text: str,
) -> IntakeIntent:
    intent, created = repository.create_intent(
        actor_id=ACTOR_ID,
        idempotency_key=idempotency_key,
        payload_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        content_text=text,
        effective_flags={},
    )
    assert created
    return intent


def _set_lease(config: ApiConfig, handoff_id: str, lease_until: str) -> None:
    with sqlite3.connect(config.database_path) as conn:
        conn.execute(
            "UPDATE intake_reservations SET lease_until = ?, state = 'processing' "
            "WHERE handoff_id = ?",
            (lease_until, handoff_id),
        )


def test_expired_pending_intent_is_recovered_once_without_duplicate_effect(
    tmp_path: Path,
) -> None:
    """REQ-FUN-001/REQ-INV-002/REQ-QUA-002: only expired leases are recovered, once."""

    config = _config(tmp_path)
    repository = IntakeRepository(config.database_path)
    expired = _pending_intent(repository, "idem-expired", "expired text")
    active = _pending_intent(repository, "idem-active", "active text")
    _set_lease(
        config, expired.handoff_id, (datetime.now(UTC) - timedelta(seconds=60)).isoformat()
    )
    _set_lease(
        config, active.handoff_id, (datetime.now(UTC) + timedelta(seconds=60)).isoformat()
    )

    discoverable = repository.list_recoverable_pending(before=datetime.now(UTC), limit=10)

    assert [item.handoff_id for item in discoverable] == [expired.handoff_id]
    processor = FakeProcessor(deque([_committed_result()]))
    result = recover_pending(
        expired, repository=repository, processor=processor, config=config
    )

    assert result is not None
    assert result.status == "committed"
    assert processor.calls == [
        (expired.handoff_id, ACTOR_ID, "expired text", {})
    ]
    assert repository.list_recoverable_pending(before=datetime.now(UTC), limit=10) == ()
    stored = repository.get_intent(expired.handoff_id)
    assert stored is not None and stored.result == result
    assert repository.get_intent(active.handoff_id) == active


def test_active_lease_is_not_recovered(tmp_path: Path) -> None:
    """REQ-QUA-002/REQ-INV-002 negative: an active lease cannot be reprocessed."""

    config = _config(tmp_path)
    repository = IntakeRepository(config.database_path)
    active = _pending_intent(repository, "idem-active", "active text")
    _set_lease(
        config, active.handoff_id, (datetime.now(UTC) + timedelta(seconds=60)).isoformat()
    )
    processor = FakeProcessor(deque([_committed_result()]))

    assert repository.list_recoverable_pending(before=datetime.now(UTC), limit=10) == ()
    assert (
        recover_pending(active, repository=repository, processor=processor, config=config)
        is None
    )
    assert processor.calls == []
    with sqlite3.connect(config.database_path) as conn:
        row = conn.execute(
            "SELECT state, attempt_count FROM intake_reservations WHERE handoff_id = ?",
            (active.handoff_id,),
        ).fetchone()
    assert row == ("processing", 0)


def test_transient_recovery_failure_keeps_intent_recoverable(tmp_path: Path) -> None:
    """REQ-INV-002: transient recovery failure leaves intent pending, never successful."""

    config = _config(tmp_path)
    repository = IntakeRepository(config.database_path)
    intent = _pending_intent(repository, "idem-transient", "retry me")
    _set_lease(
        config, intent.handoff_id, (datetime.now(UTC) - timedelta(seconds=60)).isoformat()
    )
    processor = FakeProcessor(
        deque([ProcessingUnavailable("provider_unavailable", "still offline")])
    )

    assert (
        recover_pending(intent, repository=repository, processor=processor, config=config)
        is None
    )
    stored = repository.get_intent(intent.handoff_id)
    assert stored is not None and stored.state == "pending" and stored.result is None
    assert [
        item.handoff_id
        for item in repository.list_recoverable_pending(
            before=datetime.now(UTC), limit=10
        )
    ] == [intent.handoff_id]
