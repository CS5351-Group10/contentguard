# Verification Constraints (D4)

> The rules the verification agent (and human reviewers) apply. Three-tier verification:
> **structural**, **regression**, **behavioral**.

## Universal rules

1. Every fit criterion in `docs/req/requirements.yaml` has **at least one test**.
2. Every invariant has at least one test that **fails when the invariant is violated**
   (negative test — required per feature by `.agent/rules.md`).
3. Every test references the requirement or invariant ID it verifies (docstring).
4. Every new round of work runs **all** previous rounds' test suites with **zero
   regressions** (CI gate 5; `pytest test/offline` = the full deterministic suite).

## Tier 1 — Structural (every commit / PR)

- Imports, module boundaries, one-to-one element↔module mapping
  (`docs/code-governance/structural-constraints.md`).
- Permissions conformance: agent PRs touch only whitelisted paths
  (`docs/architecture/permission-model.md`).
- Architectural fitness functions: call-graph check that enforcement API is reachable
  only from `src/contentguard/policy/` (INV-1).
- Lint + type-check clean (`ruff`, `mypy`).

## Tier 2 — Regression (every PR)

- Full prior suites: `pytest test/offline -v` (deterministic; no network).
- Deterministic tests live in `test/offline/`; **live** tests (needing API access) in
  `test/live/` and never run in the offline regression tier.

## Tier 3 — Behavioral (quality thresholds)

- Semantic evaluation for the AI component: fixed evaluation set
  (`test/eval/moderation_eval.jsonl`) replayed by CI gate 4 on any prompt/model change.
- Metrics (thresholds finalized with ADR-001; initial drafts):
  - verdict agreement with the labeled set ≥ agreed threshold
  - **zero safety escapes** (high-severity item never auto-approved) — hard 0
  - faithfulness/relevance of rationales ≥ agreed threshold (LLM-judge rubric)
- Fault-injection: AI-unavailable paths behave per runtime policy catalog R-1/R-2.

## Evidence discipline

- Gate failures are never waived silently; a waiver requires a review-memo entry with
  verdict CHANGES REQUIRED→APPROVE chain and a debt-register line.
- `docs/review-memo.md`: one memo per PR — spec alignment, architecture alignment,
  code & test quality, operational metadata, security & efficiency throughout, ending
  in APPROVE / CHANGES REQUIRED / REJECT.
