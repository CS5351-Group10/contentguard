"""Audit error hierarchy (REQ-INV-004).

The audit subsystem must not import ``contentguard.policy``; these errors are local so
the audit package is self-contained.
"""

from __future__ import annotations


class AuditError(Exception):
    """Base class for audit-domain errors."""


class AuditValidationError(AuditError):
    """An audit record failed schema validation (missing/unknown key, bad type, empty)."""


class AuditConflictError(AuditError):
    """An audit insert reused a ``decision_id`` with a different payload."""


__all__ = [
    "AuditConflictError",
    "AuditError",
    "AuditValidationError",
]
