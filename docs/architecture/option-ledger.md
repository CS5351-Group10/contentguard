# Option Ledger (D2.11, optional)

> Rejected architectural options and **when they should be reconsidered**.
> Status: Phase ② baseline (2026-11-16); links ADR-001 (PR #15).

| Option | Why rejected | Reconsider when |
|---|---|---|
| Split services (analysis / policy / queue) | Distributed audit/queue consistency, deployment and coordination cost in a four-day build; weaker atomic commit for INV-4 | Measured multi-process throughput or an independent-deployment requirement appears (ADR reopen condition) |
| Rules-only + optional LLM | Would remove the genuine AI component and retrieval grounding required by the project sheet | Provider unavailable for the whole build window (fallback/demo only), or the course scope changes |
| Vector service / embeddings | Extra dependency, cost, and evaluation burden; a small approved policy corpus supports deterministic lexical retrieval with stable tie-breaks | Evaluation recall on the fixed set falls below the agreed threshold |
| Appeal endpoint | `wont` for MVP; ADR-001 reserves the extension seam; human review covers the demo | The 2026-11-20/21 architecture revision adopts it, or REQ-FUN-006 changes priority |
| Gate 7 (review-memo presence gate) | Extra CI surface and an already-growing memo backlog during build; project sheet §6 requires six gates, not seven | After the 11/21 transcript/architecture lock and the memo backlog is zero; issue #4 has the full spec |
| SQLite → server database | Single-writer limits; local transactions reduce failure modes for the course demo | Measured DB contention or a multi-worker requirement appears |

> An option re-enters consideration only when one of its reconsider triggers fires AND
> a human approves reopening the ADR (see ADR-001 "conditions that would reopen").
