# Offline tests (deterministic)

Tests that need **no network, no API key, no model access**. CI gate 5 (regression)
runs the full directory on every commit/PR.

Rules (see `docs/code-governance/verification-constraints.md`):

- No ordering dependencies, no shared mutable state (`.agent/rules.md` C3).
- Every test docstring cites the REQ-*/INV-* ID it verifies.
- At least one **negative test** per feature (proves rejection of an invalid path).
- Fault-injection tests for the AI-unavailable paths live here (INV-2).

## Evaluation corpus checks

`test_evaluation_dataset.py` validates the fixed gate-4 corpus at
`test/eval/moderation_eval.jsonl` and the deterministic builder. Corpus
provenance, licensing, PII remediation, counts/hashes and regeneration are
documented in `test/eval/README.md`.

Run: `pytest test/offline -v`
