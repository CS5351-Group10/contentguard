# Architecture Blueprint (D2.1)

> **Status: DRAFT skeleton.** Sections are filled during the W12 architecture session
> using the ADD method (see course appendix: *Litmus Test & ADD guide*). The Plan agent
> treats every statement here as a binding constraint once marked APPROVED.

## 1. Scope

TBD — MVP boundary defined by `docs/req/requirements.yaml` MoSCoW; restate here once
the registry is baselined.

## 2. Architectural drivers

TBD — ASRs derived from the requirements registry (invariants, quality attributes,
performance, cost, governance, security).

## 3. System boundaries

TBD — external actors (content authors, moderators, policy admins), external systems
(LLM API), data in/out.

## 4. Components

TBD — one component per architectural element; module mapping in `AGENTS.md` §5.
Planned components: analysis (LLM advisory), policy engine (authoritative), escalation
(human queue), audit, API.

## 5. Authority boundaries (advisory vs authoritative)

TBD — the core safety boundary:
- **Advisory:** the LLM's verdict/severity/rationale — it may *influence* but never
  *execute* enforcement.
- **Authoritative:** the deterministic policy engine — the only component permitted to
  decide and execute enforcement actions (approve / hold / reject / escalate).
- Any conflict resolves toward the more restrictive action (fail-safe).

## 6. Agent workflow

TBD — how the OpenCode agent (plan → build → verify) interacts with this repository:
gates, approvals, and artifact ownership per `AGENTS.md` and `.opencode/permissions.jsonc`.

## 7. Permissions

TBD — summarized from `docs/architecture/permission-model.md` (file-level read/write
rights per agent role; default no read, no write).

## 8. Verification strategy

TBD — three-tier verification (structural / regression / behavioral) per
`docs/code-governance/verification-constraints.md`; semantic evaluation for the AI
component with a fixed evaluation set.

## 9. Observability

TBD — audit log design, metrics, decision traceability (input hash → AI verdict →
policy decision → action).

## 10. Change policy

TBD — how requirements/architecture changes propagate (registry → ADR → blueprint →
code within one sprint; see `.agent/rules.md` context freshness).

## 11. Layered context structure for the AI component (D2.2)

TBD — the context the moderation LLM receives on every call: identity, standing
constraints, retrieved policy knowledge, conversation/content history, resumable state,
current task; the assembly pipeline (deduplicate → prioritize → budget → compact →
assemble); the token-budget cap with compaction threshold; and the policy for
re-injecting critical constraints after compaction.
