# Invariant Register (D2.3)

> Every invariant: statement, source requirement ID, enforcing component, verification
> method, and a **concrete** operational fallback. Zero-tolerance: if any verification
> fails, the merge is blocked. Sources: `docs/req/requirements.yaml` (REQ-INV-*).

## INV-1 — AI output never executes enforcement

- **Statement:** the LLM analysis component never directly executes an enforcement
  action (approve/publish, reject/remove, ban). Only the deterministic policy engine
  decides and executes enforcement.
- **Source requirement:** REQ-INV-001
- **Enforcing component:** policy engine (deterministic); structurally enforced by
  module boundary `src/contentguard/policy/`
- **Verification method:** structural check (import/call-graph test) + negative test
  proving outside calls are blocked
- **Operational fallback if violated:** CI blocks the merge; the offending path is
  feature-flagged off at deploy until a human-approved fix lands

## INV-2 — Fail-safe hold on AI unavailability

- **Statement:** AI unavailable / timeout / invalid response ⇒ content goes to the
  human review queue; never auto-approved, never auto-rejected.
- **Source requirement:** REQ-INV-002
- **Enforcing component:** escalation (human review queue) + policy engine default rule
- **Verification method:** fault-injection unit test (AI client mocked to fail)
- **Operational fallback if violated:** audit subsystem marks the decision invalid,
  the item is reverted to the queue, on-call moderator alerted

## INV-3 — High-severity always reaches human review

- **Statement:** high-severity content (AI-flagged or deterministic pre-filter) goes
  to human review regardless of any automated verdict, including a policy allow.
- **Source requirement:** REQ-INV-003
- **Enforcing component:** policy engine routing rules
- **Verification method:** table-driven test over the severity × policy matrix
- **Operational fallback if violated:** daily audit reconciliation job reopens the
  item into the queue; case logged in `docs/bug-diary.md`

## INV-4 — Every decision leaves an audit record

- **Statement:** every moderation decision persists an audit record (content hash, AI
  verdict, policy rule hit, final action, timestamps, actor IDs).
- **Source requirement:** REQ-INV-004
- **Enforcing component:** audit subsystem
- **Verification method:** integration test asserting one complete record per decision
- **Operational fallback if violated:** decision voided, item re-enters the pipeline,
  audit writes suspend (fail closed) until the write path is restored

## INV-5 — Prompt/model changes pass semantic evaluation before production

- **Statement:** no prompt or model configuration change merges to production without
  a green replay of the fixed evaluation set against quality thresholds (CI gate 4).
- **Source requirement:** REQ-INV-005
- **Enforcing component:** CI semantic evaluation gate
  (`scripts/check_semantic_eval.py`)
- **Verification method:** CI gate replay of `test/eval/moderation_eval.jsonl`
- **Operational fallback if violated:** instant rollback via prompt version pinning
  (`prompts/prompt_vN.yaml`); incident recorded in `docs/debt-register.md`

---

Change control: invariants change only through a new/updated ADR **and** human approval
(`.agent/rules.md` covenant). Adding an invariant here requires adding REQ-INV-* to the
registry in the same PR (trace matrix keeps them locked together).
