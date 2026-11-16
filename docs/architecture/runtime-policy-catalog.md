# Runtime Policy Catalog (D2.7)

> What the system does when each degraded or failure path is triggered.
> Status: Phase ② baseline (2026-11-16) — R-1..R-7 come from the invariant register;
> R-8..R-12 come from ADR-001 (PR #15). Evidence cells name the planned test/CI path;
> `TBD (Sx)` marks the session that fills it. A row is verified only when its evidence
> lands and passes.

| # | Trigger | System behavior | Enforces | Evidence |
|---|---|---|---|---|
| R-1 | AI service unavailable / timeout | Item held in human review queue; never auto-approved/rejected | INV-2 (REQ-INV-002) | `test/offline/test_failsafe_hold.py` `TBD (S1)` |
| R-2 | AI returns malformed/invalid analysis | Same as R-1 (treat as unavailable) | INV-2 (REQ-INV-002) | `test/offline/test_analysis_contract.py` `TBD (S3)` |
| R-3 | AI verdict conflicts with high-severity pre-filter | Human review queue (pre-filter wins toward restriction) | INV-3 (REQ-INV-003) | `test/offline/test_escalation_routing.py` `TBD (S1)` |
| R-4 | Policy engine rule evaluation error | Item held; error page raised; audit record with `error` actor | INV-2, INV-4 | `test/offline/test_policy_determinism.py` `TBD (S1)` |
| R-5 | Audit write failure | Decision voided; writes suspended (fail closed) until restored | INV-4 (REQ-INV-004) | `test/offline/test_audit_completeness.py` `TBD (S1)` |
| R-6 | Semantic evaluation gate failure on prompt/model change | Merge blocked; change reported; rollback via prompt version pin | INV-5 (REQ-INV-005) | `.github/workflows/ci.yml` gate 4 `TBD (S4)` |
| R-7 | Structural check detects enforcement call outside the policy engine | Merge blocked; path feature-flagged off at deploy | INV-1 (REQ-INV-001) | structural check `TBD (S4)` |
| R-8 | Retrieval unavailable, no usable match, stale snapshot, or forged citation | Analysis returns `GroundingUnavailable`; policy holds for human review; never auto-approve | INV-1, INV-2; REQ-FUN-005/SEC-001 | `test/offline/test_retrieval_grounding.py` `TBD (S3)` |
| R-9 | Context exceeds the input cap after compaction | No provider call; item held; fallback id recorded | INV-2; REQ-COS-001 | `test/offline/test_context_budget.py` `TBD (S3)` |
| R-10 | Unknown or invalid feature flag | Fail closed to defaults; flag change rejected; actor recorded | INV-1; REQ-FUN-007 | `test/offline/test_demo_flags.py` `TBD (S5)` |
| R-11 | Duplicate delivery, lost acknowledgment, or conflicting review on one revision | Reconcile by idempotency key; at most one commit wins; no false success | INV-4; REQ-QUA-002 | `test/offline/test_transaction_replay.py` `TBD (S2)` |
| R-12 | Audit/queue write fails inside the commit transaction | Whole transaction rolls back; API reports failed/unconfirmed; no partial effect | INV-4; REQ-INV-002/004 | `test/offline/test_audit_completeness.py` `TBD (S2)` |

> Rule of thumb encoded in every row: **when in doubt, restrict** (fail-safe) and
> **always leave a trace** (INV-4). R-8..R-12 are design commitments from ADR-001; they
> are not verified until the named evidence lands.
