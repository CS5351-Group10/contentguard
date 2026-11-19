# Submitting a PR (member guide)

Thin entry-point summary — the authoritative rules are `docs/review-memo.md`
(§Review process, §PR & commit conventions); this file points to them and records the
issue-lifecycle SOP (§Issue lifecycle).
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
   gate 1 and `n/a (no code/prompt change; note any AI-assisted drafting)` under gate 6.
6. **Before merge** — the reviewer's memo lands in `docs/review-memo.md` (the
   PM records the verdict, inside this PR — not afterwards). For a PM-authored PR
   the independent reviewer records the verdict and the PM countersigns **when the
   ledger entry is appended**; if the PM cannot countersign, the RM entry says so
   explicitly (`countersign pending` or `countersign absent`) **with the reason** —
   an unsigned memo must never be indistinguishable from a signed one.
   Code/prompt PRs update `docs/ai-use-log.yaml` in the same PR (gate 6 blocks
   otherwise).
7. **Keep the PR current** — branch off latest `main`; when CI says the branch
   is behind, click **Update branch**. Review feedback: push fixes to the same
   branch — they join the same PR, no new PR needed. Push once, when done:
   every push dismisses stale approvals and forces a re-review.
8. **Merge** — the **author** merges once (a) a non-author approval from a
   matching CODEOWNER stands, (b) `blocking-gates` is green, and (c) the review
   verdict is recorded in the PR (step 6). Squash only; the head branch
   auto-deletes. The PM is the memo gate, not a merge gate. Turnaround target is
   24 h; a PR waiting longer is escalated at the daily stand-up (RSK-3).

## Issue lifecycle (handoff / decision / test plan / deferred / completed)

Issues are the audit trail for role handoffs, decisions, and gate 1 test plans. One issue
per work item. Append new information as comments; do not edit or delete past comments.
When closing, update the body's status/approval fields (or add a top status block) so the
current state is visible.

- **Handoff** (`handoff` label): close only when every checklist item is done and the
  linked PRs are merged. The closing comment names the PRs/commits and any follow-up.
- **Decision** (`decision` label): keep open through the stated objection window; close
  with the accepted outcome and a link to the deciding comment. Reopen on objection.
- **Test plan** (`test-plan` label, gate 1): close only when the implementing PR is merged
  and the planned tests exist. The closing comment links the PR and the test path.
  A `deferred` issue keeps this rule suspended until the deferral is lifted.
- **Deferred** (`deferred` label): keep open with a link to the debt-register row, or close
  as `NOT_PLANNED` with the same link. Never leave the status implicit.
- **Completed/closed issue**: add a `## Resolution` section (what changed, evidence,
  follow-ups) and close with the correct reason (`COMPLETED` / `NOT_PLANNED` / `DUPLICATE`).
  Closed issues are retained as audit evidence (D4 review memos, D6 process-report inputs)
  — never delete them.
- **PR memos**: every PR still needs an RM memo before merge. A docs-only PR may carry the
  memo as a reviewer/PM comment; the `docs/review-memo.md` ledger append follows in the next
  docs PR (or the same PR if it already edits that file).
- **Body hygiene**: if the original request or approval line is stale, update the body (or
  add a top status block) before closing; do not rely on a comment alone.

Every active issue has an assignee and one of the labels above. The PM and the Governance &
CI owner maintain the label set; domain owners keep their issues current. Recent examples:
#6 (closed test plan with a `## Resolution` section), #4 (deferred gate 7, linked to TD-9),
#23 (decision with an explicit objection window).
