# Structural Constraints (D3)

> Module organization rules the coding agent must obey. To be enforced by CI
> structural checks (**planned — TD-4**, not yet implemented) and review memos
> meanwhile.

1. **One-to-one mapping:** each architectural element maps to exactly one module.
   Module names match architectural elements (`src/contentguard/<element>/`). If the
   architecture introduces an element, a module appears; if an element is removed, its
   module is removed — no orphan modules.
2. **Extend, never replace:** new work extends the existing baseline. Wholesale
   rewrites/replacements of existing modules are rejected in review; refactor in place
   through small PRs.
3. **Requirement/invariant referencing:** every module and every public function
   references, in its docstring, the architecture decision (ADR-x) and the invariant or
   requirement ID it implements (traceability to the trace matrix).
4. **Authority boundaries (from `architecture-blueprint.md` §Components and dependencies):**
   - `analysis/` (LLM, advisory) may call **no** enforcement API; its output is data.
   - `policy/` (authoritative, SAFETY-CRITICAL) is the only module allowed to decide
     and execute enforcement actions.
   - `escalation/`, `audit/`, `api/` orchestrate but never invent policy decisions.
5. **Dependency direction:** `api → {analysis, policy}; policy → {escalation, audit}`;
   no cycles. `analysis` must not import `policy` internals. `policy` may consume the
   validated advisory result that `api` passes as read-only data, but must not import
   `analysis` internals or delegate enforcement authority to the model output. Adapters
   depend on read-only DTOs, not protected mutation internals. Aligned with
   `architecture-blueprint.md` §Components and dependencies and ADR-001.
6. **Frozen / human-owned paths** per `AGENTS.md` §4 — an agent PR touching them
   without a human co-author is rejected (CI structural check).
7. **Safety-critical change rule:** any change under `src/contentguard/policy/**` or to
   a file named in `docs/architecture/invariants.md` requires: (a) an architecture
   decision (new/updated ADR), and (b) human review approval — enforced by branch
   protection (project sheet §6).
