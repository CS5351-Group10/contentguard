"""S2 review-queue API tests (ADR-001; REQ-FUN-003, REQ-INV-003).

Review requests are authenticated evidence, not enforcement authority.  Every
transition remains mediated by the policy boundary and current case revision.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from fastapi.testclient import TestClient

from contentguard.analysis.contracts import AdvisoryResult
from contentguard.api.adapter import PolicyAdapter
from contentguard.api.app import create_app
from contentguard.api.config import ActorConfig, ApiConfig
from contentguard.api.errors import MandatoryRuleViolation
from contentguard.api.schemas import CaseView, ProcessingResult, QueueView
from contentguard.api.storage import StorageUnavailable
from contentguard.escalation.contracts import QueueEntry
from contentguard.escalation.repository import QueueRepository
from contentguard.policy.engine import PolicyEngine
from contentguard.policy.snapshot import PolicySnapshot
from contentguard.policy.store import SqliteStore

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
    policy: FakeReviewPolicy | PolicyAdapter,
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


def test_stale_review_revision_conflicts_through_policy(
    tmp_path: Path,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> None:
    """REQ-FUN-003/REQ-INV-003 negative: a genuinely stale non-replay request is
    rejected by the policy-owned currency check as a CONFLICT (409) — the route
    delegates replay/staleness ordering to the engine instead of preempting it,
    and the refusal writes nothing."""

    snap = snapshot_with_reject_rule
    client, store, _repository = _real_policy_client(tmp_path, snap, advisory_medium)
    with client:
        before_counts = _store_counts(store)
        response = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(expected_revision=3),
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "case revision/snapshot/hash mismatch"}
    assert _store_counts(store) == before_counts  # the engine refuses without writing


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


# --- real policy engine + store: the ADR-002 acceptance-matrix HTTP leg ----------------


def _seed_escalated_case(store: SqliteStore, snapshot: PolicySnapshot) -> None:
    """Seed a reviewable escalated case row (pinned medium-severity evidence) and an
    open escalation queue entry in a real store."""
    with store.transaction() as conn:
        store.activate_snapshot(conn, snapshot)
        conn.execute(
            """
            INSERT INTO cases (
                case_id, revision, status, content_hash, policy_snapshot_id,
                policy_snapshot_digest, content_text, advisory_verdict,
                advisory_severity, advisory_model_id, advisory_model_version,
                analysis_failure_code, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "case-high",
                4,
                "escalated",
                "c" * 64,
                snapshot.snapshot_id,
                snapshot.digest,
                "seeded content",
                "violate",
                "medium",
                "model-x",
                "2026-11",
                None,
                "2026-11-22T00:00:00+00:00",
            ),
        )
        QueueRepository.enqueue(
            conn,
            QueueEntry(
                case_id="case-high",
                case_revision=4,
                outcome="escalate",
                reason_id="RULE-HIGH-SEVERITY",
                enqueued_at="2026-11-22T00:00:00+00:00",
            ),
        )


def _real_case_view(snapshot: PolicySnapshot) -> CaseView:
    """The API projection of the seeded real row, including its content text."""
    return CaseView(
        case_id="case-high",
        owner_id="submitter-1",
        revision=4,
        status="escalated",
        content_hash="c" * 64,
        policy_snapshot_id=snapshot.snapshot_id,
        policy_snapshot_digest=snapshot.digest,
        audit_id="audit-escalation",
        content_text="seeded content",
    )


def _store_counts(store: SqliteStore) -> tuple[int, int, int]:
    """Return (audit row count, open queue depth, replay record count)."""
    with store.read_connection() as conn:
        audit = conn.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0]
        queue = QueueRepository.count(conn)
        replay = conn.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
    return int(audit), int(queue), int(replay)


def _real_policy_client(
    tmp_path: Path,
    snapshot: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> tuple[TestClient, SqliteStore, FakeReviewRepository]:
    """Wire the API to a real PolicyEngine over a real store (repository stays the
    API-owned projection fake: engine + store are the safety-critical pair)."""
    store = SqliteStore(f"{tmp_path}/policy.db")
    store.initialize()
    _seed_escalated_case(store, snapshot)
    repository = FakeReviewRepository(cases={"case-high": _real_case_view(snapshot)})
    adapter = PolicyAdapter(engine=PolicyEngine(snapshot), store=store)
    return _client(tmp_path, repository, adapter), store, repository


def test_real_engine_approve_against_reject_floor_is_422_with_zero_writes(
    tmp_path: Path,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> None:
    """Acceptance matrix group 1, HTTP leg (ADR-002): a real engine + store behind the
    API port refuses a requested APPROVE that the mandatory REJECT floor would
    override — 422 with zero writes: no case revision bump, no queue change, no audit
    row, no replay record."""
    snap = snapshot_with_reject_rule
    client, store, _repository = _real_policy_client(tmp_path, snap, advisory_medium)
    with client:
        before_counts = _store_counts(store)
        response = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(),
        )

    assert response.status_code == 422
    assert "mandatory rule" in response.json()["detail"]
    assert _store_counts(store) == before_counts
    with store.read_connection() as conn:
        row = conn.execute(
            "SELECT revision, status FROM cases WHERE case_id = ?", ("case-high",)
        ).fetchone()
    assert row is not None
    assert (int(row[0]), str(row[1])) == (4, "escalated")


def _refresh_projection(
    repository: FakeReviewRepository, store: SqliteStore
) -> None:
    """Rebuild the API projection from the real store row — the current revision and
    status a database-backed repository would actually serve after a commit."""
    with store.read_connection() as conn:
        row = conn.execute(
            "SELECT revision, status, content_hash, policy_snapshot_id, "
            "policy_snapshot_digest, content_text FROM cases WHERE case_id = ?",
            ("case-high",),
        ).fetchone()
    assert row is not None
    repository.cases["case-high"] = CaseView(
        case_id="case-high",
        owner_id="submitter-1",
        revision=int(row[0]),
        status=str(row[1]),
        content_hash=str(row[2]),
        policy_snapshot_id=str(row[3]),
        policy_snapshot_digest=str(row[4]),
        audit_id="audit-escalation",
        content_text=None if row[5] is None else str(row[5]),
    )


def test_real_engine_permitted_reject_commits_replays_and_conflicts_via_http(
    tmp_path: Path,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> None:
    """Acceptance matrix group 1, HTTP leg (ADR-002): a permitted requested REJECT
    commits exactly once through the API port; a same-key same-request retry
    (expected_revision pinned to the pre-commit revision, against a repository
    projection refreshed to the CURRENT stored row) reconciles the stored result; a
    same-key retry that changes only the rationale is a 409 CONFLICT (the
    review-request identity gate) — all with a real engine and store, and the replay
    row persists the review-request identity."""
    snap = snapshot_with_reject_rule
    client, store, repository = _real_policy_client(tmp_path, snap, advisory_medium)
    with client:
        first = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(requested_outcome="reject"),
        )
        assert first.status_code == 200
        assert first.json()["status"] == "committed"
        assert first.json()["outcome"] == "reject"
        assert first.json()["audit_id"] is not None
        counts_after_first = _store_counts(store)
        assert counts_after_first == (1, 0, 1)  # audit appended, queue resolved, replay row

        # A database-backed projection now serves the post-commit row (revision 5,
        # status rejected) — the retry's expected_revision stays at 4, so this leg
        # exercises the replay-before-staleness ordering end to end.
        _refresh_projection(repository, store)

        retry = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(requested_outcome="reject"),
        )
        assert retry.status_code == 200
        assert retry.json()["decision_id"] == first.json()["decision_id"]
        assert retry.json()["audit_id"] == first.json()["audit_id"]
        assert _store_counts(store) == counts_after_first  # reconciled, no new writes

        edited = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(
                requested_outcome="reject",
                rationale="a different moderator rationale",
            ),
        )
        assert edited.status_code == 409
        assert edited.json() == {"detail": "replay key reused with a different payload"}
        assert _store_counts(store) == counts_after_first

    with store.read_connection() as conn:
        row = conn.execute(
            "SELECT revision, status FROM cases WHERE case_id = ?", ("case-high",)
        ).fetchone()
        replay = conn.execute(
            "SELECT review_request_hash FROM commits WHERE replay_key = ?",
            ("review:case-high:4",),
        ).fetchone()
    assert row is not None
    assert (int(row[0]), str(row[1])) == (5, "rejected")
    assert replay is not None
    assert replay[0] is not None  # the review-request identity is persisted


def test_real_engine_current_row_replay_reconciles_and_identity_conflicts(
    tmp_path: Path,
    snapshot_with_reject_rule: PolicySnapshot,
    advisory_medium: AdvisoryResult,
) -> None:
    """Architecture re-review requirement (ADR-002 replay-before-staleness, HTTP
    leg): with the repository projection at the CURRENT stored row (post-commit
    revision 5, rejected), an identical retry whose expected_revision pins the
    pre-commit revision reconciles the stored result through the policy-owned
    replay path; a retry that changes only the rationale, or one that flips the
    requested outcome REJECT→APPROVE under the matching mandatory REJECT floor,
    conflicts via the review-request identity gate — all with no additional
    writes to case, queue, audit or replay state."""
    snap = snapshot_with_reject_rule
    client, store, repository = _real_policy_client(tmp_path, snap, advisory_medium)
    with client:
        first = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(requested_outcome="reject"),
        )
        assert first.status_code == 200
        counts_after_first = _store_counts(store)
        assert counts_after_first == (1, 0, 1)

        _refresh_projection(repository, store)

        identical = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(requested_outcome="reject"),
        )
        assert identical.status_code == 200
        assert identical.json()["status"] == "committed"
        assert identical.json()["decision_id"] == first.json()["decision_id"]
        assert identical.json()["audit_id"] == first.json()["audit_id"]
        assert _store_counts(store) == counts_after_first

        rationale_flip = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(
                requested_outcome="reject",
                rationale="a different moderator rationale",
            ),
        )
        assert rationale_flip.status_code == 409
        assert rationale_flip.json() == {
            "detail": "replay key reused with a different payload"
        }
        assert _store_counts(store) == counts_after_first

        outcome_flip = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(requested_outcome="approve"),
        )
        assert outcome_flip.status_code == 409
        assert outcome_flip.json() == {
            "detail": "replay key reused with a different payload"
        }
        assert _store_counts(store) == counts_after_first


def test_review_case_read_failure_is_503_with_zero_policy_calls(
    tmp_path: Path,
) -> None:
    """Architecture re-review requirement (REQ-FUN-001/REQ-INV-004): a query failure
    on the review route's earliest storage read (the case lookup) maps to 503 — not
    an unhandled server error — and no policy call happens."""

    @dataclass
    class FailingReadRepository(FakeReviewRepository):
        def get_case(self, case_id: str) -> CaseView | None:
            raise StorageUnavailable("case read failed: disk I/O error")

    repository = FailingReadRepository()
    policy = FakeReviewPolicy(_committed_review())
    with _client(tmp_path, repository, policy) as client:
        response = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(),
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "storage unavailable"}
    assert policy.calls == []


def test_review_queue_storage_failure_is_503_not_empty(tmp_path: Path) -> None:
    """REQ-FUN-001/REQ-INV-004: a queue query failure reports unavailable — it must
    not masquerade as a legitimate empty queue."""

    @dataclass
    class FailingQueueRepository(FakeReviewRepository):
        def list_open_queue(self) -> tuple[QueueView, ...]:
            raise StorageUnavailable("queue query failed: disk I/O error")

    repository = FailingQueueRepository()
    policy = FakeReviewPolicy(_committed_review())
    with _client(tmp_path, repository, policy) as client:
        response = client.get("/v1/review-queue", headers=_auth(GRANTED_MODERATOR_TOKEN))

    assert response.status_code == 503
    assert response.json() == {"detail": "storage unavailable"}


def test_review_grant_query_failure_is_503_never_403(tmp_path: Path) -> None:
    """REQ-FUN-003/REQ-INV-004: a grant query failure on the review route reports
    unavailable — it must not be answered with a fabricated authorization denial."""

    @dataclass
    class FailingGrantRepository(FakeReviewRepository):
        def has_case_grant(self, case_id: str, actor_id: str) -> bool:
            raise StorageUnavailable("grant query failed: disk I/O error")

    repository = FailingGrantRepository()
    policy = FakeReviewPolicy(_committed_review())
    with _client(tmp_path, repository, policy) as client:
        response = client.post(
            "/v1/cases/case-high/reviews",
            headers=_auth(GRANTED_MODERATOR_TOKEN),
            json=_review_payload(),
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "storage unavailable"}
    assert policy.calls == []  # the authorization gate precedes any policy call
