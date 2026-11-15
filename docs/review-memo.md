# Review Memos (D4) — one memo per pull request

> Each PR gets a memo covering: spec alignment, architecture alignment, code quality,
> test quality, operational metadata — security and efficiency checked throughout —
> ending in a verdict: **APPROVE / CHANGES REQUIRED / REJECT**.

## Review process (team agreement, 2026-11-15)

1. **Tier 1 — peer review (rotating):** every PR is assigned one peer reviewer
   (rotation roster maintained by the PM). Focus: code/test quality, spec fit details.
2. **Tier 2 — PM final gate:** the PM reviews **every** PR before merge: spec
   alignment, architecture alignment, invariants, and signs the verdict. Safety-critical
   paths (`src/contentguard/policy/**`, invariant-named files) are PM-reviewed **and**
   require a linked architecture decision (ADR) — per project sheet §6 branch protection.
3. PRs stay small (one feature/invariant slice); memos are written **before** merge.
4. Review turnaround target: 24 h. A PR waiting longer is escalated at the daily
   stand-up (risk RSK-3).

## Memo template (copy per PR)

```
## RM-<NNN> — PR #<n>: <title>

- Reviewer(s): peer <name>; PM <name>
- Spec alignment: <requirement IDs touched; registry updated? MoSCoW respected?>
- Architecture alignment: <ADR/invariants conformance; authority boundaries respected?>
- Code quality: <naming, structure, module constraints 1-7>
- Test quality: <fit-criterion coverage; ≥1 negative test per feature; regression suite green>
- Security: <secrets, input validation, permission model>
- Efficiency: <cost/latency-relevant choices (tokens, calls, DB)>
- Operational metadata: <ai-use-log updated? transcript saved? debt/bug entries needed?>
- Verdict: APPROVE / CHANGES REQUIRED / REJECT
```

## Memos

<!-- Append memos below, newest last. -->
