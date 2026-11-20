# Trace Matrix (D2.4)

> Every requirement → its enforcing component → its test/evidence → its runtime monitor.
>
> Kept in lockstep with `docs/req/requirements.yaml` (CI smoke test checks IDs appear here).

The table below maps all 31 requirements in the v1.0 registry. A test file or evidence item marked `TBD (Sx)` is **planned, not yet implemented or verified**. It must not be counted as passing evidence.

Runtime-monitor cells name the **intended** production monitor; until the owning slice's production monitor exists (S2 api / S3 analysis / S5 evaluation), monitors exist only as log/audit artifacts — except the governance rows, whose monitors are the already-live CI gates. Treat product-monitor cells as planned, not verified.

- **S1:** Policy kernel and audit (11/17).
- **S2:** Intake and queue (11/18).
- **S3:** RAG and analysis (11/18–19; merged #52, 11/20).
- **S4:** CI and governance (11/19).
- **S5:** Evaluation and revision (11/20).

| Req ID | Type | Enforcing component | Test / evidence | Runtime monitor |
|---|---|---|---|---|
| REQ-INV-001 | invariant | policy engine + module boundary | `test/offline/test_invariants.py` — structural call-graph + forged-action negative test; `test/offline/test_release_invariants_acceptance.py` — forged decision rejected before any write (PR #62); structural element/cycle/path checks in `test/offline/test_structural_check.py` (gate 2e, PR #69) | CI structural check (gate 2e, TD-4 / #69) |
| REQ-INV-002 | invariant | escalation queue + policy default rule | `test/offline/test_release_invariants_acceptance.py` — all five typed failure codes hold/escalate and commit to a durable human queue (PR #62); S2 planned (not yet on main): `test_failsafe_hold.py`, `test_transaction_replay.py` `TBD (S2)`; S3: `test/offline/test_analysis_contract.py` + `test_analysis_handoff.py` — typed failure contract (PR #52) | queue depth + audit anomaly alert |
| REQ-INV-003 | invariant | policy routing rules | `test/offline/test_escalation_routing.py` — severity × policy matrix; `test/offline/test_release_invariants_acceptance.py` — high severity cannot finalize without a current review (PR #62) | daily audit reconciliation |
| REQ-INV-004 | invariant | audit subsystem | `test/offline/test_audit_completeness.py` — exactly one record per decision + write-failure rollback; `test/offline/test_release_invariants_acceptance.py` — late-write failure rolls back audit/case/queue (PR #62) | audit write-path health |
| REQ-INV-005 | invariant | CI gate 4 | `.github/workflows/ci.yml` gate 4 + replay in `test/eval/`; `test/offline/test_release_invariants_acceptance.py` — bad/missing replay blocked under `--strict` (PR #62) | gate 4 on prompt/model PRs |
| REQ-FUN-001 | functional | API intake | `test/offline/test_intake.py` — four outcomes + resolvable audit id + incomplete-state cases `TBD (S2)` | request/outcome logging |
| REQ-FUN-002 | functional | analysis (LLM advisory) | `test/offline/test_analysis_contract.py`, `test_analysis_provider.py`, `test_analysis_handoff.py` — offline contract/advisory path (PR #52); live configured-LLM evidence remains pending (no `test/live/test_analysis_live.py` on main) | response-schema failures |
| REQ-FUN-003 | functional | escalation queue + API review | `test/offline/test_release_must_acceptance.py` — failure→hold→review finalization at the policy/queue boundary (PR #62); S2 `test/offline/test_review_queue.py` — API review `TBD (S2)` | queue depth |
| REQ-FUN-004 | functional | policy engine + audit | `test/offline/test_policy_justification.py` — rule/fallback id; `test/offline/test_release_must_acceptance.py` — attribution pinned across a policy change (PR #62) | decision reason in audit |
| REQ-FUN-005 | functional | analysis retrieval | `test/offline/test_retrieval_grounding.py`, `test_citation_binding.py`, `test_context_trust.py` — authentic/forged/stale/conflicting/injection/no-match (PR #52); the 100-case pinned synthetic fixture set (40 match / 60 tampering-error) meets the sampling minima, while Testing/PM ratification of the provisional targets and live acceptance remain pending | grounding failure metric |
| REQ-FUN-006 | functional | none (wont; ADR extension seam) | Scope decision in registry + ADR seam `TBD (S5)` | n/a (deferred) |
| REQ-FUN-007 | functional | demo harness / feature flags | `test/offline/test_demo_flags.py` — comparable baseline/enhanced runs, conditional on S5 capacity under Issue #23 `TBD (S5)` | flag configuration audit |
| REQ-SEC-001 | security | analysis context boundary | `test/offline/test_context_trust.py` + `test_analysis_authority.py` — direct/indirect injection + forged citations (PR #52); live/integration injection acceptance remains pending | schema/injection failure counter |
| REQ-SEC-002 | security | API intake validation | `test/offline/test_intake_validation.py` — malformed/missing/unsupported + boundary `TBD (S2)` | 4xx rate |
| REQ-SEC-003 | security | API auth + policy review | `test/offline/test_moderator_auth.py` — authorized/unauthorized/stale/mandatory-rule `TBD (S2)` | 401/403 audit |
| REQ-SEC-004 | security | audit/evidence access | `test/offline/test_evidence_access.py` — owner/assigned/unauthorized + retention clock `TBD (S5)` | access log |
| REQ-SEC-005 | security | release/zip scan | release checklist + secret scan `TBD (S4)` | SEC-005 release gate |
| REQ-QUA-001 | quality | policy engine | `test/offline/test_policy_determinism.py` — repeat/reorder fixed fixtures; `test/offline/test_release_must_acceptance.py` — replay returns the same audit id (PR #62) | n/a |
| REQ-QUA-002 | quality | policy + DB transaction | S2 planned (not yet on main): `test/offline/test_transaction_replay.py` — opposite actions, duplicate delivery, lost ack `TBD (S2)` | conflict/duplicate metric |
| REQ-QUA-003 | quality | eval harness | Partial evaluation evidence: `test/eval/` report + `evaluation-logbook.md`; full evaluation deferred under Issue #23 `TBD (S5)` | eval dashboard |
| REQ-PER-001 | performance | metrics/log | Full benchmark (≥100 requests) deferred under Issue #23; performance measurement remains limited to available logging evidence `TBD (S5)` | p50/p95 latency |
| REQ-COS-001 | cost | provider usage accounting + analysis context budget | `test/offline/test_context_budget.py` + `test_analysis_provider.py` — context-envelope and usage-accounting fixtures on main via PR #52; the ≥100-request benchmark and provider-reported usage coverage remain pending; aggregate logical-request budget remains OPEN and separate from the 8192-token envelope; full benchmark deferred under Issue #23 | token usage counter |
| REQ-GOV-001 | governance | ai-use-log + transcripts | `docs/ai-use-log.yaml` + `transcripts/` + review | gate 6 + review memo |
| REQ-GOV-002 | governance | gate 1 | `scripts/check_test_approval.py` + test-plan issues | gate 1 |
| REQ-GOV-003 | governance | gate 3 | `scripts/validate_requirements.py` + validator tests | gate 3 |
| REQ-GOV-004 | governance | trace matrix + registry | this file + coverage `test_smoke.py` | CI coverage check |
| REQ-GOV-005 | governance | branch protection + ADR/CODEOWNERS | protection settings + ADR | required review/co-sign |
| REQ-GOV-006 | governance | gate 2 | ruff + mypy (+ dependency check S4) | gate 2 |
| REQ-GOV-007 | governance | gate 5 | `pytest test/offline` | gate 5 |
| REQ-GOV-008 | governance | gate 6 | `scripts/check_ai_use_log.py` | gate 6 |
| REQ-GOV-009 | governance | branch protection | `blocking-gates` required check | settings audit |

> Rows marked TBD are filled as code lands; the matrix is updated in the same PR that implements the requirement (co-evolution evidence for Report.md §5).
