"""Human review queue routing (REQ-INV-003/004).

S1 provides only the minimal transaction-enlisted queue repository the policy kernel
needs to prove an atomic commit; intake, queue views, review APIs and duplicate-delivery
handling are S2-owned. This package must not import ``contentguard.policy``.

Only the queue DTO exists in CP1; the repository arrives in a later slice.
"""

__all__: list[str] = []
