# ADR-002 — Human-review transition on the policy boundary with pre-commit mandatory-rule validation

- Status: Proposed (2026-11-21) — requires PM + architecture approval before any `src/contentguard/policy/` change (AGENTS.md §7 safety-critical rule)
- Amends: ADR-001 (adds the step-7 human-review transition to the policy boundary; changes nothing about the advisory/authoritative split)
- Recorded against: issue #51 (amended test plan), PR #75 (S2 slice), RM-042 thread, #76 closeout handoff, #49 endgame status

## Context

1. The approved amended test plan (#51) requires the review route to answer a
   mandatory-rule-violating moderator action with **HTTP 422 and no consequential write**.
2. The S2 slice (PR #75) implements the route against a policy-boundary fake
   (`test/offline/test_api_review_queue.py:108`): the API calls
   `policy.review_and_commit(...)`; the fake raises a typed `MandatoryRuleViolation`
   **before** any result is produced, and the test asserts `422` + `policy.calls == 1` +
   no final effect. The API's own docstring for the fake states the boundary: *"the API
   may request but never decide a transition."*
3. S1 on main (`d0f38c1`) explicitly does **not** implement the human-review transition:
   `PolicyEngine.evaluate_and_commit` documents that "a review is passed through to
   `evaluate` which rejects it" (`src/contentguard/policy/engine.py:200-201`), and the
   engine has an internal `_validate_review` currency/authorization/staleness check
   (`engine.py:627`) but no transition path. Typed analysis failures currently end in
   HOLD/ESCALATE decisions that **commit** through `EnforcementAuthority.commit`
   (REQ-INV-002 evidence, PR #62).

The gap: S2's contract assumes a policy operation that **validates a requested review
transition before committing and raises a typed violation without writing anything**;
S1 does not expose it. The mismatch is recorded in #49/#75/#76 and was triaged as
S1-owned (architecture recommendation, RM-042 thread).

## Decision

Extend `PolicyEngine` with a `review_and_commit(...)` operation implementing the step-7
human-review transition, atomically, in this order:

1. Load the case row and its **pinned** snapshot (same pattern as
   `evaluate_and_commit`).
2. Run the existing `_validate_review` checks unchanged (case currency, status
   reviewability, revision/snapshot/content-hash freshness, moderator role, non-empty
   rationale).
3. Validate the **requested outcome against the pinned snapshot's mandatory rules**
   (for example: a high-severity case cannot be approved without the mandatory review
   path; a human review cannot waive a mandatory rule). On violation, raise a new typed
   `MandatoryRuleViolation` (policy error type, carrying a stable machine-readable code)
   with **no write of any kind**: no case revision bump, no audit row, no queue entry,
   no replay record.
4. On success, perform the transition through the existing atomic commit machinery
   (audit row, revision bump, replay idempotency) — unchanged.

The API layer maps the typed violation to HTTP 422 and nothing else. Authority stays
with policy end to end: the API requests, policy decides, and a mandatory-rule refusal
is an input/action **validation** outcome, not a moderation decision.

## Boundaries made explicit

- REQ-INV-002 ("typed failures commit to a durable human queue") continues to apply to
  **moderation decisions** (analysis failures → HOLD/ESCALATE). A
  `MandatoryRuleViolation` raised by review-transition validation is an action
  rejection, not a moderation decision; it deliberately writes nothing. This boundary
  is part of the decision, not an oversight, and the invariant's negative tests are
  unaffected.
- The API never validates mandatory rules itself; adding such checks outside policy is
  an invariant violation (INV-1) even if it would pass tests.

## Alternatives considered and rejected

- **API-side validation of mandatory rules** — moves a policy judgment out of the
  authoritative component; breaks the documented request/decide boundary even though it
  would pass the offline suite.
- **Relax #51 to accept a committed REJECT for violating reviews** — would rewrite an
  approved test plan after the fact and weaken the no-consequential-write guarantee the
  plan was written for.
- **Commit the invalid transition to the review queue** — creates durable garbage state
  and a false audit trail; rejected on integrity grounds.

## Consequences

- Positive: the #51 review-route contract becomes implementable against the real policy
  kernel; the S1/S2 mismatch recorded in #49/#75/#76 closes; trace-matrix rows
  REQ-FUN-003 / REQ-INV-003 (S2 planned) can flip from `TBD (S2)` to real evidence once
  the live integration test lands.
- Negative / cost: one more policy operation to maintain and test; a new typed error in
  the policy surface; the invariant boundary above must be stated in
  `docs/architecture/invariants.md` (one clarifying sentence, added in the implementing PR).
- Verification required before merge: policy-layer negative tests (violation → zero
  writes, asserted on revision, audit row count, and queue depth), full offline suite
  green, ruff/mypy clean, gate 2e structural checks green, `docs/ai-use-log.yaml`
  updated in the implementing session, session transcript recorded.

## Implementation slice (agent session, after this ADR is approved)

- `src/contentguard/policy/`: add `MandatoryRuleViolation` typed error;
  `PolicyEngine.review_and_commit(...)` implementing steps 1–4; keep
  `evaluate_and_commit` unchanged.
- `src/contentguard/policy/` errors module: export the typed error.
- `test/offline/`: policy-layer negative tests for review_and_commit (currency/staleness
  cases reuse `_validate_review` behaviour; mandatory-rule case asserts zero writes);
  no `test/live` changes.
- Docs in the same PR: one clarifying sentence in `docs/architecture/invariants.md`;
  trace-matrix note for REQ-FUN-003/INV-003 pointing at the new test.
- Out of scope: any change to `evaluate_and_commit`, the advisory contract, or
  requirement fit criteria.
