# Structural Constraints (D3)

> Module organization rules the coding agent must obey. To be enforced by CI
> structural checks (**planned — TD-4**, not yet implemented) and review memos
> meanwhile.

1. **One-to-one mapping:** each architectural element maps to exactly one module, and the
   module name mirrors the element name. The **element set** is fixed by
   `architecture-blueprint.md` + ADR-001 — adding, renaming or splitting an element requires
   a new architecture decision, not a quiet new directory. No orphan modules: if an element
   is removed, its module goes with it. (The module tree in `AGENTS.md` §5 points at
   ADR-001 for the layout; that tree is a name sketch, not a licence to create directories
   ahead of the element.)
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
   without a human co-author is rejected in review; a code scan cannot see authorship, so this
   stays a review rule. Issue #66 plans a narrow guard for `.opencode/**` and `.agent/**` only —
   deliberately **not** `transcripts/**`, because human transcripts are committed legitimately
   (see the enforcement table below).
7. **Safety-critical change rule:** any change under `src/contentguard/policy/**` or to
   a file named in `docs/architecture/invariants.md` requires: (a) an architecture
   decision (new/updated ADR), and (b) human review approval — machine-enforced through
   `.github/CODEOWNERS` (`/src/contentguard/policy/` lists the architecture owner) plus
   branch protection's `require_code_owner_reviews` (project sheet §6). Note that
   CODEOWNERS resolves **last-match**, so the broad `*` rule must stay first in that file.

## Enforcement status (2026-11-19)

| Rule | Enforced by | Status |
|---|---|---|
| 7 (policy/** needs architecture co-sign) | `.github/CODEOWNERS` + `require_code_owner_reviews` | **machine-enforced** |
| 4 — the INV-1 half (enforcement reachable only from `policy/`) | `test/offline/test_invariants.py::test_enforcement_only_from_policy` (gate 5), proven on the `fixtures/forbidden_enforcement/` fixture by `test_forbidden_call_structural` | **machine-enforced (gate 5)** |
| 5 — the named prohibitions (`audit`/`escalation` → `policy`, `policy` → `analysis`) | `test/offline/test_invariants.py::test_dependency_direction` (gate 5) | **machine-enforced (gate 5)**; the `analysis` → `policy` edge and element-to-element cycles are **planned (issue #66)** |
| 1 (element↔module mapping) | review memos | **review only**; planned in issue #66 |
| 4 — the rest (authority boundary as a semantic property) | review memos | review only — a static check cannot decide "advisory vs authoritative" |
| 6 (frozen / human-owned paths) | review memos; authorship is invisible to a code scan | review rule; issue #66 plans a narrow `.opencode/**` + `.agent/**` guard only (not `transcripts/**`: human transcripts are committed legitimately) |
| lint / type / dependency hygiene | CI gate 2a/2b/2c | **machine-enforced** (`ruff`, `mypy`, `check_dependencies.py` against `requirements.txt`) |
| safety-path ADR/invariant reference | CI gate 2d (`check_safety_paths.py`) | **machine-enforced**, and only that tier: contract diffs, API-surface diffs and a structural call-graph check **do not exist** (the file itself says so) |

**Honest reading:** rules 4 (INV-1 half) and 5 (named prohibitions) are already machine-enforced by
gate 5, not "pending TD-4" as the earlier version of this table said. Rule 1 is still a reviewer's
memory; issue #66 (`Test plan: CI structural checks`) would close that plus the missing
`analysis → policy` edge, cycles and the narrow frozen-path guard. Everything not listed above
stays a review duty, and this table is the place to say so rather than implying a CI job covers it.


