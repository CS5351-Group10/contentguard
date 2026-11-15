# Review Memos (D4) — one memo per pull request

> Each PR gets a memo covering: spec alignment, architecture alignment, code quality,
> test quality, operational metadata — security and efficiency checked throughout —
> ending in a verdict: **APPROVE / CHANGES REQUIRED / REJECT**.

## Review process (CR assignment system, team proposal §4.2, agreed 2026-11-15)

1. **Domain-assigned CR:** every PR is reviewed by the **non-author owner of the
   matching main line** — architecture PRs → architecture owner; test PRs → testing
   owner; governance/CI PRs → governance & CI owner; requirements PRs → requirements
   owner. (Not a rotation: the domain expert reviews, so review-memo content stays
   consistent with each deliverable line.)
2. **PM gate:** the PM provides the memo template, **signs off every memo**, and
   personally reviews critical PRs (invariants, architecture, anything touching D7
   gates or the contribution method).
3. **Safety-critical paths** (`src/contentguard/policy/**`, files named in
   `docs/architecture/invariants.md`): the **architecture owner co-signs** (D7
   hard requirement) **and** a linked architecture decision (ADR) is mandatory —
   branch protection enforces human review on these paths (§6).
4. PRs stay small (one feature/invariant slice); memos are written **before** merge.
5. Review turnaround target: 24 h. A PR waiting longer is escalated at the daily
   stand-up (risk RSK-3).

## Memo template (copy per PR)

```
## RM-<NNN> — PR #<n>: <title>

- Reviewer(s): domain CR <name>; PM <name>; architecture co-sign <name> (safety-critical only)
- Spec alignment: <requirement IDs touched; registry updated? MoSCoW respected?>
- Architecture alignment: <ADR/invariants conformance; authority boundaries respected?>
- Code quality: <naming, structure, module constraints 1-7>
- Test quality: <fit-criterion coverage; ≥1 negative test per feature; regression suite green>
- Security: <secrets, input validation, permission model>
- Efficiency: <cost/latency-relevant choices (tokens, calls, DB)>
- Operational metadata: <ai-use-log updated? transcript saved? debt/bug entries needed?>
- Verdict: APPROVE / CHANGES REQUIRED / REJECT
```

## PR & commit conventions (agreed 2026-11-15)

- **One logical change per PR** — a feature slice or a single deliverable chunk;
  small PRs keep memos meaningful.
- **Branch:** `<type>/<req-or-inv-id>-<slug>` (e.g. `feat/REQ-FUN-001-intake`).
- **PR title:** `<type>(<scope>): <subject>` — cite REQ/INV IDs in title or body;
  squash merge appends `(#<n>)`. Template: `.github/PULL_REQUEST_TEMPLATE.md`;
  test plans go through `.github/ISSUE_TEMPLATE/test-plan.md` issues (gate 1).
- **Merge method: squash only** (repo setting) — `main` becomes a curated ledger of
  one commit per reviewed change; granular agent-session commits stay visible on the
  PR page (D5 evidence). Consistent with the required linear history.
- **Contribution attribution (D6) rests on three anchors**, not on squash-commit
  authorship: (1) `docs/ai-use-log.yaml` `operator` + `pr` fields, (2) the PR body
  (authored by the member), (3) the man-hours table in `docs/contribution-log.md`.
  Authors merge their own PRs after approval — a responsibility discipline, not the
  attribution mechanism.
- **Prologue (history chapter 0):** the first 10 commits (the 2026-11-15 bootstrap
  cohort) were direct pushes while branch protection was being set up. They contain
  human-written docs/governance files (red-line compliant) **and** the human-drafted
  scaffold seed (CI workflow, `scripts/**`, `prompts/**`, test scaffolding incl.
  `test_smoke.py`, `pytest.ini`) written before the team adopted the agentic red
  line — tracked as **TD-3** in `docs/debt-register.md`, to be regenerated through
  OpenCode sessions. Two follow-up governance fixes also landed via admin windows
  (roster re-key; cross-session audit fixes) — recorded here as exceptions. From
  now on **every change lands via PR**; an exceptional admin window must carry an
  `[admin-window]` tag in the commit message **and** be recorded in the next review
  memo.

## Memos

<!-- Append memos below, newest last. -->

## RM-001 — PR #7: fix(ci): gate 1/4/6 PR-file fetch 401 (token plumbing) — TD-3, supports REQ-INV-005

- Reviewer(s): domain CR n/a (author IS the governance & CI owner); PM LIU Jianwei — critical-PR review per review process §2 (touches D7 gates); architecture co-sign n/a (not a safety-critical path)
- Spec alignment: no requirement change; supports REQ-INV-005 (auditable, verifiable process) — CI gates become reliably green so the audit trail works
- Architecture alignment: CI plumbing only; no module/ADR/invariant impact
- Code quality: root cause fixed (blank token produced a malformed `Authorization: Bearer ` header → 401); blank token now yields an anonymous request; gates fail closed with actionable diagnostics
- Test quality: new `test/offline/test_pr_files_headers.py` covers header construction incl. negative case; blocking-gates green on this branch
- Security: least-privilege workflow permissions (contents: read, pull-requests: read); token scoped to gates 1/4 via step env
- Efficiency: n/a (CI plumbing)
- Operational metadata: `docs/ai-use-log.yaml` updated in-PR (agent-session evidence, gate 6); TD-3 entry added to debt register
- Verdict: APPROVE

## RM-002 — PR #2: docs(governance): repo transferred to team org + public; update repo URL

> **Post-merge backfill (2026-11-16).** PR #2 was merged without a memo — an
> execution gap against "memos are written before merge" (review process §4),
> the exact hole **Gate 7 (issue #4)** exists to close. Recorded transparently
> as a case study rather than silently patched. Verdict source: creator-xiyuan's
> APPROVED review (2026-11-15T14:32:40Z); recorded by PM from that verdict
> (PM is also the PR author, so the domain verdict is the independent one).

- Reviewer(s): domain CR creator-xiyuan (governance & CI owner — APPROVED 2026-11-15); PM sign-off: this entry
- Spec alignment: no requirement change; governance records feeding D7 (repo transfer to team org, old-URL retirement, repo-scoped admin grant); MoSCoW unaffected
- Architecture alignment: no ADR/invariant impact; repository-level operations only
- Code quality: n/a (human-owned docs/governance files only — README repo section, contribution-log governance-events ledger, team index row)
- Test quality: docs-only; blocking-gates green after rebase onto post-#7 main (both check runs SUCCESS)
- Security: visibility private → public accepted by PM (roster student IDs readable — deliberate, documented); admin granted repo-scoped to @creator-xiyuan (least blast radius)
- Efficiency: n/a
- Operational metadata: governance-events ledger updated in-PR; no code/prompt change → no ai-use-log delta
- Verdict: APPROVE (post-merge ratification of the domain CR's verdict)
