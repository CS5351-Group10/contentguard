# src/ — application source (D8)

This directory is documentation plus the (eventually) application modules. ADR-001
(`docs/architecture/adr/001-grounded-advisory-transactional-policy.md`, approved
2026-11-16) fixes the layout below; module names match architectural elements one-to-one
(`docs/code-governance/structural-constraints.md` rule 1). Modules are added only as their
elements are implemented — this README is not a module and creates no directories.

```
src/contentguard/
  api/            # service interface: validate/authenticate, coordinate analysis → policy
  analysis/       # AI (LLM) advisory moderation analysis — advisory only
  policy/         # deterministic policy engine — AUTHORITATIVE (safety-critical)
  escalation/     # human review queue routing (mutations enlisted by policy)
  audit/          # append-only decision audit log
```

## Authority boundary (the one rule that matters)

- **`analysis/` is advisory.** It retrieves approved policy clauses, assembles bounded
  context and returns an advisory result (verdict `allow/review/violate`, severity,
  rationale, validated citations). It holds no DB write credentials, calls no enforcement
  API, and its output is data — never an executed action (INV-1 / REQ-INV-001).
- **`policy/` alone is authoritative.** Only the deterministic policy engine decides and
  executes consequential transitions (approve/hold/reject/escalate) under mandatory rules
  and fallbacks. It may consume the validated advisory result as read-only input but must
  not import analysis internals or delegate enforcement to model output.
- **`api/` coordinates; it does not decide.** It validates/authenticates, calls analysis,
  then calls policy, and maps responses. `escalation/` and `audit/` own their repositories
  but neither decides policy nor commits independently.

## Dependency direction

`api → {analysis, policy}` and `policy → {escalation, audit}`; no cycles. `analysis` must
not import `policy` internals. Integration contracts live in
`docs/architecture/interface-contracts.md`. The structural call-graph check that enforces
these boundaries is planned (TD-4) — until it lands they are enforced by review.
