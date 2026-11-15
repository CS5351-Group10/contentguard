# Project Covenant (D3)

> Binding rules for the whole project (agents and humans). Human-owned; changes require
> a human commit reviewed by the PM.

## C1 — Abstraction limits

- No new abstraction (class hierarchy, framework, plugin system) beyond what an
  approved ADR introduces. If a change feels like it needs a new abstraction, stop and
  propose an ADR instead of building it.

## C2 — Dependency constraints

- Runtime dependencies are declared in `requirements.txt`/`pyproject.toml` only;
  no undeclared imports (CI dependency check).
- The analysis component depends on the LLM **API client** and nothing internal to
  `policy/` (authority boundary, INV-1).
- Deterministic tests must not require network, API keys, or model access (that is
  what `test/live/` is for).

## C3 — Test independence

- Every test runs in isolation: no ordering dependencies, no shared mutable state,
  no reliance on previous tests' side effects.
- **At least one negative test per feature**: for every feature, a test exists that
  demonstrates the system *rejecting* an invalid path (e.g., enforcement attempt
  outside the policy engine, malformed AI response, invariant-violating input).

## C4 — Safety-critical change rule

- Changing safety-critical code (anything enforcing an invariant:
  `src/contentguard/policy/**`, files named in `docs/architecture/invariants.md`)
  requires **both**: (a) an architecture decision (new/updated ADR), and
  (b) explicit human approval in review. Enforced by branch protection (sheet §6).

## C5 — Context freshness

- When requirements change (registry edit), the governance rules that reference them
  (`AGENTS.md`, structural/verification constraints, trace matrix, prompts) are
  updated **within one sprint** — checked at sprint-end governance review.
- Stale rules found later are recorded as human/cognitive debt in
  `docs/debt-register.md`.
