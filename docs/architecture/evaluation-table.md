# Candidate Evaluation Table (D2.8)

> Status: Phase ② baseline (2026-11-16). **Design judgment, not benchmark evidence** —
> see `evaluation-logbook.md` entry 2026-11-16. Source: ADR-001 (PR #15) and
> `architecture-blueprint.md`.

## Criteria and weights (derived from architectural drivers)

| Criterion | Weight | Why it matters | Driver source |
|---|---:|---|---|
| Safety and atomic persistence | 35% | Five zero-tolerance invariants; case/queue/audit must commit atomically | REQ-INV-001..005, especially REQ-INV-004 |
| Grounded AI scope fit | 25% | The project requires a genuine AI component plus retrieval grounding | REQ-FUN-002/005; project sheet p.3 |
| Build-window feasibility | 25% | Four build days with five students; coordination cost is real | proposal §4.3; RSK-3 |
| Offline verification | 15% | Deterministic tests and blocking gates must run without network | D4; REQ-GOV-006/007 |

## Candidates

- **C1 — Modular monolith:** one process, REST boundary, in-process policy engine,
  hosted LLM adapter, one transactional SQLite database.
- **C2 — Split services:** separate analysis, policy, and queue services/deployments.
- **C3 — Rules-only + optional LLM:** deterministic rules first; the LLM is optional
  enrichment.

## Comparison

| Criterion (weight) | C1 | C2 | C3 |
|---|---:|---:|---:|
| Safety and atomic persistence (35%) | 5 | 3 | 5 |
| Grounded AI scope fit (25%) | 5 | 5 | 1 |
| Build-window feasibility (25%) | 5 | 2 | 5 |
| Offline verification (15%) | 5 | 3 | 5 |
| **Weighted score** | **5.00** | **3.25** | **4.00** |

Scores are design judgments from 1 (weak) to 5 (strong), not measurements.

## Verdict

Adopt **C1 (modular monolith)**. It keeps one transactional boundary for
case/queue/audit (INV-4), keeps the advisory/authoritative split enforceable by a module
boundary (INV-1), and fits the four-day build window. C2 is rejected for distributed
consistency and coordination cost; C3 is rejected because it removes the genuine AI
component and RAG grounding required by the project. Reopen conditions are listed in
ADR-001 ("Reopen ADR if...") and `option-ledger.md`.

> Links: ADR-001 (PR #15; the file is `docs/architecture/adr/001-placeholder.md` until
> the ADR is renamed) and the module interface contracts (added by PR #15 at
> `docs/architecture/interface-contracts.md`; not present on `main` yet). Any future
> benchmark result goes to `evaluation-logbook.md` and may change a score.
