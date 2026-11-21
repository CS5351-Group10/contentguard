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
3. S1 on main (verified at `802c59a`; policy engine unchanged since `af63260`) already
   has a **partial** step-7 path: `PolicyEngine.evaluate` accepts
   `review: ReviewRequest | None` and routes a current authorized review to
   `_build_review_decision` (the `if review is not None:` branch in
   `src/contentguard/policy/engine.py`), whose docstring specifies that the **first
   matching `REJECT` rule is a mandatory floor that overrides the review**; otherwise
   the reviewed APPROVE/REJECT applies. The module header and the `evaluate` docstring
   still say "Step 7 — the human-review transition — is NOT implemented in this slice";
   the docstring lags the code — the executable path, not the docstring, is the
   evidence. The disposition of that review decision persists through the existing
   commit path.

The gap (restated precisely, per the architecture review on this PR): what S1 lacks is
(a) the **S2-compatible `review_and_commit` operation** with the exact
parameter/exception contract the #75 adapter is written against, and (b) a **typed
pre-commit refusal with zero consequential writes** — the current mandatory REJECT
floor produces a *decision that commits* (audit + revision + queue), which cannot
satisfy #51's "422 with no consequential write" for a mandatory-rule-violating review
request. The mismatch is recorded in #49/#75/#76 and was triaged as S1-owned
(architecture recommendation, RM-042 thread).

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

## S2 adapter and exception contract

The #75 adapter invokes the policy boundary as
`review_policy.review_and_commit(CaseView, reviewer_id, expected_revision,
requested_outcome, rationale)` and currently catches an **API-owned**
`MandatoryRuleViolation`. To keep one authority and one error identity:

- `MandatoryRuleViolation` becomes a **policy-owned** typed error (stable
  machine-readable code) exported from `src/contentguard/policy/`.
- The S2 adapter's policy client catches the **policy-owned** error and projects it to
  HTTP 422 through the API's existing typed-failure error mapping. The API performs no
  mandatory-rule evaluation of its own — it translates error identity only.
- The stale API-owned exception is replaced (same PR as the S2 adapter update, or
  earlier if #75 merges first — the adapter must be updated before any merge of the
  policy change so the catch never misses).
- Parameter flow: authenticated review evidence (`reviewer_id`, non-empty `rationale`),
  pinned identity (`case_id`, `expected_revision`, `policy_snapshot_id`,
  `policy_snapshot_digest`, `content_hash`), and replay identity (actor idempotency
  key) reach `review_and_commit` as explicit parameters built from the authenticated
  request. The API never decides — it assembles and forwards.
- **No HTTP rejection after commit**: once the transition commits, the API answers with
  the committed outcome; the 422 path exists only for pre-commit refusals.

## Replay ordering and atomicity

`review_and_commit` preserves the ordering guarantees the existing commit path
documents for `evaluate_and_commit`:

1. Load the case row and pinned snapshot; a same-key/**same-payload** committed retry
   is recognized and reconciled **before** revision/status precondition checks (a
   retry after snapshot activation or revision advance returns the stored result, not a
   spurious conflict); a same-key/**different-payload** retry is a CONFLICT.
2. Mandatory-rule refusals leave **case revision/status, review queue, audit log, and
   replay records unchanged** (zero writes, no partial state).
3. A valid requested REJECT commits **exactly once** — case row, audit entry, queue
   effect, and replay record atomically.
4. Authorized high-severity reviews remain possible whenever the mandatory rules permit
   them; the floor only overrides reviews that would waive a mandatory rule.
5. Read/validation and commit are fenced against a concurrent case or snapshot change
   (same transaction/locking pattern as `evaluate_and_commit`).

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
  `PolicyEngine.review_and_commit(...)` implementing the decision steps above; keep
  `evaluate_and_commit` unchanged.
- `src/contentguard/policy/` errors module: export the typed error.
- `src/contentguard/api/` adapter: switch the catch to the policy-owned error (same
  change-set as the policy change, or sequenced so the catch never misses — see the
  adapter/exception contract above).
- **Acceptance matrix** (real engine/store plus HTTP-adapter integration; the
  fake-based 422 test alone cannot establish these):
  - prohibited approve (mandatory-rule violation) → HTTP 422 **and zero writes**
    (case revision/status, queue depth, audit row count, replay records all unchanged);
  - permitted reject → **exactly one atomic commit** (case + audit + queue + replay
    records land together);
  - valid high-severity review → commits;
  - stale or unauthorized review evidence → typed validation failure without commit;
  - duplicate replay (same key, same payload) → reconciled stored result;
    conflicting replay (same key, different payload) → CONFLICT;
  - injected persistence failure → rollback, no partial state.
- Docs in the same PR: one clarifying sentence in `docs/architecture/invariants.md`;
  trace-matrix note for REQ-FUN-003/INV-003 pointing at the new tests.
- Out of scope: any change to `evaluate_and_commit`, the advisory contract, or
  requirement fit criteria.
