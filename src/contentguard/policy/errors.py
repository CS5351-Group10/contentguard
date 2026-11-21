"""Policy error hierarchy (REQ-INV-001/003/004).

All policy-domain rejections derive from :class:`PolicyError` so callers can catch a
single family. :class:`PolicyKernelError` is the controlled "no writes, no invented
result" failure (S1 plan §3.5 step 3 / step 10). The specialized subclasses make the
distinction between stale evidence, unauthorized reviewers, revision/snapshot conflicts
and cross-module safety violations explicit and testable.
"""

from __future__ import annotations


class PolicyError(Exception):
    """Base class for every policy-domain error (no partial state is written)."""


class PolicyKernelError(PolicyError):
    """A controlled evaluation failure: no decision and no write are produced."""


class MandatoryRuleViolation(PolicyError):
    """A requested human-review outcome conflicts with a mandatory policy rule
    (ADR-002 review-transition validation).

    Raised by ``PolicyEngine.review_and_commit`` *before any write*: the refusal is an
    action validation outcome, not a moderation decision, so nothing is committed —
    no case revision bump, no audit row, no queue entry, no replay record. Carries a
    stable machine-readable code so the API layer can project it to HTTP 422 by error
    identity alone.
    """

    code = "MANDATORY_RULE_VIOLATION"


class PolicyConflictError(PolicyError):
    """Revision/snapshot/state conflict; the caller's view is stale."""


class InvalidReviewError(PolicyError):
    """A human review was supplied for a case that cannot be reviewed."""


class StaleReviewError(PolicyError):
    """A human review's currency fields no longer match the case (stale evidence)."""


class UnauthorizedReviewError(PolicyError):
    """A human review's reviewer is not authorized (or its rationale is empty)."""


class ForbiddenAuthorityError(PolicyError):
    """A protected write was attempted without a valid engine-minted authority token."""


__all__ = [
    "ForbiddenAuthorityError",
    "InvalidReviewError",
    "MandatoryRuleViolation",
    "PolicyConflictError",
    "PolicyError",
    "PolicyKernelError",
    "StaleReviewError",
    "UnauthorizedReviewError",
]
