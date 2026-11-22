"""Typed API-boundary errors (ADR-001; REQ-FUN-001/003, REQ-INV-004).

``MandatoryRuleViolation`` is the policy-owned typed error (ADR-002): the API
layer re-exports it so the review route keeps a stable import surface and the
422 mapping can never disagree with the policy engine about the error type.
"""

from ..policy.errors import MandatoryRuleViolation

__all__ = ["MandatoryRuleViolation"]
