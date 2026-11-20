"""S3 advisory-to-S1 policy adapter tests (ADR-001; REQ-FUN-002/004).

The adapter projects validated analysis data into immutable policy DTOs and invokes
only ``PolicyEngine.evaluate_and_commit``.  It never grants analysis enforcement
authority or manufactures success after a failed policy commit (REQ-INV-001/004).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from contentguard.analysis.contracts import (
    AdvisoryResult as AnalysisAdvisory,
    AnalysisFailure as S3Failure,
    AttemptIdentity,
    Citation,
    Usage as AnalysisUsage,
)
from contentguard.api.adapter import PolicyAdapter
from contentguard.policy.contracts import (
    AdvisoryResult as PolicyAdvisory,
    AnalysisFailure as PolicyFailure,
    CaseSnapshot,
    CaseStatus,
    CommitResult,
    CommitStatus,
    FailureCode as PolicyFailureCode,
    ReplayKey,
    Severity,
    Verdict,
)


def _attempt() -> AttemptIdentity:
    return AttemptIdentity(
        attempt_id="attempt-1",
        case_id="case-1",
        case_revision=1,
        snapshot_id="policy-v1",
        snapshot_revision=1,
        prompt_version="prompt-v1.1",
        model_id="model-demo",
        model_version="2026-11-20",
        tokenizer_id="tokenizer-demo",
        contract_version="analysis-v1",
        role="initial_review",
    )


def _s3_advisory() -> AnalysisAdvisory:
    return AnalysisAdvisory(
        attempt=_attempt(),
        verdict="review",
        severity="medium",
        rationale="The approved clause requires human review.",
        citations=(
            Citation(
                corpus_id="community-policy",
                corpus_revision=1,
                clause_id="CP-HARASS-001",
                clause_revision=1,
                clause_digest="a" * 64,
            ),
        ),
        usage=AnalysisUsage(input_tokens=120, output_tokens=30, usage_unknown=False),
        known_severity="medium",
    )


def _s3_failure(code: str = "provider_unavailable") -> S3Failure:
    return S3Failure(
        code=code,  # type: ignore[arg-type]
        detail="analysis unavailable",
        attempt=_attempt(),
        usage=AnalysisUsage(input_tokens=0, output_tokens=0, usage_unknown=True),
        known_severity=None,
    )


def _case() -> CaseSnapshot:
    return CaseSnapshot(
        case_id="case-1",
        revision=1,
        status=CaseStatus.ANALYZING,
        content_hash="b" * 64,
        policy_snapshot_id="policy-v1",
        policy_snapshot_digest="c" * 64,
    )


def _committed() -> CommitResult:
    return CommitResult(
        status=CommitStatus.COMMITTED,
        decision_id="decision-1",
        audit_id="audit-1",
        case_revision=2,
        message="committed",
    )


@dataclass
class FakePolicyEngine:
    """Records the single permitted policy entry point."""

    result: CommitResult
    calls: list[dict[str, Any]] = field(default_factory=list)

    def evaluate_and_commit(self, **kwargs: Any) -> CommitResult:
        self.calls.append(kwargs)
        return self.result


def _invoke(
    adapter: PolicyAdapter,
    outcome: AnalysisAdvisory | S3Failure,
) -> CommitResult:
    return adapter.evaluate_and_commit(
        store=object(),
        case=_case(),
        content_text="content requiring review",
        analysis=outcome,
        expected_revision=1,
        replay_key=ReplayKey("submitter-1", "idem-1"),
    )


def test_advisory_is_projected_to_policy_dto_and_committed_once() -> None:
    """REQ-FUN-002/004, REQ-INV-001: advisory data reaches policy without authority."""

    engine = FakePolicyEngine(_committed())
    result = _invoke(PolicyAdapter(engine), _s3_advisory())

    assert result is engine.result
    assert len(engine.calls) == 1
    call = engine.calls[0]
    assert call["case"] == _case()
    assert call["content_text"] == "content requiring review"
    assert call["expected_revision"] == 1
    assert call["replay_key"] == ReplayKey("submitter-1", "idem-1")
    advisory = call["advisory"]
    assert isinstance(advisory, PolicyAdvisory)
    assert advisory.verdict is Verdict.REVIEW
    assert advisory.severity is Severity.MEDIUM
    assert advisory.rationale == "The approved clause requires human review."
    assert advisory.prompt_version == "prompt-v1.1"
    assert advisory.model_id == "model-demo"
    assert advisory.model_version == "2026-11-20"
    assert len(advisory.citations) == 1


@pytest.mark.parametrize(
    "failure_code",
    [
        "provider_unavailable",
        "timeout",
        "invalid_response",
        "grounding_unavailable",
        "context_overflow",
    ],
)
def test_typed_analysis_failures_remain_typed_for_policy(failure_code: str) -> None:
    """REQ-INV-002: every S3 failure is passed to policy without an invented verdict."""

    engine = FakePolicyEngine(_committed())
    _invoke(PolicyAdapter(engine), _s3_failure(failure_code))

    projected = engine.calls[0]["advisory"]
    assert isinstance(projected, PolicyFailure)
    assert projected.code is PolicyFailureCode(failure_code)
    assert projected.detail == "analysis unavailable"
    assert not hasattr(projected, "verdict")


def test_failed_policy_commit_is_returned_without_audit_claim() -> None:
    """REQ-INV-004 negative: adapter preserves failed commit status and absent audit."""

    failed = CommitResult(
        status=CommitStatus.FAILED,
        decision_id="decision-1",
        audit_id=None,
        case_revision=None,
        message="audit persistence failed",
    )
    engine = FakePolicyEngine(failed)

    result = _invoke(PolicyAdapter(engine), _s3_advisory())

    assert result.status is CommitStatus.FAILED
    assert result.audit_id is None
    assert result.case_revision is None
    assert result.message == "audit persistence failed"


def test_analysis_projection_contains_no_enforcement_fields() -> None:
    """REQ-INV-001 negative: schema-valid analysis still cannot request enforcement."""

    payload = _s3_advisory().to_s1_payload()

    assert set(payload) == {
        "role",
        "verdict",
        "severity",
        "rationale",
        "citations",
        "prompt_version",
        "model_id",
        "model_version",
        "usage",
    }
    assert not {
        "action",
        "outcome",
        "enforcement",
        "actor",
        "privileges",
        "tools",
        "audit_id",
    }.intersection(payload)


def _imports_under(root: Path) -> set[str]:
    imports: set[str] = set()
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
    return imports


def test_analysis_package_does_not_import_policy() -> None:
    """REQ-INV-001 negative: S3 analysis has no dependency on policy internals."""

    imports = _imports_under(Path("src/contentguard/analysis"))
    assert not any(
        name == "contentguard.policy" or name.startswith("contentguard.policy.")
        for name in imports
    )


def test_api_adapter_does_not_import_policy_enforcement() -> None:
    """REQ-INV-001 negative: API adapter may use engine/contracts, never enforcement."""

    adapter_path = Path("src/contentguard/api/adapter.py")
    tree = ast.parse(adapter_path.read_text(encoding="utf-8"), filename=str(adapter_path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert "contentguard.policy.enforcement" not in imports
    assert "policy.enforcement" not in imports
