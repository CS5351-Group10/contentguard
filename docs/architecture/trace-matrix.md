# Trace Matrix (D2.4)

> Every requirement → its enforcing component → its test/evidence → its runtime monitor.
> Kept in lockstep with `docs/req/requirements.yaml` (CI smoke test checks IDs appear here).

| Req ID | Type | Enforcing component | Test / evidence | Runtime monitor |
|---|---|---|---|---|
| REQ-INV-001 | invariant | policy engine module boundary | structural check + negative test (TBD path) | import/call-graph check in CI |
| REQ-INV-002 | invariant | escalation queue + policy default rule | fault-injection unit test (TBD path) | audit anomaly alert |
| REQ-INV-003 | invariant | policy engine routing | table-driven routing test (TBD path) | daily audit reconciliation job |
| REQ-INV-004 | invariant | audit subsystem | audit completeness integration test (TBD path) | audit write-path health check |
| REQ-INV-005 | invariant | CI semantic evaluation gate | gate 4 replay report | gate 4 on every prompt/model PR |
| REQ-FUN-001 | functional | API + intake | integration test (TBD path) | request/outcome logging |
| REQ-FUN-002 | functional | analysis (LLM advisory) | contract test (TBD path) | response-schema validation failures |
| REQ-FUN-003 | functional | escalation queue UI/API | integration test (TBD path) | queue depth metric |

> Rows marked TBD are filled as code lands; the matrix is updated in the same PR that
> implements the requirement (co-evolution evidence for Report.md §5).
