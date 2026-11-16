# Structural Constraints (D3)

> Module organization rules the coding agent must obey. To be enforced by CI
> structural checks (**planned — TD-4**, not yet implemented) and review memos
> meanwhile.

1. **One-to-one mapping:** each architectural element maps to exactly one module, and the
   module name mirrors the element name. The **element set** is fixed by
   `architecture-blueprint.md` + ADR-001 — adding, renaming or splitting an element requires
   a new architecture decision, not a quiet new directory. No orphan modules: if an element
   is removed, its module goes with it. (The current placeholder layout in `AGENTS.md` §5 is
   a name sketch, not a licence to create directories ahead of the element.)
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
   without a human co-author is rejected in review; CI cannot see authorship, so this one
   stays a review rule (TD-4 note below).
7. **Safety-critical change rule:** any change under `src/contentguard/policy/**` or to
   a file named in `docs/architecture/invariants.md` requires: (a) an architecture
   decision (new/updated ADR), and (b) human review approval — machine-enforced through
   `.github/CODEOWNERS` (`/src/contentguard/policy/` lists the architecture owner) plus
   branch protection's `require_code_owner_reviews` (project sheet §6). Note that
   CODEOWNERS resolves **last-match**, so the broad `*` rule must stay first in that file.

## Enforcement status (2026-11-16)

| Rule | Enforced by | Status |
|---|---|---|
| 7 (policy/** needs architecture co-sign) | `.github/CODEOWNERS` + `require_code_owner_reviews` | **machine-enforced** |
| 1, 4, 5 (module mapping, authority boundaries, dependency direction) | review memos today; CI structural check | **TD-4, pending** |
| 6 (frozen / human-owned paths) | review memos; authorship is invisible to CI | review rule |
| lint / type / dependency hygiene | CI gate 2 | lint + type enforced; **dependency check pending (TD-8)** |

Once TD-4 lands, rules 1/4/5 become a CI job rather than a reviewer's memory — which is the
honest framing: today "structural constraints" are enforced by people reading this file.

