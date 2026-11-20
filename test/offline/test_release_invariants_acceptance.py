"""Release-acceptance invariant boundary tests (REQ-INV-001..REQ-INV-005).

Cross-module acceptance checks for the five zero-tolerance invariants at the public
module boundary. These are not S1/S2 unit tests: they exercise policy + escalation +
audit + the semantic-evaluation gate together and assert that forged enforcement, AI
unavailability, unreviewed high severity, failed audit commits, and invalid or
unverified replay are strictly blocked.

Deterministic and offline: no network, no provider secret, no model call.
"""

from __future__ import annotations

import importlib.util
import io
import sys
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest
from conftest import make_case

import contentguard.policy as policy_package
from contentguard.audit.repository import AuditRepository
from contentguard.escalation.repository import QueueRepository
from contentguard.policy.contracts import (
    ActorRef,
    AdvisoryResult,
    AnalysisFailure,
    CaseSnapshot,
    CaseStatus,
    CommitStatus,
    FailureCode,
    Outcome,
    PolicyDecision,
    ReplayKey,
    ReviewRequest,
    Severity,
    Verdict,
)
from contentguard.policy.enforcement import EnforcementAuthority
from contentguard.policy.engine import PolicyEngine
from contentguard.policy.errors import ForbiddenAuthorityError
from contentguard.policy.snapshot import PolicySnapshot
from contentguard.policy.store import SqliteStore

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
GATE_PATH = SCRIPTS / "check_semantic_eval.py"
CORPUS_PATH = ROOT / "test" / "eval" / "moderation_eval.jsonl"
GOOD_REPLAY = ROOT / "test" / "eval" / "replay" / "good_prompt.jsonl"
BAD_REPLAY = ROOT / "test" / "eval" / "replay" / "bad_prompt.jsonl"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_UPDATED_AT = "2026-11-18T12:00:00+00:00"
_DECIDED_AT = datetime(2026, 11, 18, 12, 0, 0, tzinfo=UTC)


def _advisory(*, verdict: Verdict, severity: Severity) -> AdvisoryResult:
    return AdvisoryResult.from_payload(
        {
            "role": "initial_review",
            "verdict": verdict.value,
            "severity": severity.value,
            "rationale": "Acceptance fixture rationale.",
            "citations": ("clause-001",),
            "prompt_version": "prompt-v1",
            "model_id": "model-x",
            "model_version": "2026-11",
            "usage": {
                "input_tokens": 120,
                "output_tokens": 40,
                "usage_unknown": False,
            },
        }
    )


@pytest.fixture()
def store(tmp_path: Path) -> SqliteStore:
    instance = SqliteStore(tmp_path / "release-invariants.db")
    instance.initialize()
    return instance


def _seed_case(
    store: SqliteStore, case: CaseSnapshot, snapshot: PolicySnapshot
) -> None:
    with store.transaction() as conn:
        store.activate_snapshot(conn, snapshot)
    with store.transaction() as conn:
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
                case.case_id,
                case.revision,
                case.status.value,
                case.content_hash,
                case.policy_snapshot_id,
                case.policy_snapshot_digest,
                "acceptance fixture content",
                case.advisory_verdict.value
                if case.advisory_verdict is not None
                else None,
                case.advisory_severity.value
                if case.advisory_severity is not None
                else None,
                case.advisory_model_id,
                case.advisory_model_version,
                case.analysis_failure_code.value
                if case.analysis_failure_code is not None
                else None,
                _UPDATED_AT,
            ),
        )


def _audit_count(store: SqliteStore) -> int:
    with store.read_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM audit_records").fetchone()
    assert row is not None
    return int(row[0])


def _case_row(store: SqliteStore, case_id: str) -> tuple[int, str]:
    with store.read_connection() as conn:
        row = conn.execute(
            "SELECT revision, status FROM cases WHERE case_id = ?", (case_id,)
        ).fetchone()
    assert row is not None
    return int(row[0]), str(row[1])


def _queue_count(store: SqliteStore) -> int:
    with store.read_connection() as conn:
        return QueueRepository.count(conn)


def _replay_count(store: SqliteStore) -> int:
    with store.read_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM commits").fetchone()
    assert row is not None
    return int(row[0])


def _read_audit(store: SqliteStore, audit_id: str):
    with store.read_connection() as conn:
        return AuditRepository.read(conn, audit_id)


def _load_gate() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_inv5_gate", GATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run_gate(
    monkeypatch: pytest.MonkeyPatch,
    gate: ModuleType,
    *,
    corpus: Path,
    replay: Path | None,
) -> int:
    monkeypatch.delenv("EVAL_REPLAY", raising=False)
    event = {
        "pull_request": {
            "number": 55,
            "body": "Test-Plan-Approved: #55",
            "base": {"repo": {"full_name": "o/r"}},
        }
    }
    monkeypatch.setattr(gate, "event_payload", lambda: event)
    monkeypatch.setattr(gate, "changed_files", lambda *a, **k: ["prompts/prompt_v1.0.yaml"])
    monkeypatch.setattr(gate, "EVAL_SET", corpus)
    monkeypatch.setattr(gate, "EVAL_REPLAY", replay)
    monkeypatch.setattr(sys, "argv", ["check_semantic_eval.py", "--strict"])
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        return gate.main()


def test_inv001_forged_enforcement_is_blocked_before_any_write(
    store: SqliteStore, snapshot_v1: PolicySnapshot
) -> None:
    """REQ-INV-001: only engine-minted decisions may enforce; forged decisions write nothing.

    Cross-module boundary: the policy package must not re-export the protected writer, an
    advisory payload cannot smuggle an enforcement action, and a directly constructed
    decision is rejected with ``ForbiddenAuthorityError`` before the transaction opens.
    """
    assert not hasattr(policy_package, "EnforcementAuthority")

    payload = {
        "role": "initial_review",
        "verdict": "allow",
        "severity": "low",
        "rationale": "forged action attempt",
        "citations": ("clause-001",),
        "prompt_version": "prompt-v1",
        "model_id": "model-x",
        "model_version": "2026-11",
        "usage": {"input_tokens": 1, "output_tokens": 1, "usage_unknown": False},
        "action": "approve",
    }
    with pytest.raises(ValueError):
        AdvisoryResult.from_payload(payload)

    case = make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.LOW))
    _seed_case(store, case, snapshot_v1)
    forged = PolicyDecision(
        decision_id="forged-decision",
        case_id=case.case_id,
        case_revision=case.revision,
        outcome=Outcome.APPROVE,
        reason_id="RULE-ALLOW-LOW",
        reason_text="Allowed by forged decision.",
        severity=Severity.LOW,
        advisory_verdict=Verdict.ALLOW,
        advisory_severity=Severity.LOW,
        advisory_model_id="model-x",
        advisory_model_version="2026-11",
        analysis_failure_code=None,
        policy_snapshot_id=case.policy_snapshot_id,
        policy_snapshot_digest=case.policy_snapshot_digest,
        content_hash=case.content_hash,
        requires_human_review=False,
        actor_ids=("policy", "ai:model-x"),
        decided_at=_DECIDED_AT,
        _authority_token=None,
    )

    with pytest.raises(ForbiddenAuthorityError):
        EnforcementAuthority(store).commit(
            forged,
            expected_revision=1,
            replay_key=ReplayKey("submitter-1", "inv1-forged"),
        )

    assert _audit_count(store) == 0
    assert _case_row(store, case.case_id) == (1, CaseStatus.ANALYZING.value)
    assert _queue_count(store) == 0


@pytest.mark.parametrize("failure_code", list(FailureCode))
@pytest.mark.parametrize(
    ("text", "expected"),
    [("benign text", Outcome.HOLD), ("dangerous threat", Outcome.ESCALATE)],
)
def test_inv002_analysis_failure_never_auto_disposes(
    snapshot_v1: PolicySnapshot,
    failure_code: FailureCode,
    text: str,
    expected: Outcome,
) -> None:
    """REQ-INV-002: every typed analysis failure holds or escalates, never auto-decides.

    External-boundary check: the policy engine is the only component that can act on an
    analysis outcome, and it must never turn ``FailureCode`` into an APPROVE or REJECT.
    """
    case = make_case(advisory=None)
    decision = PolicyEngine(snapshot_v1).evaluate(
        case=case,
        content_text=text,
        advisory=AnalysisFailure(code=failure_code, detail="injected failure"),
    )

    assert decision.outcome is expected
    assert decision.requires_human_review is True
    assert decision.outcome not in (Outcome.APPROVE, Outcome.REJECT)


@pytest.mark.parametrize("failure_code", list(FailureCode))
def test_inv002_failure_commit_reaches_a_durable_human_queue(
    store: SqliteStore, snapshot_v1: PolicySnapshot, failure_code: FailureCode
) -> None:
    """REQ-INV-002: every typed failure commits to a durable hold plus human queue entry.

    Cross-module check for policy + escalation + audit: the case is paused, the reviewer
    queue has one unresolved entry, and the audit row records the failure with no verdict.
    """
    case = make_case(advisory=None)
    _seed_case(store, case, snapshot_v1)

    result = PolicyEngine(snapshot_v1).evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=AnalysisFailure(code=failure_code, detail="injected failure"),
        expected_revision=1,
        replay_key=ReplayKey("submitter-1", f"inv2-{failure_code.value}"),
    )

    assert result.status is CommitStatus.COMMITTED
    assert result.audit_id is not None
    assert _case_row(store, case.case_id) == (2, CaseStatus.HELD.value)
    assert _queue_count(store) == 1

    record = _read_audit(store, result.audit_id)
    assert record.outcome == Outcome.HOLD.value
    assert record.ai_verdict is None
    assert record.analysis_failure_code == failure_code.value


def test_inv003_high_severity_never_finalizes_without_a_current_review(
    store: SqliteStore, snapshot_v1: PolicySnapshot
) -> None:
    """REQ-INV-003: high severity escalates and only a current moderator review finalizes.

    Cross-module check for policy + escalation + audit: the first commit is non-final, an
    unreviewed re-decision conflicts and adds no audit row, and a current moderator review
    then produces the single final disposition and resolves the queue.
    """
    case = make_case(advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.HIGH))
    _seed_case(store, case, snapshot_v1)
    engine = PolicyEngine(snapshot_v1)

    escalated = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.HIGH),
        expected_revision=1,
        replay_key=ReplayKey("submitter-1", "inv3-escalate"),
    )

    assert escalated.status is CommitStatus.COMMITTED
    assert escalated.audit_id is not None
    assert _case_row(store, case.case_id) == (2, CaseStatus.ESCALATED.value)
    assert _queue_count(store) == 1
    escalated_record = _read_audit(store, escalated.audit_id)
    assert escalated_record.outcome == Outcome.ESCALATE.value
    assert escalated_record.policy_reason_id == "RULE-HIGH-SEVERITY"

    unreviewed = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.HIGH),
        expected_revision=2,
        replay_key=ReplayKey("submitter-1", "inv3-unreviewed"),
    )

    assert unreviewed.status is CommitStatus.CONFLICT
    assert _audit_count(store) == 1
    assert _case_row(store, case.case_id) == (2, CaseStatus.ESCALATED.value)

    review = ReviewRequest(
        reviewer=ActorRef(actor_id="moderator-1", role="moderator"),
        case_id=case.case_id,
        expected_revision=2,
        requested_outcome=Outcome.REJECT,
        rationale="Confirming the escalation after human inspection.",
        policy_snapshot_id=case.policy_snapshot_id,
        policy_snapshot_digest=case.policy_snapshot_digest,
        content_hash=case.content_hash,
    )
    finalized = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=_advisory(verdict=Verdict.ALLOW, severity=Severity.HIGH),
        review=review,
        expected_revision=2,
        replay_key=ReplayKey("moderator-1", "inv3-review"),
    )

    assert finalized.status is CommitStatus.COMMITTED
    assert finalized.audit_id is not None
    assert _case_row(store, case.case_id) == (3, CaseStatus.REJECTED.value)
    assert _queue_count(store) == 0
    assert _audit_count(store) == 2

    final_record = _read_audit(store, finalized.audit_id)
    assert final_record.outcome == Outcome.REJECT.value
    assert final_record.policy_reason_id == "RULE-HUMAN-REVIEW"
    assert "reviewer:moderator-1" in final_record.actor_ids


@pytest.mark.parametrize(
    ("text", "expected_outcome"),
    [
        ("benign text", Outcome.HOLD),
        ("dangerous threat", Outcome.ESCALATE),
    ],
)
def test_inv004_late_write_failure_rolls_back_audit_case_and_queue(
    store: SqliteStore,
    snapshot_v1: PolicySnapshot,
    text: str,
    expected_outcome: Outcome,
) -> None:
    """REQ-INV-002, REQ-INV-004: a commit is atomic; no queue write survives a late failure.

    Cross-module check for policy + audit + escalation: the case update, queue insertion,
    and audit row are appended before the replay row, so aborting the replay insert proves
    the whole protected write rolls back and the caller receives FAILED with no audit id.
    """
    case = make_case(advisory=None)
    _seed_case(store, case, snapshot_v1)
    with store.transaction() as conn:
        conn.execute(
            "CREATE TRIGGER release_inv4_abort BEFORE INSERT ON commits "
            "BEGIN SELECT RAISE(ABORT, 'injected replay write failure'); END"
        )

    result = PolicyEngine(snapshot_v1).evaluate_and_commit(
        store=store,
        case=case,
        content_text=text,
        advisory=AnalysisFailure(
            code=FailureCode.INVALID_RESPONSE, detail="injected invalid response"
        ),
        expected_revision=1,
        replay_key=ReplayKey(
            "submitter-1", f"inv4-rollback-{expected_outcome.value}"
        ),
    )

    assert result.status is CommitStatus.FAILED
    assert result.audit_id is None
    assert _audit_count(store) == 0
    assert _replay_count(store) == 0
    assert _case_row(store, case.case_id) == (1, CaseStatus.ANALYZING.value)
    assert _queue_count(store) == 0


@pytest.mark.parametrize(
    ("text", "expected_status", "expected_outcome"),
    [
        ("benign text", CaseStatus.HELD, Outcome.HOLD),
        ("dangerous threat", CaseStatus.ESCALATED, Outcome.ESCALATE),
    ],
)
def test_inv004_queue_write_paths_commit_atomically(
    store: SqliteStore,
    snapshot_v1: PolicySnapshot,
    text: str,
    expected_status: CaseStatus,
    expected_outcome: Outcome,
) -> None:
    """REQ-INV-002, REQ-INV-004: hold/escalate writes reach the queue before replay.

    Successful counterpart to the rollback test: the same scenarios must commit the case
    update, one unresolved queue entry, one audit record, and one replay record.
    """
    case = make_case(advisory=None)
    _seed_case(store, case, snapshot_v1)

    result = PolicyEngine(snapshot_v1).evaluate_and_commit(
        store=store,
        case=case,
        content_text=text,
        advisory=AnalysisFailure(
            code=FailureCode.INVALID_RESPONSE, detail="injected invalid response"
        ),
        expected_revision=1,
        replay_key=ReplayKey(
            "submitter-1", f"inv4-queue-{expected_outcome.value}"
        ),
    )

    assert result.status is CommitStatus.COMMITTED
    assert result.audit_id is not None
    assert _case_row(store, case.case_id) == (2, expected_status.value)
    assert _queue_count(store) == 1
    assert _audit_count(store) == 1
    assert _replay_count(store) == 1
    record = _read_audit(store, result.audit_id)
    assert record.outcome == expected_outcome.value


def test_inv005_bad_or_unverifiable_replay_blocks_the_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-INV-005: invalid or unverified semantic replay must block a prompt/model change.

    Acceptance boundary: the real gate is driven with PR context, the shipped corpus and
    replay fixtures, plus a missing-corpus path. A safety-escaping replay and a missing
    evaluation set fail under ``--strict``; the approved replay passes.
    """
    gate = _load_gate()

    assert _run_gate(monkeypatch, gate, corpus=CORPUS_PATH, replay=BAD_REPLAY) != 0
    assert _run_gate(monkeypatch, gate, corpus=CORPUS_PATH, replay=GOOD_REPLAY) == 0
    missing_corpus = CORPUS_PATH.parent / "missing-moderation-eval.jsonl"
    assert _run_gate(monkeypatch, gate, corpus=missing_corpus, replay=GOOD_REPLAY) != 0
