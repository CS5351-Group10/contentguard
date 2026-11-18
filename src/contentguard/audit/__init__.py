"""Decision audit log — append-only, transaction-enlisted (REQ-INV-004).

This package must not import ``contentguard.policy`` (structural rule 5); it validates
against local value sets that a test keeps in lockstep with the policy enums.

Only the record schema exists in CP1; the repository arrives in a later slice.
"""

__all__: list[str] = []
