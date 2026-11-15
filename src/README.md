# src/ — application source (D8)

**Currently empty by design** (pre-ADR-001). The first code lands only after the
architecture decision is human-approved (see `AGENTS.md` §3 and
`docs/architecture/adr/001-placeholder.md`).

Module naming rule (`docs/code-governance/structural-constraints.md` #1): module
names match architectural elements, one-to-one:

```
src/contentguard/
  analysis/     # AI (LLM) advisory moderation analysis
  policy/       # deterministic policy engine (SAFETY-CRITICAL — the only enforcement authority)
  escalation/   # human review queue routing
  audit/        # decision audit log
  api/          # service interface
```

Planned layout is a placeholder until ADR-001 fixes it.
