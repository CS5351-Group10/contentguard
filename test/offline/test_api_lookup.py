"""S2 case and audit lookup tests (ADR-001; REQ-FUN-001, REQ-SEC-004).

The lookup boundary exposes immutable historical policy references only to the
submission owner or a moderator holding an explicit case grant.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

import pytest
from fastapi.testclient import TestClient

from contentguard.api.app import create_app
from contentguard.api.config import ActorConfig, ApiConfig
from contentguard.api.schemas import AuditView, CaseView, ProcessingResult
from contentguard.api.storage import IntakeRepository, StorageUnavailable

OWNER_TOKEN = "owner-token"
OUTSIDER_TOKEN = "outsider-token"
GRANTED_MODERATOR_TOKEN = "granted-moderator-token"
UNGRANTED_MODERATOR_TOKEN = "ungranted-moderator-token"


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _config(tmp_path: Path) -> ApiConfig:
    return ApiConfig(
        database_path=tmp_path / "lookup.sqlite3",
        api_tokens={
            _digest(OWNER_TOKEN): ActorConfig(
                actor_id="owner-1",
                actor_type="submitter",
                scopes=frozenset({"case:read-own", "audit:read-own"}),
            ),
            _digest(OUTSIDER_TOKEN): ActorConfig(
                actor_id="outsider-1",
                actor_type="submitter",
                scopes=frozenset({"case:read-own", "audit:read-own"}),
            ),
            _digest(GRANTED_MODERATOR_TOKEN): ActorConfig(
                actor_id="moderator-1",
                actor_type="moderator",
                scopes=frozenset({"case:read-granted", "audit:read-granted"}),
            ),
            _digest(UNGRANTED_MODERATOR_TOKEN): ActorConfig(
                actor_id="moderator-2",
                actor_type="moderator",
                scopes=frozenset({"case:read-granted", "audit:read-granted"}),
            ),
        },
        intake_max_bytes=16_384,
        lease_seconds=30,
        recovery_interval_seconds=5,
        max_attempts=5,
        start_recovery_worker=False,
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _case() -> CaseView:
    return CaseView(
        case_id="case-1",
        owner_id="owner-1",
        revision=3,
        status="held",
        content_hash="a" * 64,
        policy_snapshot_id="policy-v1",
        policy_snapshot_digest="b" * 64,
        audit_id="audit-1",
    )


def _audit() -> AuditView:
    return AuditView(
        audit_id="audit-1",
        decision_id="decision-1",
        case_id="case-1",
        case_revision=3,
        owner_id="owner-1",
        outcome="hold",
        policy_reason_id="RULE-REVIEW",
        policy_snapshot_id="policy-v1",
        policy_snapshot_digest="b" * 64,
    )


@dataclass
class FakeLookupRepository:
    """Read-only lookup port fake with explicit case-scoped grants."""

    cases: dict[str, CaseView] = field(
        default_factory=lambda: {"case-1": _case()}
    )
    audits: dict[str, AuditView] = field(
        default_factory=lambda: {"audit-1": _audit()}
    )
    grants: set[tuple[str, str]] = field(
        default_factory=lambda: {("case-1", "moderator-1")}
    )
    active_policy_snapshot_id: str = "policy-v2"

    def get_case(self, case_id: str) -> CaseView | None:
        return self.cases.get(case_id)

    def get_audit(self, audit_id: str) -> AuditView | None:
        return self.audits.get(audit_id)

    def has_case_grant(self, case_id: str, actor_id: str) -> bool:
        return (case_id, actor_id) in self.grants


class UnusedProcessor:
    """Lookup requests must never enter the moderation processor."""

    def process(self, **kwargs: object) -> object:
        raise AssertionError("lookup must not call the moderation processor")


def _client(tmp_path: Path, repository: FakeLookupRepository) -> TestClient:
    return TestClient(
        create_app(
            config=_config(tmp_path),
            processor=UnusedProcessor(),
            lookup_repository=repository,
        )
    )


def test_owner_can_read_known_case_and_resolvable_audit(tmp_path: Path) -> None:
    """REQ-FUN-001/REQ-SEC-004: owner receives its case and audit evidence."""

    repository = FakeLookupRepository()
    with _client(tmp_path, repository) as client:
        case_response = client.get("/v1/cases/case-1", headers=_auth(OWNER_TOKEN))
        audit_response = client.get("/v1/audits/audit-1", headers=_auth(OWNER_TOKEN))

    assert case_response.status_code == 200
    assert case_response.json() == {
        "case_id": "case-1",
        "revision": 3,
        "status": "held",
        "content_hash": "a" * 64,
        "policy_snapshot_id": "policy-v1",
        "policy_snapshot_digest": "b" * 64,
        "audit_id": "audit-1",
    }
    assert audit_response.status_code == 200
    assert audit_response.json() == {
        "audit_id": "audit-1",
        "decision_id": "decision-1",
        "case_id": "case-1",
        "case_revision": 3,
        "outcome": "hold",
        "policy_reason_id": "RULE-REVIEW",
        "policy_snapshot_id": "policy-v1",
        "policy_snapshot_digest": "b" * 64,
    }


def test_case_granted_moderator_can_read_case_and_audit(tmp_path: Path) -> None:
    """REQ-SEC-004: a moderator grant is scoped to the referenced case."""

    repository = FakeLookupRepository()
    with _client(tmp_path, repository) as client:
        case_response = client.get(
            "/v1/cases/case-1", headers=_auth(GRANTED_MODERATOR_TOKEN)
        )
        audit_response = client.get(
            "/v1/audits/audit-1", headers=_auth(GRANTED_MODERATOR_TOKEN)
        )

    assert case_response.status_code == 200
    assert audit_response.status_code == 200


def test_unrelated_submitter_and_ungranted_moderator_are_forbidden(
    tmp_path: Path,
) -> None:
    """REQ-SEC-004 negative: unrelated actors receive 403 and no evidence."""

    repository = FakeLookupRepository()
    with _client(tmp_path, repository) as client:
        responses = [
            client.get("/v1/cases/case-1", headers=_auth(OUTSIDER_TOKEN)),
            client.get("/v1/audits/audit-1", headers=_auth(OUTSIDER_TOKEN)),
            client.get(
                "/v1/cases/case-1", headers=_auth(UNGRANTED_MODERATOR_TOKEN)
            ),
            client.get(
                "/v1/audits/audit-1", headers=_auth(UNGRANTED_MODERATOR_TOKEN)
            ),
        ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]
    assert all(response.json() == {"detail": "forbidden"} for response in responses)


def test_unknown_case_and_audit_are_404_for_authenticated_actor(tmp_path: Path) -> None:
    """REQ-FUN-001: an authenticated lookup of unknown evidence returns 404."""

    repository = FakeLookupRepository()
    with _client(tmp_path, repository) as client:
        case_response = client.get("/v1/cases/missing", headers=_auth(OWNER_TOKEN))
        audit_response = client.get("/v1/audits/missing", headers=_auth(OWNER_TOKEN))

    assert case_response.status_code == 404
    assert case_response.json() == {"detail": "case not found"}
    assert audit_response.status_code == 404
    assert audit_response.json() == {"detail": "audit not found"}


def test_historical_policy_references_do_not_follow_active_policy(tmp_path: Path) -> None:
    """REQ-FUN-004/REQ-SEC-004: lookups preserve immutable policy attribution."""

    repository = FakeLookupRepository(active_policy_snapshot_id="policy-v2")
    with _client(tmp_path, repository) as client:
        case_body = client.get(
            "/v1/cases/case-1", headers=_auth(OWNER_TOKEN)
        ).json()
        audit_body = client.get(
            "/v1/audits/audit-1", headers=_auth(OWNER_TOKEN)
        ).json()

    assert case_body["policy_snapshot_id"] == "policy-v1"
    assert audit_body["policy_snapshot_id"] == "policy-v1"
    assert case_body["policy_snapshot_digest"] == "b" * 64
    assert audit_body["policy_snapshot_digest"] == "b" * 64


# --- truthful projection of failures and terminal intake state (REQ-FUN-001,
# --- REQ-INV-004): a broken query is never a 404, a terminal result is never 202.


def test_storage_query_failure_is_503_not_404(tmp_path: Path) -> None:
    """REQ-FUN-001/REQ-INV-004: a durable-state query failure reports unavailable —
    it must not fabricate a legitimate-absence (404) claim."""

    @dataclass
    class FailingLookupRepository(FakeLookupRepository):
        def get_case(self, case_id: str) -> CaseView | None:
            raise StorageUnavailable("case query failed: disk I/O error")

        def get_audit(self, audit_id: str) -> AuditView | None:
            raise StorageUnavailable("audit query failed: disk I/O error")

    repository = FailingLookupRepository()
    with _client(tmp_path, repository) as client:
        case_response = client.get("/v1/cases/case-1", headers=_auth(OWNER_TOKEN))
        audit_response = client.get("/v1/audits/audit-1", headers=_auth(OWNER_TOKEN))

    assert case_response.status_code == 503
    assert case_response.json() == {"detail": "storage unavailable"}
    assert audit_response.status_code == 503
    assert audit_response.json() == {"detail": "storage unavailable"}


def test_real_storage_query_failure_is_typed_and_missing_domain_is_absent(
    tmp_path: Path,
) -> None:
    """REQ-FUN-001/REQ-INV-004, storage layer: a genuine operational failure raises
    the typed unavailable error, while an intake-only deployment (no policy tables)
    stays a legitimate absence."""

    class _FailingConnection:
        def execute(self, *args: object, **kwargs: object) -> object:
            raise sqlite3.OperationalError("disk I/O error")

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    class _FailingConnectRepository(IntakeRepository):
        def __init__(self, database_path: Path) -> None:
            # Parent __init__ creates the schema through connect(); this fake has no
            # backing database, so only set up the path state.
            self.database_path = Path(database_path)
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

        def connect(self) -> _FailingConnection:  # type: ignore[override]
            return _FailingConnection()

    repository = _FailingConnectRepository(tmp_path / "truthful.sqlite3")
    with pytest.raises(StorageUnavailable):
        repository.get_case("case-1")
    with pytest.raises(StorageUnavailable):
        repository.get_audit("audit-1")
    with pytest.raises(StorageUnavailable):
        repository.list_open_queue()

    # An intake-only store has no policy tables: legitimate absence, not failure.
    fresh = IntakeRepository(tmp_path / "intake-only.sqlite3")
    assert fresh.get_case("case-1") is None
    assert fresh.get_audit("audit-1") is None
    assert fresh.list_open_queue() == ()


def _seed_terminal_intent(
    tmp_path: Path, result: ProcessingResult
) -> tuple[IntakeRepository, str]:
    repository = IntakeRepository(tmp_path / "lookup.sqlite3")
    intent, created = repository.create_intent(
        actor_id="owner-1",
        idempotency_key="terminal-idem",
        payload_hash="a" * 64,
        content_text="please review this text",
        effective_flags={"analysis.reconsideration_enabled": False},
    )
    assert created
    repository.save_result(intent.handoff_id, result)
    return repository, intent.handoff_id


def _terminal_client(tmp_path: Path, repository: IntakeRepository) -> TestClient:
    return TestClient(
        create_app(
            config=_config(tmp_path),
            processor=UnusedProcessor(),
            lookup_repository=repository,
        )
    )


def test_terminal_failed_intake_is_503_never_202_pending(tmp_path: Path) -> None:
    """REQ-FUN-001/REQ-INV-004/REQ-QUA-002: a durable terminal failed result is
    reported as a terminal failure — never projected as pending success."""

    failed = ProcessingResult(
        status="failed",
        case_id=None,
        case_revision=None,
        decision_id="decision-failed",
        audit_id=None,
        outcome=None,
        message="processing failed terminally",
    )
    repository, handoff_id = _seed_terminal_intent(tmp_path, failed)
    with _terminal_client(tmp_path, repository) as client:
        response = client.get(
            f"/v1/cases/{handoff_id}", headers=_auth(OWNER_TOKEN)
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "processing failed terminally"}


def test_terminal_conflict_intake_is_409_never_202_pending(tmp_path: Path) -> None:
    """REQ-FUN-001/REQ-INV-004/REQ-QUA-002: a durable terminal conflict result is
    reported as a conflict — never projected as pending success."""

    conflict = ProcessingResult(
        status="conflict",
        case_id="case-conflict",
        case_revision=None,
        decision_id="decision-conflict",
        audit_id=None,
        outcome=None,
        message="replay key reused with a different payload",
    )
    repository, handoff_id = _seed_terminal_intent(tmp_path, conflict)
    with _terminal_client(tmp_path, repository) as client:
        response = client.get(
            f"/v1/cases/{handoff_id}", headers=_auth(OWNER_TOKEN)
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "replay key reused with a different payload"}


def test_pending_intake_without_result_stays_202(tmp_path: Path) -> None:
    """REQ-FUN-001: an intent with no durable result is still truthfully pending."""

    repository = IntakeRepository(tmp_path / "lookup.sqlite3")
    intent, _created = repository.create_intent(
        actor_id="owner-1",
        idempotency_key="pending-idem",
        payload_hash="b" * 64,
        content_text="please review this text",
        effective_flags={"analysis.reconsideration_enabled": False},
    )
    with _terminal_client(tmp_path, repository) as client:
        response = client.get(
            f"/v1/cases/{intent.handoff_id}", headers=_auth(OWNER_TOKEN)
        )

    assert response.status_code == 202
    assert response.json()["status"] == "pending_unconfirmed"
