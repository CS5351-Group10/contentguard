"""Deterministic policy engine — authoritative component (SAFETY-CRITICAL).

REQ-INV-001 requires that only this package can authorize enforcement. This
``__init__`` deliberately does **not** import or re-export
``policy.enforcement.EnforcementAuthority``; S2's API must use
``PolicyEngine.evaluate`` / ``PolicyEngine.evaluate_and_commit`` only. The structural
invariant test scans for any other import of that module.

Only the data contracts exist in CP1; snapshot/prefilter/engine/store arrive in later
slices.
"""

__all__: list[str] = []
