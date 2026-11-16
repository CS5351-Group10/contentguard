# Submitting a PR (member guide)

Thin entry-point summary — the authoritative rules are `docs/review-memo.md`
(§Review process, §PR & commit conventions); this file only points to them.
Every change lands on `main` via PR (branch protection: 1 non-author approval
+ green `blocking-gates`; no direct pushes).

1. **Test plan first (code changes)** — gate 1: an approved test-plan issue
   must exist *before* implementation starts
   (`.github/ISSUE_TEMPLATE/test-plan.md`). Docs-only changes skip this.
2. **Branch & title** — branch `<type>/<req-or-inv-id>-<slug>`
   (e.g. `feat/REQ-FUN-001-intake`); with no applicable registry ID
   (docs/governance work) `<type>/<slug>` is accepted (e.g.
   `docs/rm-002-backfill`). PR title `<type>(<scope>): <subject>`, citing
   REQ/INV IDs when applicable.
3. **One logical change per PR** — small PRs keep review memos meaningful.
4. **Reviewer** — request the non-author owner of the matching main line
   (`docs/team/README.md`). While a line's owner is still onboarding (pending
   rows there), the PM (@swordnew123) reviews by default; governance/CI PRs →
   @creator-xiyuan. Safety-critical paths (`src/contentguard/policy/**`, files
   named in `docs/architecture/invariants.md`) additionally need the
   architecture owner's co-sign and a linked ADR.
5. **PR body** — use the template; docs-only PRs write `n/a (docs-only)` under
   gate 1 and `n/a (human-written docs)` under gate 6.
6. **Before merge** — the reviewer's memo lands in `docs/review-memo.md` (the
   PM records the verdict, inside this PR — not afterwards). Code/prompt PRs
   update `docs/ai-use-log.yaml` in the same PR (gate 6 blocks otherwise).
7. **Keep the PR current** — branch off latest `main`; when CI says the branch
   is behind, click **Update branch**. Review feedback: push fixes to the same
   branch — they join the same PR, no new PR needed. Push once, when done:
   every push dismisses stale approvals and forces a re-review.
8. **Merge** — after approval the author merges (squash only; the head branch
   auto-deletes). Turnaround target is 24 h; a PR waiting longer is escalated
   at the daily stand-up (RSK-3).
