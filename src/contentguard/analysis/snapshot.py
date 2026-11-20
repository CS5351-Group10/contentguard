"""Snapshot trust, approval and digest helpers (ADR-001, REQ-FUN-005, REQ-SEC-001).

Every public function cites its governing requirements.
"""

from __future__ import annotations

import hashlib
import unicodedata

from .contracts import PolicySnapshot, TrustAnchor
from .errors import DomainValidationError
from .ports import SnapshotSourcePort, TrustRegistryPort


def canonical_text(text: str) -> str:
    """Normalize clause text to NFC with canonical line endings (REQ-FUN-005, ADR-001)."""
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def canonical_clause_digest(text: str) -> str:
    """Compute one clause digest from normalized text (REQ-FUN-005, REQ-SEC-001)."""
    return "sha256:" + hashlib.sha256(canonical_text(text).encode("utf-8")).hexdigest()


def load_snapshot(snapshot_id: str, revision: int, source: SnapshotSourcePort) -> PolicySnapshot | DomainValidationError:
    """Load a pinned snapshot from an injected read-only source (REQ-FUN-005, REQ-INV-002)."""
    if not isinstance(revision, int) or isinstance(revision, bool):
        return DomainValidationError("stale_snapshot", "revision must be int", snapshot_id, -1)
    loaded = source.load(snapshot_id, revision)
    if isinstance(loaded, DomainValidationError):
        return loaded
    if loaded.snapshot_id != snapshot_id or loaded.revision != revision:
        return DomainValidationError("stale_snapshot", "snapshot mismatch", snapshot_id, revision)
    return loaded


def lookup_trust_anchor(corpus_id: str, corpus_revision: int, registry: TrustRegistryPort) -> TrustAnchor | DomainValidationError:
    """Look up the synthetic approved release binding (REQ-FUN-005, REQ-SEC-001)."""
    if not isinstance(corpus_revision, int) or isinstance(corpus_revision, bool):
        return DomainValidationError("stale_snapshot", "revision must be int", corpus_id, -1)
    anchor = registry.lookup(corpus_id, corpus_revision)
    if isinstance(anchor, DomainValidationError):
        return anchor
    if anchor.corpus_id != corpus_id or anchor.corpus_revision != corpus_revision:
        return DomainValidationError("stale_snapshot", "binding mismatch", corpus_id, corpus_revision)
    return anchor


def validate_approval(snapshot: PolicySnapshot, anchor: TrustAnchor) -> PolicySnapshot | DomainValidationError:
    """Verify explicit approval status and reference against the registry (REQ-SEC-001)."""
    if snapshot.approval.status != "approved" or anchor.status != "approved":
        return DomainValidationError(
            "invalid_approval_status", "explicit approval required", snapshot.snapshot_id, snapshot.revision
        )
    if (
        snapshot.approval.approval_revision != anchor.approval_reference
        or snapshot.approval.approver_ref != anchor.approved_by
        or snapshot.snapshot_id != anchor.policy_snapshot_id
    ):
        return DomainValidationError(
            "approval_reference_mismatch", "approval metadata mismatch", snapshot.snapshot_id, snapshot.revision
        )
    return snapshot


def compute_corpus_digest(snapshot: PolicySnapshot) -> str:
    """Compute the canonical corpus digest proposal (REQ-FUN-005, ADR-001)."""
    payload = "\n".join(
        f"{clause.clause_id}@{clause.clause_revision}:{clause.clause_digest}"
        for clause in sorted(snapshot.clauses, key=lambda item: (item.clause_id, item.clause_revision))
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_corpus_digest(snapshot: PolicySnapshot, anchor: TrustAnchor) -> PolicySnapshot | DomainValidationError:
    """Verify corpus integrity against the trusted binding (REQ-FUN-005, REQ-INV-002)."""
    digest = compute_corpus_digest(snapshot)
    if snapshot.corpus_digest != digest or anchor.approved_corpus_digest != digest or anchor.policy_snapshot_digest != digest:
        return DomainValidationError("digest_mismatch", "corpus digest mismatch", snapshot.snapshot_id, snapshot.revision)
    return snapshot
