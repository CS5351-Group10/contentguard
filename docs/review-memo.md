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
6. **An approval is a judgement, not a click.** Review from your own main-line role:
   state what you actually checked and whether the change is *right*, not merely that it
   exists. If it is wrong or incomplete, do not approve — record the concrete problems and
   return CHANGES REQUIRED. A verdict with no check behind it is noise, and a four-minute
   bare approve is treated as no review at all. What each role is expected to check:
   - **Requirements owner:** requirement IDs, fit criteria, priority (MoSCoW) correctness,
     traceability from each requirement to a component/test.
   - **Architecture owner:** ADR conformance, module/authority boundaries, layered context
     structure, token budget and compaction thresholds.
   - **Testing owner:** negative test per invariant, threshold/eligibility of the gates,
     offline-vs-live separation.
   - **Governance & CI owner:** that the document's claims match machine behaviour —
     branch protection, CODEOWNERS resolution, gate semantics — and that red-line
     boundaries (agent-generated code, human-owned files) are respected.
   - **PM:** spec alignment, cross-artifact consistency, and the contribution/process
     record.

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

> RM-N = the Nth memo in this ledger. RM-001..RM-004 follow the intended PR
> sequence; RM-005 onward follow the 2026-11-16 finalization note below (posted
> labels where unique, ledger renumbering where they collided). RM-002/RM-003
> were backfilled by PR #9 after RM-004 was drafted in PR #8; they are placed
> before RM-004 so the early ledger reads in PR order. A dismissed "RM-003"
> review draft on PR #5 predates this ledger's RM-003 and is void.
>
> **2026-11-16 ledger finalization note (supersedes the ordering rule above for
> RM-005 onward).** Reviewers posted memos in PR threads faster than the ledger could
> be appended, and their provisional labels collided. From RM-005 onward the ledger
> number matches the reviewer's posted label where that label is unique; where it
> collided, the ledger number below is authoritative. Full mapping:
> - PR #5's draft said RM-007 → ledger **RM-010**.
> - PR #10's draft said RM-005 → ledger **RM-011**.
> - PR #8 also carries a dismissed RM-007 review on old commit `6529e42`; its binding
>   memo is **RM-004** on the merged head (`12d4936`).
> - PR #13 (RM-008), PR #14 (RM-009), PR #17 (RM-005), PR #16 (RM-006) and PR #29
>   (RM-007) keep their posted numbers.
> - PR #15 was approved and merged after this append (squash `8747723`); its memo is
>   **RM-013** below, added in the 2026-11-16 backfill. PR #11 remains unnumbered
>   until its final head is re-reviewed and merged; its current verdict is CHANGES
>   REQUIRED and is not a final memo.
>
> **2026-11-19 ledger backfill note (RM-015–RM-032).** This backfill fills the gap
> left by the post-#39 review burst. The rule is the same as 2026-11-16: the ledger
> number matches the reviewer's posted label where that label is unique; where
> labels collided, the ledger number below is authoritative. Mapping:
> - RM-015 #32; RM-016 #34; RM-017 #37 final (the author-side timing record
>   originally in this slot is folded into the same entry); RM-018 #33;
>   RM-019 #39 (the governance/CI review posted as RM-018 is folded in);
>   RM-020 #35; RM-021 #44; RM-022 #46 governance/CI.
> - RM-023 #11 (posted RM-019; #39's PM memo is earlier); RM-024 #41
>   (posted RM-020; #35 is earlier); RM-025 #41 architecture co-sign (Li);
>   RM-026 #46 architecture co-sign (Li); RM-027 #47 final (the provisional
>   RM-024 on #47 is superseded and void, following the RM-003 void-draft
>   precedent); RM-028 #45; RM-029 #53; RM-030 #54.
> - RM-031 #40 (posted RM-025; #41's Li memo is earlier); RM-032 #59
>   (posted RM-020; #35 is earlier).
> - RM-033 is reserved for PR #62's final memo after its pending test fixes and
>   re-review; the posted RM-021 changes-requested reviews (on `1ff2050`,
>   re-issued on `8111850`) are superseded and not a final memo.
>   RM-034/RM-035 are the provisional labels for the PM's #57/#61 reviews
>   (final ledger entries after approval).
> - #47's provisional RM-024 is void; #37's draft RM-015 is superseded by
>   RM-017.

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

## RM-003 — PR #9: docs(review-memo): RM-002 post-merge backfill for PR #2

- Reviewer(s): domain CR creator-xiyuan (governance & CI owner); PM authored this PR, so the domain verdict is the independent one (recorded by PM from the CR's approve on this PR)
- Spec alignment: no requirement change; closes the PR #2 memo-gap audit item (RM-002 post-merge backfill; enforcement path → Gate 7, issue #4)
- Architecture alignment: n/a (ledger append only)
- Code quality: n/a (docs)
- Test quality: docs-only; blocking-gates green on this branch
- Security: n/a
- Efficiency: n/a
- Operational metadata: governance-events row for the incident added in this PR (contribution-log.md)
- Verdict: APPROVE

## RM-004 — PR #8: docs(contribution-log): per-phase man-hours recording protocol (D6 evidence chain)

- Reviewer(s): domain CR creator-xiyuan (governance & CI owner); PM authored the PR, so the domain verdict is the independent one (recorded by PM from the CR's approve on this PR)
- Spec alignment: no requirement change; operationalizes the D6 recording method (per-phase cadence, same-day capture, hours-only, pre-agreed what-counts) — feeds `Report.md` §2 contribution weights
- Architecture alignment: n/a (docs only; no module/ADR/invariant impact)
- Code quality: n/a (docs)
- Test quality: docs-only; blocking-gates green (both check runs SUCCESS on this head)
- Security: n/a
- Efficiency: n/a
- Operational metadata: man-hours table re-keyed (Phase column, story points dropped); protocol set before the first logged entry — no historical hours rewritten
- Verdict: APPROVE

## RM-005 — PR #17: docs(governance): phase-2 close records (bug diary, AI-use-log, debt register, roster)

- Reviewer(s): domain CR creator-xiyuan (governance & CI owner); PM LIU Jianwei authored the PR, so this review is the independent verdict
- Spec alignment: no registry change; records D4/D6 evidence — bug-diary BUG-001/BUG-002, debt register TD-1..TD-9 with owners and pay-down dates, Report §1 roster and §2 hours skeleton, and the `docs/team/README.md` index
- Architecture alignment: n/a (governance/docs)
- Code quality: n/a (docs)
- Test quality: docs-only; `blocking-gates` green on `311dcd7`; final head `ce88b3d` (main merge + this ledger append) re-approved by the reviewer before squash merge
- Security: n/a
- Efficiency: n/a
- Operational metadata: BUG-002's "Fixed in: PR #11 (pending)" is correct at memo time; update when #11 lands
- Oversight case: yes — reviewer independently reproduced BUG-001's 401 path (`Authorization: Bearer ` with a blank token; only gate 6 was wired to `GITHUB_TOKEN`, gate 1 died with a 401 and gates 4/6 never ran. Reviewer also checked that TD-3 is honestly `partial`, verified TD-1..TD-4 dates and TD-9's gate-7 deferral, and confirmed AI-001 `pr: 7` matches PR #7's squash commit `9cd38f7`
- Verdict: APPROVE

## RM-006 — PR #16: docs(architecture): complete D2 support artifacts for Phase 2

- Reviewer(s): domain CR creator-xiyuan (governance & CI; cross-domain review — the PR includes D4/D6 evaluation, risk and option ledgers); architecture owner path approval @xiaolizi33 is required by `/docs/architecture/` and is recorded separately when granted
- Spec alignment: fills D2.5 memory, D2.7 runtime policy, D2.8 evaluation table, D2.9 logbook, D2.10 risk list, D2.11 option ledger; no registry change
- Architecture alignment: design judgment explicitly distinguished from benchmark evidence; S4/S5 logbook rows marked Planned, not evidence; retention/access values marked pending ratification
- Code quality: n/a (docs)
- Test quality: n/a (docs); evaluation arithmetic recomputed. Review head `d6f4c7c`; final head `8e9509d` adds the ADR/contracts link fix and awaits @xiaolizi33's path approval — not yet merged at ledger time
- Security: n/a
- Efficiency: n/a
- Operational metadata: review hours 0.5h (11/16 18:40–19:10); future D3 edits to `docs/code-governance/mcp-tool-manifest.md` route through the governance & CI owner
- Oversight case: yes — reviewer recomputed the weighted scores (C1 5.00, C2 3.25, C3 4.00) rather than trusting the totals, and flagged the cross-PR references to interface-contracts/PR #15 for re-check when #15 lands
- Verdict: APPROVE

## RM-007 — PR #29: docs(governance): add issue-lifecycle SOP to the member guide

- Reviewer(s): domain CR creator-xiyuan (governance & CI owner); PM LIU Jianwei authored the PR, so this review is the independent verdict
- Spec alignment: no registry change; documents handoff/decision/test-plan/deferred/closed issue discipline, close reasons, never-delete-closed rule, and the Resolution section
- Architecture alignment: n/a
- Code quality: n/a (docs)
- Test quality: docs-only; `blocking-gates` green on `2973770`; final head `602330c` after update-branch, approval preserved, merged
- Security: n/a
- Efficiency: n/a
- Operational metadata: docs-only gate-6 wording moves to "n/a (no code/prompt change; note any AI-assisted drafting)" — an honest relaxation; review hours 0.3h (11/16 19:10–19:30)
- Oversight case: yes — reviewer flagged the gate-6 wording change explicitly (docs-only PRs may now disclose AI-assisted drafting) and confirmed the PR deliberately avoids `docs/review-memo.md` to stay clear of the #8 collision
- Verdict: APPROVE

## RM-008 — PR #13: roster: add 60368210

- Reviewer(s): PM LIU Jianwei (roster/D6 domain; non-author)
- Spec alignment: card follows `docs/team/_TEMPLATE.md` (name, student ID, GitHub, main line Governance & CI); feeds `Report.md` §1
- Architecture alignment: n/a
- Code quality: n/a
- Test quality: docs-only; `blocking-gates` green
- Security: student ID public by the PM decision of 2026-11-15; no secrets
- Efficiency: n/a
- Operational metadata: index update deferred to the PM per the roster design
- Oversight case: no (routine roster card); template conformance and public-ID decision checked
- Verdict: APPROVE

## RM-009 — PR #14: docs(d5): archive annotated governance-CI session transcript (60368210)

- Reviewer(s): PM LIU Jianwei (D5/D6 evidence; non-author)
- Spec alignment: D5 transcript for the governance/CI line; covers plan approval, build, and verification of the CI 401 fix (PR #7); 874 lines with 3 annotated interventions (approve-with-corrections, accidental interruption, scope guard) and rationale
- Architecture alignment: n/a; the transcript shows the least-privilege decision and the gate-name/scope constraints
- Code quality: n/a
- Test quality: references the new `test_pr_files_headers.py` and the gate runs
- Security: sanitized — only example `Bearer ` / `Bearer xxx` strings; no real token; working-directory paths present (acceptable, could be redacted)
- Efficiency: n/a
- Operational metadata: `docs/ai-use-log.yaml` AI-001 exists (`pr: 7`); filename matches the D5 convention. Non-blocking follow-up: the transcript omits tool outputs ("condensed for size") and uses a table rather than inline `>>> [INTERVENTION]` markers; add the full raw export (or a documented excerpt policy) and inline markers before the 11/21 lock
- Oversight case: yes — the operator rejected job-level token hoisting (least privilege) and required ID-citing test docstrings; the D5 follow-up (full export/inline markers) is separately recorded above
- Verdict: APPROVE (with the D5 follow-up above)

## RM-010 — PR #5: roster: add 60938585

- Reviewer(s): PM LIU Jianwei (roster/D6 domain; non-author)
- Spec alignment: roster card follows `docs/team/_TEMPLATE.md` (name + student ID, GitHub, main line Architecture); name now matches the Canvas registration (Shiyi LI); file is `docs/team/60938585-LI-Shiyi.md`; feeds `Report.md` §1
- Architecture alignment: n/a
- Code quality: n/a
- Test quality: docs-only; `blocking-gates` green after updating the branch to current `main`
- Security: student ID public by the PM decision of 2026-11-15; no secrets
- Efficiency: n/a
- Operational metadata: index update deferred; no ai-use-log needed (human docs)
- Oversight case: yes — the PM caught the filename/name mismatch and withdrew an incorrect index-row instruction that would have violated the roster design ("nobody edits the same file"; the PM maintains the index)
- Verdict: APPROVE

## RM-011 — PR #10: docs(governance): member PR entry guide + reviewer docs match machine reality

- Reviewer(s): domain CR creator-xiyuan (governance & CI owner); PM LIU Jianwei authored the PR, so this review is the independent verdict
- Spec alignment: adds `.github/CONTRIBUTING.md` (thin member guide), registers it as human-owned in `AGENTS.md` §4, aligns CODEOWNERS comments/PR template with what branch protection actually enforces, links the guide from README; supports D3/D7
- Architecture alignment: n/a
- Code quality: n/a
- Test quality: docs-only; `blocking-gates` green
- Security: no secrets; no permission changes
- Efficiency: reduces review ambiguity
- Operational metadata: docs-only; no ai-use-log required
- Oversight case: yes — reviewer verified the CODEOWNERS/AGENTS/PR-template claims against the actual branch protection (`required_approving_review_count: 1`, `require_code_owner_reviews: false` at that time) and flagged a non-blocking step-8 wording inconsistency (author merges vs reviewer gate)
- Verdict: APPROVE

## RM-012 — PR #30: chore(governance): per-domain CODEOWNERS rules (two owners each, no self-approval deadlock)

- Reviewer(s): PM LIU Jianwei (non-author); author creator-xiyuan
- Spec alignment: replaces the single `* @swordnew123` rule with per-domain owners (`*`, `/docs/req/`, `/docs/architecture/`, `/src/contentguard/policy/`, `/.github/workflows/`, `/scripts/`), each with a domain owner plus one fallback; supplies the rule set for the `require_code_owner_reviews` branch protection that was already enabled on `main`. No requirement change.
- Architecture alignment: matches the review process §1 domain split and the D7 safety-critical path; the file documents that CODEOWNERS resolves a file's owners by the last matching pattern, so the broad default rule stays first.
- Code quality: n/a (config)
- Test quality: n/a (config); `blocking-gates` green on `3373e3`
- Security: least-privilege review ownership; no permission grant beyond the existing collaborators
- Efficiency: n/a
- Operational metadata: the root D2.1/D9 artifacts (`/architecture-blueprint.md`, `/Prompt.md`) were missing from the first head and were added after PM review. Merged at `d5ec877`.
- Oversight case: yes — PM caught the two missing root patterns (issue #21's recommendation explicitly listed `architecture-blueprint.md`) and requested the two-line fix; the author added them and corrected the last-match wording.
- Verdict: APPROVE

## RM-013 — PR #15: docs(architecture): propose ADR-001, blueprint and module contracts

- Reviewer(s): PM LIU Jianwei (non-author); author LI Shiyi; requirements/testing co-signs pending
- Spec alignment: ADR-001 chooses the modular monolith with grounded advisory analysis and transactional policy authority; the blueprint restores the D2.1 system-boundaries, agent-workflow, permissions and verification-strategy sections; interface contracts define the module operations; the ADD process is documented. No registry change.
- Architecture alignment: advisory/authoritative split, policy authority, RAG grounding, layered context, compaction/reinjection, fail-safe fallbacks, and INV-1..5 alignment verified against the blueprint.
- Code quality: n/a (docs)
- Test quality: n/a (docs); the acceptance-test list is handed to the test plans
- Security: untrusted submitted/retrieved text, citation validation, no provider tools, server-authenticated moderator identity
- Efficiency: 8,192 envelope / 6,144 input / 4,608 compaction / 20 s per-call cap; 20 s is a hard cap, not REQ-PER-001's p95; REQ-COS-001 provisional/not-claimed
- Operational metadata: PM approved on 2026-11-16 with requirements/testing co-signs recorded as pending; PM updated the ADR/blueprint/contracts status lines at merge time because the author was unavailable, leaving the substantive content unchanged. Merged at `8747723`.
- Oversight case: yes — PM verified items 1–9 of the `5683ac7` re-review, refused to approve while the ADR still said PROPOSED, and required the pending co-signs to be recorded rather than claimed complete.
- Verdict: APPROVE (with requirements/testing co-signs pending)

## RM-014 — PR #31: docs(review-memo): rule 6 — an approval is a judgement, not a click

- Reviewer(s): PM LIU Jianwei (non-author); author creator-xiyuan
- Spec alignment: adds rule 6 to the review process: state what was checked; do not approve incomplete work; per-role check surface for requirements/architecture/testing/governance/PM. No requirement change.
- Architecture alignment: n/a (process docs)
- Code quality: n/a (docs)
- Test quality: docs-only; `blocking-gates` green on `d0768b9`
- Security: n/a
- Efficiency: n/a
- Operational metadata: merged at `3bda2ed`; the rule applies to future memos and the `Oversight case:` line is now the norm.
- Oversight case: yes — PM checked the diff scope (only `docs/review-memo.md` §Review process), confirmed the rule matches the cited PR #2 incident, and verified the existing RM ledger/numbering note was untouched.
- Verdict: APPROVE

## RM-015 — PR #32: docs(governance): align AGENTS §5 and structural rule 5 with ADR-001

- Reviewer(s): domain CR creator-xiyuan (governance & CI)
- Spec alignment: docs-only; `AGENTS.md` §5 and structural rule 5 aligned with ADR-001; no registry change
- Architecture alignment: the new pointers resolve; the section-ref fix is right; dependency direction matches `architecture-blueprint.md` L126–127
- Code quality: n/a (docs)
- Test quality: docs-only; the gate claim holds — files touched are `AGENTS.md` and `docs/code-governance/**`, neither on a gate path
- Security / Efficiency: n/a
- Operational metadata: merged at `5846363`; posted memo 2026-11-16T15:36:47Z
- Verdict: APPROVE

## RM-016 — PR #34: docs(governance): backfill post-merge RM memos and fix section refs

- Reviewer(s): domain CR creator-xiyuan (governance & CI)
- Spec alignment: ledger backfill; numbering checked against `main` (RM-012 #30, RM-013 #15, RM-014 #31) and the §1/§2 split of `Report.md`
- Architecture alignment: n/a (docs)
- Code quality: n/a
- Test quality: docs-only
- Security / Efficiency: n/a
- Operational metadata: merge SHAs verified — `d5ec877` #30, `8747723` #15, `3bda2ed` #31; merged at `e3e88cd`; posted memo 2026-11-16T15:36:49Z
- Oversight case: yes — reviewer audited the ledger against commits, branch protection and `Report.md`, and flagged the RM-009 rewrite and RM-006 note for correction
- Verdict: APPROVE

## RM-017 — PR #37: test(eval): add fixed moderation evaluation corpus

- Reviewer(s): PM LIU Jianwei @swordnew123 (the testing owner is the author, so the PM reviews); governance/CI sign-off by @creator-xiyuan at `826dcfd`
- Head reviewed: `826dcfdb35014b44aa1b63aa8fc68ac9fadea85b`
- Spec alignment: corpus is 100 records (80 Jigsaw / 20 COLD), seed `5351`, native label schemes preserved (no cross-scheme mapping), no source row IDs; committed file 75,817 bytes with SHA-256 `37a1135e…8ed1`
- Architecture alignment: fixed evaluation set is INV-5 evidence; the PR supplies the corpus only and does not enable strict gate 4 (strict is #57/TD-1); the ADR addendum is #46
- Code quality: no `src/` change; 10 files, corpus/docs/tests/transcripts only
- Test quality: data-contract tests cover PII negatives, README/NOTICE assertions, digest checks and fallback; **204 passed** at `826dcfd`
- Security: PII sweep re-run at this head — IPv4, email, `@handle`, `User:` forms: 0 hits; NOTICE records Jigsaw CC0 1.0 / Wikipedia CC BY-SA 3.0 / COLD Apache-2.0 with source URLs and retrieval evidence
- Efficiency: n/a
- Operational metadata: `AI-003` and `AI-004` entries plus transcripts are present; gate 6 green. Timing deviation: first implementation commit `0c742340` (2026-11-16 19:55:02Z) preceded PM conditional approval by **7h26m** and governance/CI co-approval by **9h44m**; recorded as a process deviation, not waived. Draft-state toggle did not take effect; the standing CHANGES_REQUESTED held the merge until re-review. Merge landed after the 09:00 HKT target; the #49 triage must record the actual time rather than moving it silently.
- Oversight case: yes — reviewer independently re-checked corpus shape, PII, licensing, AI-use evidence and the 204-test result at the final head
- Verdict: APPROVE; merged at `539ae7cf` (2026-11-19 12:48 HKT)

## RM-018 — PR #33: docs(governance): align verification & structural constraints with CI reality (TD-1/2/4/8)

- Reviewer(s): PM LIU Jianwei (non-author; governance/CI owner is the author)
- Spec alignment: D4 verification governance and D7 blocking-gate truthfulness; docs-only — no `src/`, `test/`, `prompts/`, `scripts/` or workflow change
- Architecture alignment: enforcement-status table correctly marks rule 7 machine-enforced via CODEOWNERS, rules 1/4/5 TD-4 pending, rule 6 review-only, dependency check TD-8 pending
- Code quality: n/a (docs)
- Test quality: docs-only; `blocking-gates` green on `57c9efc`; branch rebased onto `5846363`
- Security / Efficiency: n/a
- Operational metadata: merged at `1d23218`; posted memo 2026-11-17T05:55:24Z
- Verdict: APPROVE

## RM-019 — PR #39: docs(governance): author merges after review verdict

- Reviewer(s): domain CR creator-xiyuan (governance & CI; posted RM-018, folded here because #33's memo posted RM-018 earlier); PM LIU Jianwei (PR-comment memo, posted RM-019)
- Spec alignment: moves the team from "PM merges" to "author merges after a non-author approval, green `blocking-gates` and a recorded verdict"; no requirement change
- Architecture alignment: n/a (process docs)
- Code quality: n/a
- Test quality: docs-only; CI green
- Security: reviewer verified `enforce_admins: true` — "no push restrictions" does not mean admin direct push
- Efficiency: n/a
- Operational metadata: records the push-after-approval incident (second commit 7 seconds after approval dismissed it; head reset and re-approved); merged at `ab57937`
- Oversight case: yes — the failure mode was tested by a real incident, not only asserted
- Verdict: APPROVE

## RM-020 — PR #35: roster: add 60105888

- Reviewer(s): PM LIU Jianwei (non-author; docs-only roster change)
- Spec alignment: adds Buna DA (60105888) to the roster that feeds `Report.md` §1 and D6; card matches `docs/team/_TEMPLATE.md` and the naming convention
- Architecture / Code quality: n/a (docs)
- Test quality: docs-only; `blocking-gates` green
- Security: student ID + GitHub handle are the roster's required fields (repo public by decision); no email or other PII
- Efficiency: n/a
- Operational metadata: PR body placeholders replaced with `n/a`; `docs/team/README.md` index update deferred to the next roster batch; merged at `8bb799a`
- Oversight case: no (routine roster card); template conformance and public-ID decision checked
- Verdict: APPROVE

## RM-021 — PR #44: docs(report): draft process report sections 3–6 (D6)

- Reviewer(s): domain CR creator-xiyuan (governance & CI)
- Spec alignment: D6 report sections 3–6; no registry change
- Architecture / Code quality: n/a (docs)
- Test quality: docs-only; the posted memo verified the 121-test figure and the gate-status claims
- Security / Efficiency: n/a
- Operational metadata: merged at `a74ff70`; posted memo 2026-11-18T04:28:22Z (re-issued 06:56:12Z)
- Verdict: APPROVE

## RM-022 — PR #46: docs(architecture): record ADR-001 addendum for corpus maintenance

- Reviewer(s): domain CR creator-xiyuan (governance & CI)
- Spec alignment: ADR-001 addendum for corpus maintenance; the ≥100 condition matches the verification constraints; the 95-record fallback is recorded
- Architecture alignment: the addendum does not overclaim — it does not close TD-1 or establish a blocking replay; the AI-004/AI-003 split and raw-path restriction match the #37 ruling
- Code quality / Test quality: n/a (docs)
- Security / Efficiency: n/a
- Operational metadata: merged at `7b0ee1e`; posted memo 2026-11-18T04:28:24Z
- Verdict: APPROVE

## RM-023 — PR #11: feat(req): baseline requirements registry v1.0 + validator gate-3 check

- Reviewer(s): domain CR creator-xiyuan (code-owner review; posted RM-019 — renumbered because #39's PM memo posted RM-019 earlier)
- Spec alignment: requirements registry v1.0 + gate-3 validator; all 31 requirements valid
- Architecture alignment: registry IDs and fit criteria match the D2 trace matrix; REQ-GOV-003 fit criterion rewritten during review
- Code quality: validator and gate-3 script reviewed; no unresolved blocking issue
- Test quality: reviewer ran gate 3 and the offline suite at the final head; three non-blocking records
- Security / Efficiency: no secrets; no runtime path
- Operational metadata: merged at `25ddd8a` (2026-11-18); the ledger now assigns RM-023, and the Report's earlier "intentionally not pre-numbered" sentence is refreshed in the follow-up docs pass (PR #63 / next Report pass)
- Oversight case: yes — reviewer ran the checks instead of trusting the PR body, and recorded a schema misread
- Verdict: APPROVE

## RM-024 — PR #41: feat(policy): S1 deterministic policy kernel + audit subsystem (#25)

- Reviewer(s): domain CR creator-xiyuan (governance & CI; posted RM-020 — renumbered because #35's memo posted RM-020 earlier)
- Spec alignment: S1 policy kernel + audit; safety-critical path (`src/contentguard/policy/**`)
- Architecture alignment: ADR-001 / invariants; architecture co-sign is RM-025 (Li)
- Code quality: deterministic policy kernel, atomic SQLite transaction, exactly one audit record per committed decision
- Test quality: reviewer ran the 121-test suite and verified the ten planned cases
- Security: authority token is a module-private opaque object; forged-advisory and authority-binding tests
- Efficiency: n/a
- Operational metadata: merged at `e60dd50`; posted memo 2026-11-18T04:28:21Z
- Verdict: APPROVE

## RM-025 — PR #41: Architecture co-sign: S1 policy kernel + audit

- Reviewer(s): xiaolizi33 (architecture owner; safety-critical co-sign)
- Spec alignment: ADR-001 conformance and authority boundaries for `src/contentguard/policy/**`
- Architecture alignment: co-sign required by D7; no architecture change in this review
- Code quality / Test quality / Security / Efficiency: covered by RM-024; this memo records the mandatory architecture co-sign
- Operational metadata: merged at `e60dd50`; posted memo 2026-11-18T06:30:15Z
- Verdict: APPROVE

## RM-026 — PR #46: Architecture review: ADR-001 corpus-maintenance addendum

- Reviewer(s): xiaolizi33 (architecture owner)
- Spec alignment: ADR-001 corpus-maintenance addendum; architecture review of the corpus version/hash/seed/raw-path binding
- Architecture alignment: addendum is an ADR-001 extension, not a new architecture decision
- Code quality / Test quality / Security / Efficiency: n/a (docs)
- Operational metadata: merged at `7b0ee1e`; posted memo 2026-11-18T06:30:17Z
- Verdict: APPROVE

## RM-027 — PR #47: gate 4 semantic-evaluation replay harness (warn-only)

- Reviewer(s): PM LIU Jianwei (non-author)
- Spec alignment: TD-1 / REQ-INV-005 harness, warn-only scope; not a claim that gate 4 blocks yet
- Architecture alignment: replay-only, no provider secret; policy first-match and uncovered-row hard failure preserved
- Code quality: A1 verified — `load_policy` rejects uppercase `HIGH`/`BLOCK`, unknown/empty `when` keys, duplicate/blank rule ids and YAML errors; seven `test_load_policy_rejects_*` negatives. A2 verified — a prompt PR that also changes `expectation_policy.yaml` or `moderation_eval.jsonl` fails even without `--strict`; three tests cover it
- Test quality: CI green; cheap items verified (`--replay=PATH` / bare-flag exit 2, `EVAL_REPLAY` cleanup, false-block N/A, AI-009 count 19)
- Security: no provider secret; replay-only
- Efficiency: n/a
- Operational metadata: gate 6 entry AI-009; gate 1 cites #26; merged at `1f7f20c`
- Oversight case: yes — reviewer ran both suites, the good/bad/no-replay/quality demos and the policy-typo negative
- Verdict: APPROVE (warn-only merge scope; #47's provisional RM-024 is superseded by this final memo)

## RM-028 — PR #45: TD-3 scaffold regeneration + gate 2 dependency/safety tier

- Reviewer(s): PM LIU Jianwei (non-author)
- Spec alignment: TD-3 scaffold regeneration and gate 2 dependency/safety tier; no requirement change
- Architecture alignment: scaffold-regeneration provenance recorded; no module/ADR change
- Code quality: P1① verified — `requirements.txt` ranges span the observed toolchains (pytest 8.4.2–9.2.0, mypy 1.20.2–2.4.1); CI installs from the manifest
- Test quality: P1② verified — gate 2d documents the gate-5 substitution for the policy-test half of #42 and adds a visibility test; scoped policy-test step remains a TD-4 follow-up after #41
- Security / Efficiency: n/a
- Operational metadata: merged at `b2e67f1`; posted memo 2026-11-18T11:02:03Z
- Verdict: APPROVE

## RM-029 — PR #53: docs(transcripts): inline D5 stage-3/4 intervention markers (PM transcript)

- Reviewer(s): domain CR creator-xiyuan (governance & CI)
- Spec alignment: D5 transcript evidence for the PM transcript; additive-only marker insertion
- Architecture / Code quality: n/a (docs)
- Test quality: docs-only; convention check and marker-rationale spot-check
- Security / Efficiency: n/a
- Operational metadata: merged at `621b076`; posted memo 2026-11-19T04:39:09Z
- Verdict: APPROVE

## RM-030 — PR #54: docs(contribution-log): LIU Jianwei phase-③ man-hours backfill (rule 6)

- Reviewer(s): domain CR creator-xiyuan (governance & CI)
- Spec alignment: rule 6 man-hours backfill; 11/17 3.0h + 11/18 8.5h = 11.5h, with 8.5h = 2.0 + 3.5 + 3.0
- Architecture / Code quality: n/a (docs)
- Test quality: docs-only
- Security / Efficiency: n/a
- Operational metadata: anchors exist — PR #41 comments `6987656202` and `6988443555`; the deadline claim (first batch extended to 2026-11-19) is supported; merged at `06db68d` (2026-11-19T11:03:03Z)
- Verdict: APPROVE

## RM-031 — PR #40: docs(governance): phase-② man-hours first batch + roster ID fixes

- Reviewer(s): domain CR creator-xiyuan (governance & CI; posted RM-025 — renumbered because #41's architecture co-sign posted RM-025 earlier)
- Spec alignment: phase-② man-hours first batch + roster ID fixes; rule 6 arithmetic checked against the reviewer's own posted comments
- Architecture / Code quality: n/a (docs)
- Test quality: docs-only
- Security / Efficiency: n/a
- Operational metadata: two body-level wording fixes requested before merge (no new commit needed); merged at `f1d889d`; posted memo 2026-11-18T10:45:16Z
- Verdict: APPROVE

## RM-032 — PR #59: docs(report): realign §6 transcript citations after #53

- Reviewer(s): domain CR creator-xiyuan (governance & CI; posted RM-020 — renumbered because #35's memo posted RM-020 earlier)
- Spec alignment: §6 transcript citations realigned after #53; docs-only
- Architecture alignment: n/a
- Code quality: n/a
- Test quality: reviewer took both files (pre-#53 `539ae7cf`, post-#53 head) and compared line by line: 11 transcript refs all map (33→41, 34→42, 35→43, 37→45, 41→49, 123-126→142-145) with identical text; 7 #41 status refs at L55/L112/L180/L204/L207/L213/L223; 33 headings / ~6.4k words / `git diff --check` clean
- Security / Efficiency: n/a
- Operational metadata: reviewer flagged `Report.md:141`/`:142` as still "in review" and left them for the next docs pass (now PR #63); merged at `c5d42bf` (2026-11-19T11:00:36Z)
- Verdict: APPROVE
