"""Authority and snapshot-trust tests for ADR-001, REQ-FUN-005, REQ-SEC-001."""

from __future__ import annotations

from fakes import analysis as fa

from contentguard.analysis import snapshot
from contentguard.analysis.contracts import PolicySnapshot
from contentguard.analysis.errors import DomainValidationError


def test_non_integer_revision_rejected():
    """String revision is rejected; revision must be an integer (REQ-FUN-005, REQ-INV-002)."""
    snapshot_obj = fa.build_snapshot((fa.make_clause("c-01"),))
    result = snapshot.load_snapshot(snapshot_obj.snapshot_id, "1", fa.FakeSnapshotSource(snapshot_obj))
    assert isinstance(result, DomainValidationError)
    assert result.code == "stale_snapshot"


def test_missing_explicit_approval_rejected():
    """Absence of explicit approval is never treated as approved (REQ-SEC-001, REQ-FUN-005)."""
    snapshot_obj = fa.build_snapshot((fa.make_clause("c-01"),), status="unapproved")
    result = snapshot.validate_approval(snapshot_obj, fa.make_anchor(snapshot_obj, status="unapproved"))
    assert isinstance(result, DomainValidationError)
    assert result.code == "invalid_approval_status"


def test_conflicting_registry_digest_rejected():
    """Conflicting registry corpus digest is rejected (REQ-FUN-005, REQ-INV-002)."""
    snapshot_obj = fa.build_snapshot((fa.make_clause("c-01"),))
    anchor = fa.FakeTrustRegistry(fa.make_anchor(snapshot_obj), mode="conflicting").lookup(
        snapshot_obj.corpus_id, snapshot_obj.revision
    )
    assert not isinstance(anchor, DomainValidationError)
    result = snapshot.verify_corpus_digest(snapshot_obj, anchor)
    assert isinstance(result, DomainValidationError)
    assert result.code == "digest_mismatch"


def test_approval_marker_alone_is_insufficient():
    """Approved marker and self-hash alone do not establish trust (REQ-SEC-001)."""
    tampered = fa.load_fixture("snapshot_tampered_selfhash.json")
    clauses = (fa.make_clause("c-01"),)
    snapshot_obj = fa.build_snapshot(clauses)
    assert tampered["corpus_digest"] != snapshot_obj.corpus_digest
    result = snapshot.verify_corpus_digest(
        PolicySnapshot(**{**snapshot_obj.__dict__, "corpus_digest": tampered["corpus_digest"]}),
        fa.make_anchor(snapshot_obj),
    )
    assert isinstance(result, DomainValidationError)
