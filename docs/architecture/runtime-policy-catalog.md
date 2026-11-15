# Runtime Policy Catalog (D2.7)

> What the system does when each degraded or failure path is triggered.
> **Status: DRAFT skeleton** — seeded with the fail-safe paths implied by the invariant
> register; completed at the W12 architecture session.

| # | Trigger | System behavior | Enforces | Evidence |
|---|---|---|---|---|
| R-1 | AI service unavailable / timeout | Item held in human review queue; never auto-approved/rejected | INV-2 (REQ-INV-002) | fault-injection test TBD |
| R-2 | AI returns malformed/invalid analysis | Same as R-1 (treat as unavailable) | INV-2 (REQ-INV-002) | contract test TBD |
| R-3 | AI verdict conflicts with high-severity pre-filter | Human review queue (pre-filter wins toward restriction) | INV-3 (REQ-INV-003) | routing matrix test TBD |
| R-4 | Policy engine rule evaluation error | Item held; error page raised; audit record with `error` actor | INV-2, INV-4 | integration test TBD |
| R-5 | Audit write failure | Decision voided; writes suspended (fail closed) until restored | INV-4 (REQ-INV-004) | integration test TBD |
| R-6 | Semantic evaluation gate failure on prompt/model change | Merge blocked; change reported; rollback via prompt version pin | INV-5 (REQ-INV-005) | CI gate 4 |
| R-7 | Structural check detects enforcement call outside policy engine | Merge blocked; path feature-flagged off at deploy | INV-1 (REQ-INV-001) | CI structural gate |

> Rule of thumb encoded in every row: **when in doubt, restrict** (fail-safe) and
> **always leave a trace** (INV-4).
