# Offline tests (deterministic)

Tests that need **no network, no API key, no model access**. CI gate 5 (regression)
runs the full directory on every commit/PR.

Rules (see `docs/code-governance/verification-constraints.md`):

- No ordering dependencies, no shared mutable state (`.agent/rules.md` C3).
- Every test docstring cites the REQ-*/INV-* ID it verifies.
- At least one **negative test** per feature (proves rejection of an invalid path).
- Fault-injection tests for the AI-unavailable paths live here (INV-2).

Run: `pytest test/offline -v`
