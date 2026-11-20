"""Typed API-boundary errors (ADR-001; REQ-FUN-001/003, REQ-INV-004)."""


class MandatoryRuleViolation(ValueError):
    """A requested human-review outcome conflicts with a mandatory policy rule."""


__all__ = ["MandatoryRuleViolation"]
