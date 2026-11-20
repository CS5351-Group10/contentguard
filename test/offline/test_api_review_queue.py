"""S2 review-queue API tests (ADR-001; REQ-FUN-003, REQ-INV-003).

Review requests are authenticated evidence, not enforcement authority.  Every
transition remains mediated by the policy boundary and current case revision.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from fastapi.testclient import TestClient

from contentguard.api.app import create_app
from contentguard.api.config import ActorConfig, ApiConfig
from contentguard.api.errors import MandatoryRuleViolation
from contentguard.api.models import CaseView, ProcessingResult, QueueView


GRANTED_MODERATOR_TOKEN = "granted-reviewer-token"
UNGRANTED_MODERATOR_TOKEN = "ungranted-reviewer-token"
SUBMITTER_TOKEN = "submitter-token"


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _config(tmp_path: Path) -> ApiConfig:
    return ApiConfig(
        database_path=tmp_path / "review.sqlite3",
        api_tokens={
            _digest(GRANTED_MODERATOR_TOKEN): ActorConfig(
                actor_id="moderator-1",
                actor_type="moderator",
                scopes=frozenset({"review-queue:read", "review:create"}),
            ),
            _digest(UNGRANTED_MODERATOR_TOKEN): ActorConfig(
                actor_id="moderator-2",
                actor_type="moderator",
                scopes=frozenset({"review-queue:read", "review:create"}),
            ),
            _digest(SUBMITTER_TOKEN): ActorConfig(
                actor_id="submitter-1",
                actor_type="submitter",
                scopes=frozenset({"case:read-own"}),
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


def _case(*, revision: int = 4) -> CaseView:
    return CaseView(
        case_id="case-high",
        owner_id="submitter-1",
        revision=revision,
        status="escalated",
        content_hash="c" * 64,
        policy_snapshot_id="policy-v1",
        policy_snapshot_digest="d" * 64,
        audit_id="audit-escalation",
    )


def _queue_item() -> QueueView:
    return QueueView(
        case_id="case-high",
        case_revision=4,
        outcome="escalate",
        reason_id="RULE-HIGH-SEVERITY",
        severity="high",
        enqueued_at="2026-11-20T01:00:00+00:00",
    )


@dataclass
class FakeReviewRepository:
    """Read-only case/queue/grant port used by the API boundary."""

    cases: dict[str, CaseView] = field(
        default_factory=lambda: {"case-high": _case()}
    )
    queue: tuple[QueueView, ...] = field(default_factory=lambda: (_queue_item(),))
    grants: set[tuple[str, str]] = field(
        default_factory=lambda: {("case-high", "moderator-1")}
    )

    def get_case(self, case_id: str) -> CaseView | None:
        return self.cases.get(case_id)

    def list_open_queue(self) -> tuple[QueueView, ...]:
        return self.queue

    def has_case_grant(self, case_id: str, actor_id: str) -> bool:
        return (case_id, actor_id) in self.grants


@dataclass
class FakeReviewPolicy:
    """Policy-boundary fake; the API may request but never decide a transition."""

    result: ProcessingResult | Exception
    calls: list[dict[str, object]] = field(default_factory=list)

    def review_and_commit(self, **kwargs: object) -> ProcessingResult:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class UnusedProcessor:
    """Review requests must not enter the initial submission processor."""

    def process(self, **kwargs: object) -> object:
        raise AssertionError("review route must not call the submission processor")


def _committed_review() -> ProcessingResult:
    return ProcessingResult(
        status="committed",
        case_id="case-high",
        case_revision=5,
        decision_id="decision-review-1",
        audit_id="audit-review-1",
        outcome="approve",
        message="committed",
    )


def _client(
    tmp_path: Path,
    repository: FakeReviewRepository,
    policy: FakeReviewPolicy,
) -> TestClient:
    return TestClient(
        create_app(
            config=_config(tmp_path),
            processor=UnusedProcessor(),
            lookup_repository=repository,
            review_repository=repository,
            review_policy=policy,
        )
    )


def _review_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "expected_revision": 4,
        "requested_outcome": "approve",
        "rationale": "Reviewed the current evidence and policy snapshot.",
    }
    payload.update(overrides)
    return payload


def test_granted_moderator_lists_only_granted_high_severity_case(
    tmp_path: Path,
) -> None:
    """REQ-FUN-003/REQ-INV-003: high severity remains visible to its granted reviewer."""

    repository = FakeReviewRepository()
    policy = FakeReviewPolicy(_committed_review())
    with _client(tmp_path, repository, policy) as client:
        response = client.get(
            "/v1/review-queue", headers=_auth(GRANTED_MODERATOR_TOKEN)
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "case_id": "case-high",
            "case_revision": 4,
            "outcome": "escalate",
            "reason_id": "RULE-HIGH-SEVERITY",
            "severity": "high",
            "enqueued_at": "2026-11-20T01:00:00+00:00",
        }
    ]
    assert policy.calls == []


def test_submitter_and_ungranted_moderator_cannot_read_queue(tmp_path: Path) -> None:
    """REQ-FUN-003/REQ-SEC-003 negative: unauthorized queue reads return 403."""

    repository = FakeReviewRepository()
    policy = FakeReviewPolicy(_committed_review())
    with _client(tmp_path, repository, policy) as client:
        submitter = client.get(
            "/v1/review-queue", headers=_auth(SUBMITTER_TOKEN)
        )
        ungranted = client.get(
            "/v1/review-queue", headers=_auth(UNGRANTED_MODERATOR_TOKEN)
        )

    assert submitter.status_code == 403
    assert ungranted.status_code == 200
    assert ungranted.json() == []
    assert policy.calls == []


def test_authorized_review_commits_through_policy_boundary(tmp_path: Path) -> None:
    """REQ-FUN-003/REQ-INV-003: one current authorized review may commit via policy."""

    repository = FakeReviewRepository()
    policy = FakeReviewPolicy(_committed_review())
    with _client(tmp_path, repository, policy) as client:
        response = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(),
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "committed",
        "case_id": "case-high",
        "case_revision": 5,
        "decision_id": "decision-review-1",
        "audit_id": "audit-review-1",
        "outcome": "approve",
    }
    assert len(policy.calls) == 1
    assert policy.calls[0]["reviewer_id"] == "moderator-1"
    assert policy.calls[0]["case"] == _case()
    assert policy.calls[0]["expected_revision"] == 4
    assert policy.calls[0]["requested_outcome"] == "approve"


def test_unauthorized_or_forged_review_has_no_policy_effect(tmp_path: Path) -> None:
    """REQ-SEC-003 negative: grants and server identity defeat forged review claims."""

    repository = FakeReviewRepository()
    policy = FakeReviewPolicy(_committed_review())
    with _client(tmp_path, repository, policy) as client:
        unauthorized = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(UNGRANTED_MODERATOR_TOKEN),
            json=_review_payload(),
        )
        forged = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(reviewer_id="moderator-2", role="admin"),
        )

    assert unauthorized.status_code == 403
    assert unauthorized.json() == {"detail": "forbidden"}
    assert forged.status_code == 422
    assert policy.calls == []


def test_stale_review_revision_is_409_before_policy_call(tmp_path: Path) -> None:
    """REQ-FUN-003/REQ-INV-003 negative: stale review evidence cannot authorize action."""

    repository = FakeReviewRepository()
    policy = FakeReviewPolicy(_committed_review())
    with _client(tmp_path, repository, policy) as client:
        response = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(expected_revision=3),
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "stale case revision"}
    assert policy.calls == []


def test_mandatory_rule_violation_is_422_without_final_effect(tmp_path: Path) -> None:
    """REQ-FUN-003/REQ-INV-003 negative: human review cannot waive a mandatory rule."""

    repository = FakeReviewRepository()
    policy = FakeReviewPolicy(
        MandatoryRuleViolation("requested outcome violates mandatory policy rule")
    )
    with _client(tmp_path, repository, policy) as client:
        response = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(),
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "requested outcome violates mandatory policy rule"
    }
    assert len(policy.calls) == 1


def test_high_severity_case_has_no_final_effect_before_valid_review(
    tmp_path: Path,
) -> None:
    """REQ-INV-003 negative: listing an escalated case never finalizes it."""

    repository = FakeReviewRepository()
    policy = FakeReviewPolicy(_committed_review())
    with _client(tmp_path, repository, policy) as client:
        listed = client.get(
            "/v1/review-queue", headers=_auth(GRANTED_MODERATOR_TOKEN)
        )

    assert listed.status_code == 200
    assert listed.json()[0]["outcome"] == "escalate"
    assert repository.get_case("case-high") == _case()
    assert repository.get_case("case-high").status == "escalated"  # type: ignore[union-attr]
    assert policy.calls == []
