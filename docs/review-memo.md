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
> - RM-033 is PR #62's final memo, written in the 2026-11-20 append below
>   (transcribed from the APPROVED reviews on head `a4a1840`: creator-xiyuan
>   12:55:55Z, swordnew123 13:16:20Z); #62 squash-merged as `6f47cc2`. The
>   posted RM-021 changes-requested reviews (on `1ff2050`, re-issued on
>   `8111850`) are superseded and not a final memo.
>   RM-034 is the approved #57 review memo at `72eb656`; #57 squash-merged as
>   `8e7e2af` on 2026-11-19. RM-035 is the approved #61 review memo, re-issued
>   at `6ffaecc` after the base update dismissed the `7901e8c` approval; #61
>   squash-merged as `6264e89` on 2026-11-19. Both entries are written in the
>   2026-11-20 append below.
> - #47's provisional RM-024 is void; #37's draft RM-015 is superseded by
>   RM-017.
>
> **2026-11-20 ledger append note (RM-033–RM-040).** This append writes the
> entries reserved above and closes the documented deferrals in the PM reviews
> of #56 and #67 (CONTRIBUTING step 6; both review bodies are the memos of
> record, transcribed below). RM-036 keeps PM's posted label (proposed in the
> #56 review); RM-037 is chain-assigned after it (no label was posted on #67).
> RM-038/039 were first posted as CHANGES REQUIRED and are rewritten here to
> their final APPROVE verdicts after the fixes (`26eaabf` / body-only
> `fd17f6d`). RM-040 is the #52 final memo. Numbering follows the chain
> reserved in PR #64, not merge order: #56 (RM-036) merged at 13:41Z, before
> #62 (RM-033) at 14:20Z — during a backfill the reserved chain is
> authoritative.

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
- Head reviewed: `b410daf` (the co-sign binds this head; the governance review is posted as RM-020 and appears in this ledger as RM-024)
- Spec alignment: S1 follows ADR-001's advisory/authoritative boundary — policy owns evaluation and protected transitions; high-severity signals and typed analysis failures enter the deterministic review path
- Architecture alignment: commit checks revision, content hash and pinned snapshot; atomic case/queue/audit persistence with rollback/replay tests; S2/API and S3 remain separate and full FUN-005/INV-2 integration is not claimed
- Code quality / Test quality: 121 offline tests and `ruff` passed through delegated tooling (the memo explicitly does not assert the account holder personally ran them); code quality is otherwise covered by RM-024
- Security / Efficiency: covered by RM-024; this memo records the mandatory architecture co-sign, not new security/efficiency evidence
- Operational metadata: merged at `e60dd50`; posted memo 2026-11-18T06:30:15Z; co-sign covers the S1 scope/head, not future S2/S3 or live/semantic evidence
- Verdict: APPROVE

## RM-026 — PR #46: Architecture review: ADR-001 corpus-maintenance addendum

- Reviewer(s): xiaolizi33 (architecture owner)
- Head reviewed: `6f82a90`
- Spec alignment: the documentation-only diff records the narrow maintenance scope authorized on 2026-11-17; it preserves seed, quotas and native labels, requires PII/provenance/reproducibility checks, records the 95-row fallback as below the ≥100 prerequisite, and binds new replay evidence to the new corpus revision
- Architecture alignment: architecture approval, execution-plan approval, data review and PR review remain distinct; the addendum is an ADR-001 extension, not a new architecture decision
- Code quality / Test quality / Security / Efficiency: n/a (docs; no implementation tests required)
- Operational metadata: merged at `7b0ee1e`; posted memo 2026-11-18T06:30:17Z; approval records the narrow addendum and does not claim raw-data publication, runtime/model changes, or INV-5/TD-1 complete. Naming `test/eval/expectation_policy.yaml` after #47 lands is a nonblocking follow-up.
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

## RM-033 — PR #62: test(acceptance): add release invariant and must acceptance tests (#55)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; posted RM-021 — renumbered because ledger RM-021 is PR #44); PM swordnew123 (LIU Jianwei)
- Spec alignment: 22 offline tests covering REQ-INV-001..REQ-INV-005 and the merged Must acceptance flows under Test-Plan-Approved: #55; `docs/architecture/trace-matrix.md` updated to reference the two new test files (5 invariant rows + 3 must rows)
- Architecture alignment: no `src/` change; the only architecture-file edit is the trace matrix, byte-unchanged since Li's co-sign on `211ff1e`
- Code quality: n/a (tests + docs)
- Test quality: final re-review on `a4a1840` replaced the empty-assertion rollback test with parametrized HOLD/ESCALATE failure paths where a queue row would have been written before the injected ABORT, so `_queue_count == 0` now genuinely proves rollback; offline suite green
- Security: two findings documented rather than patched in-scope — the authority-token tamper path (BUG-003, needs an ADR addendum) and the declared-but-unreachable PENDING_UNCONFIRMED status (BUG-004)
- Efficiency: n/a
- Operational metadata: ai-use-log `AI-012` (renumbered from the posted AI-010 on the domain CR's instruction — AI-010/011 belong to #57/#61), transcript `transcripts/60105888-DA-Buna-AI012.md`; bug-diary BUG-003/BUG-004; PM delta check: `a4a1840` touches only the yaml (32+/31−, the AI-012 block byte-identical after the move)
- Verdict: APPROVE (final head `a4a1840`; squash `6f47cc2` 2026-11-19T14:20:06Z)

## RM-034 — PR #57: feat(ci): gate 4 blocks on semantic evaluation (--strict) + replay converter (TD-1, REQ-INV-005)

- Reviewer(s): PM swordnew123 (LIU Jianwei; posted RM-034, unique)
- Spec alignment: TD-1 — gate 4 blocks on semantic evaluation under REQ-INV-005; replay converter accepts a replay committed in the same PR
- Architecture alignment: n/a (CI + scripts; no element/ADR change)
- Code quality: `select_pr_replay()` fails closed — exactly-one replay is used, zero actionable → fail, multiple → fail — instead of silently skipping
- Test quality: single/zero/multiple replay-selection tests + success-path test; PM reproduced the CI path "prompt PR + 1 committed replay → PASS"; strictness parity locked (eval_runner and test both 0.85, registry parity test retained)
- Security / Efficiency: n/a
- Operational metadata: provisional CHANGES REQUIRED at 11:00:56Z (P0: CI could not reach a committed replay — `resolve_replay()` saw neither CLI nor env) fixed on `72eb656`; ai-use-log `AI-010`; squash `8e7e2af` 2026-11-19T12:07:51Z
- Verdict: APPROVE (final review at `72eb656`, 11:44:21Z)

## RM-035 — PR #61: test(gate1): verify the cited test plan exists, is independently approved, and predates implementation (TD-2, REQ-GOV-002)

- Reviewer(s): PM swordnew123 (LIU Jianwei; posted RM-035 provisional, re-issued final — unique)
- Spec alignment: gate 1 verifies the cited test plan exists, is independently approved (non-issue-author, non-PR-author), and predates the first implementation commit (author.date, UTC-normalized)
- Architecture alignment: n/a (scripts + tests)
- Code quality: fail-closed contract held — `_qualified_approval()` converts missing/illegal timestamps into `RuntimeError` at the parse boundary; `_parse_time`'s `ValueError` can no longer escape as a traceback
- Test quality: 16 offline gate-1 tests incl. `test_marker_comment_with_none_timestamp_fails_closed`; the per-commit file-list size cap is recorded as a documented known limitation instead of a promised truncation check
- Security / Efficiency: n/a
- Operational metadata: provisional CHANGES REQUIRED at 11:01:05Z (P1 traceback escape); an intermediate approval was dismissed by `dismiss_stale_reviews` as bookkeeping on a base update; the re-issued final at `6ffaecc` verified the own diff unchanged (5 files, +1721/−13) and gate-1 logic byte-identical to the approved `7901e8c`; ai-use-log `AI-011`; squash `6264e89` 2026-11-19T12:35:44Z
- Verdict: APPROVE (re-issued final review at `6ffaecc`, 12:20:39Z)

## RM-036 — PR #56: docs(governance): `scripts/**` is agent-writable code, not CI configuration; countersign fallback

- Reviewer(s): PM swordnew123 (LIU Jianwei; posted label RM-036, unique)
- Spec alignment: no requirement change; corrects D3 documentation to match `AGENTS.md` §4 and the permission model — `scripts/` is ordinary agent-writable code, not CI configuration; `prompts/` still triggers gate 4
- Architecture alignment: no element/ADR/invariant change; `.github/workflows/` remains the CI-configuration red line
- Code quality: n/a (docs-only; the two files are byte-identical between the reviewed head and the update)
- Test quality: docs-only; blocking-gates green on `00e7358`
- Security: no new authority — `.opencode/permissions.jsonc` already allowlists `scripts/` for the code agent; the manifest had narrowed it incorrectly; human-only paths untouched
- Efficiency: n/a
- Operational metadata: docs-only, gate 1/6 n/a per CONTRIBUTING; the countersign fallback makes an absent PM countersign explicit (pending/absent with reason); the ledger entry was deferred per CONTRIBUTING step 6 (recorded in the review) and is written here; P2 follow-ups noted (gate 1 also applies to scripts PRs via CODE_PREFIXES; the quoted wording belongs to permission-model.md); squash `344b376` 2026-11-19T13:41:33Z
- Verdict: APPROVE (review at `00e7358`, 13:15:20Z)

## RM-037 — PR #67: docs(governance): enforcement table matches gate 5's actual AST coverage (TD-4)

- Reviewer(s): PM swordnew123 (LIU Jianwei; ledger number RM-037 assigned by the reserved chain after RM-036 — no label was posted on #67)
- Spec alignment: no requirement change; the enforcement table now states exactly what gate 5 runs — rule 4's INV-1 half and rule 5's named prohibitions are machine-enforced by `test_invariants.py`; rule 1, the analysis→policy edge and element cycles remain planned in #66; contract/API/call-graph checks do not exist and are not claimed
- Architecture alignment: no element/ADR change; rule 6's inline note now says review rule + the narrow #66 guard for `.opencode/`/`.agent/`, explicitly not `transcripts/`
- Code quality: n/a (docs-only, 1 file)
- Test quality: the table's claims were verified against `test_invariants.py:174/181/233`, `check_safety_paths.py:8-12` and `ci.yml:36-49`; blocking-gates green on `34c6d1a`
- Security: no new authority; the table no longer implies a nonexistent call-graph check
- Efficiency: n/a
- Operational metadata: docs-only, gate 1/6 n/a; the ledger entry was deferred per CONTRIBUTING step 6 and is written here; P2 noted (the rule 5 row omits the mutation-repository import check — the table understates, not overstates); squash `d8d1346` 2026-11-19T13:42:51Z
- Verdict: APPROVE (review at `34c6d1a`, 13:34:32Z)

## RM-038 — PR #68: docs(evidence): record Li stage-2 candidate evaluation and human decision (#50)

- Reviewer(s): PM swordnew123 (LIU Jianwei)
- Spec alignment: D5 evidence entry for transcript #1 (Li stage-2 candidate evaluation and the human decision); content spot-checks all verified (7 code/document line references, REQ IDs, COS-001 numbers, hygiene check)
- Architecture alignment: n/a (evidence docs)
- Code quality: initial review found two governance gaps — (P1-1) the new `docs/evidence/` directory was not registered in the repository layout table (`README.md:23-32`); (P1-2) the document cited `src/contentguard/analysis/` files and `transcripts/60938585-LI-Shiyi.md` that existed only in unmerged PR #52, and the pinned commit `7206e06` would become unreachable after #52's rebase. Final head `26eaabf` resolves both: the README row is present; the evidence doc links `7206e06` and names PR #52 as provenance.
- Test quality: n/a (docs)
- Security / Efficiency: n/a
- Operational metadata: P2 follow-ups (dual H1 headings, intervention-marker format, stale "gate 4 warn-only" wording) were addressed at `1bc56b6`; initial review at `836f7ea`, final approval at `26eaabf` (main merge of #52). Squash-merged as `b5d8460` on 2026-11-20.
- Verdict: APPROVE (final) — initial CHANGES REQUIRED (review 2026-11-19T15:13:26Z, github.com/CS5351-Group10/contentguard/pull/68#pullrequestreview-5977229159) resolved; final PM approval 2026-11-20T08:14:09Z (github.com/CS5351-Group10/contentguard/pull/68#pullrequestreview-5989454526)

## RM-039 — PR #69: feat(ci): structural checks — element set, import cycles, frozen paths (TD-4, gate 2e)

- Reviewer(s): PM swordnew123 (LIU Jianwei; non-author, governance/CI line)
- Spec alignment: TD-4 per issue #66 Revision 2 (REQ-INV-001); gate-1 ordering verified from raw timestamps (approval 13:34:16Z < session start 13:50:57Z < architecture co-sign 14:21:11Z < first implementation commit `75b8569` at 14:46:13Z)
- Architecture alignment: Revision-2 co-sign conditions verified in code one by one — element set exactly five, package-only detection with `__pycache__` ignored, declared-but-absent INFO, cycle detection naming the path, frozen guard limited to `.opencode/`+`.agent/` with transcripts exempt, docs-only pass only after the changed-file list resolves, missing token fails closed, stdlib only
- Code quality: independent local run on head `fd17f6d` — push-event simulation `GATE 2E PASS` + 2 INFO (matches the author's record); ruff clean; suite 270 passed + 1 failed, and the failure also fails on clean `main` (`6f47cc2`), environmental (Windows CRLF; BUG-005), not introduced here
- Test quality: 10 deterministic offline tests; P2-1 — the claimed "API failure listing changed files also fails" is implemented but has no negative test (optional, not blocking); P2-2 (the `_dependency_direction_violations` signature) remains with the testing owner
- Security / Efficiency: n/a
- Operational metadata: the initial body's two P1s were corrected by the author on 2026-11-20 12:27 HKT, body-only with the head unchanged: the ai-use-log reference is `AI-013` (with the AI-012 origin note), and the timeline now records the accepted early start; #52 renumbered its drafted AI-013 to AI-014. Final approval on `fd17f6d` at 2026-11-20T04:29:23Z; squash-merged as `6b91946` on 2026-11-20; #66 closed.
- Verdict: APPROVE (final) — initial CHANGES REQUIRED (review 2026-11-19T15:47:55Z, github.com/CS5351-Group10/contentguard/pull/69#pullrequestreview-5978319174) resolved; final PM approval (github.com/CS5351-Group10/contentguard/pull/69#pullrequestreview-5987504428)

## RM-040 — PR #52: feat(analysis): offline S3 advisory slice and session evidence (#43)

- Reviewer(s): PM swordnew123 (LIU Jianwei; non-author, code-owner)
- Spec alignment: REQ-FUN-002/005, REQ-SEC-001, REQ-INV-001/002 (supporting checks for INV-003/004 and provisional COS-001), per test plan #43. Offline scope only; live provider, runtime snapshot, semantic replay and S1/S2 integration remain pending.
- Architecture alignment: `analysis/` stays advisory; no import of policy internals and no enforcement authority. The three P1 fixes verified at `7206e06` remain unchanged at `c95fce3`: unhashable JSON fields return typed failures; exactly one `#sha256:` prefix; full citations validate the pinned corpus/snapshot IDs, revisions and digest.
- Code quality: per-file verification at `c95fce3`: the analysis source and test files are byte-identical to the PM-reviewed `7206e06`; the only PR delta is `docs/ai-use-log.yaml` (+2 lines: the AI-014 supersedes note) plus the main merges `6f47cc2` (#62) and `6b91946` (#69). No duplicate AI IDs; AI-012 (Buna/#62) and AI-013 (Huang/#69) preserved; S3 is AI-014 with `pr: 52`.
- Test quality: hosted `blocking-gates` green on `c95fce3`; the PR records 458 local passed, ruff clean, full-source mypy clean (67 files) and 31 requirements valid. Historical 188/406/422 counts are disclosed as historical, not final-head evidence.
- Security / Efficiency: no credentials or secrets; transcript sanitized; no new dependencies; context budget/usage accounting bounded; no live-provider claim.
- Operational metadata: head `c95fce3`, base `6b91946`; squash-merged as `397e002` on 2026-11-20; #43 closed. D5 note: the merged transcript is the S3 build session (stage-4 supporting evidence); the canonical Li stage-2 file remains a separate #50 deliverable, and this file should be renamed `60938585-LI-Shiyi-s3.md` when that lands.
- Verdict: APPROVE (final) — review 2026-11-20T07:35:54Z; github.com/CS5351-Group10/contentguard/pull/52#pullrequestreview-5989077588

> **2026-11-25 ledger backfill note (RM-041–RM-061).** This append writes the memos
> for the 2026-11-20 → 11-23 review burst. The PR review bodies are the memos of
> record; entries below are structured summaries, not verbatim transcriptions.
> Numbering follows the label each reviewer posted in the review body; the four label
> collisions in this burst are resolved by first-post precedence and disclosed below.
> Dismissed interim reviews are recorded as chain entries with their verdicts noted,
> not as final memos: RM-042's first pass on `3aa6b95` (CHANGES REQUIRED, 2026-11-21)
> is superseded by the final governance approval it shares with RM-050; RM-049
> (governance pass at `c5a9b2c`) is superseded by RM-050 at `07b542e`; RM-051
> (`a2e280f`) is superseded by RM-053 at `8b0ece5`. RM-047 was first posted as
> CHANGES REQUIRED and is followed by the final APPROVE as RM-048 after the fixes.
> RM-042 and RM-050 are one final review body carrying two numbers: RM-042 is the
> chain label from the 11-21 dismissed initial, RM-050 the label posted on the final
> re-review — per the PM's reserved mapping.
>
> **Collision rulings (first-post precedence):**
> - **RM-042** — creator-xiyuan posted the label on #75 (2026-11-21T06:35:53Z) and
>   again on #77 (2026-11-21T12:06:39Z). #75 keeps RM-042 (later-memo semantics also
>   point to #75); #77 is chain-assigned RM-057.
> - **RM-056** — the PM's #88 review (2026-11-22T16:59:54Z) keeps RM-056; HUANG's
>   #87 re-review (2026-11-22T23:07:41Z) is chain-assigned RM-060.
> - **RM-057** — this ledger's #77 memo (first posted 2026-11-21T12:06:39Z) keeps
>   RM-057; HUANG's #88 re-review (2026-11-23T03:55:54Z) is chain-assigned RM-061.
> - **RM-058** — the PM's #88 re-review (2026-11-23T03:53:35Z) keeps RM-058; HUANG's
>   first #89 review (2026-11-23T04:10:05Z, CHANGES REQUESTED) is chain-linked
>   inside RM-059, whose final APPROVE at `3eb71a9` is the memo of record.
>
> **Final verdicts (backfilled 2026-11-25):** RM-054's final is RM-060 (APPROVE at
> `40abaa2`; squash `d16c9d4`); RM-055's final is RM-061 (APPROVE at `84b92bc`;
> squash `1e2d6db`); RM-056's final is RM-058 (PM re-review at `84b92bc`; squash
> `1e2d6db`); RM-059's #89 final APPROVE at `3eb71a9` is squash `dc01ad1`. The
> three CR entries keep their CHANGES REQUIRED verdict and point to these finals;
> the finals are not double-recorded as separate approvals inside the CR entries.
> RM-057's entry adapts the RM-040 skeleton fields to a docs-only man-hours review
> (Arithmetic / Recording quality / Evidence-pointer integrity in place of
> Architecture / Code / Test / Security).

## RM-041 — PR #72: docs(consistency): sync ledgers, gates, requirements and transcript inventory with merged reality

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; governance/CI lane); architecture approval for `docs/architecture/**` by xiaolizi33 (LI Shiyi) at the same head
- Spec alignment: no requirement change — a consistency sync of ledgers, gate rows, requirements and the transcript inventory with merged reality. Independently re-checkable facts verified: the six squash refs the body cites (`3cfdbc9` #64, `8481f98` #71, `ec04e5f` #74, `fb629c0` #63, `b88ae57` #65, `8637ab6` #70) are all ancestors of main, so "RM-015–RM-040 recorded as landed via #64" is true, not premature; trace-matrix TBD distribution matches the body (TBD (S3) = 0, TBD (S2) = 6, TBD (S5) = 5); the requirements.yaml PENDING set matches except REQ-PER-001, wrongly listed as pending in the body (P2: drop before merge)
- Architecture alignment: n/a (docs/ledger sync; no code/CI/registry change). One reserve recorded: `transcripts/README.md` now carries two overlapping tables (canonical file list + five-stage coverage) — dedupe at the next docs pass, otherwise the "same fact written twice" drift this PR fixes returns
- Code quality: n/a (docs-only, 11 files; single commit + one main merge)
- Test quality: n/a; CI double-green on `721d46e`
- Security / Efficiency: n/a
- Operational metadata: an earlier domain review at `5becd9e` (2026-11-20T04:28:13Z, DISMISSED on the head update) found the gate-2 table row still reading "Lint + type-check" while gate 2 is 2a–2d active plus 2e in #69 — that P2 ("Active (2a–2d), 2e in #69") is not restated in the final memo and was deferred to a later ledger pass; xiaolizi33's architecture approval (AI-assisted under LI Shiyi's explicit instruction, `test_smoke.py` 9 passed + 31 requirements valid reproduced) carries the same REQ-PER-001 P2; the review states `docs/req/**` (requirements.yaml) needs @Mei-github's sign, and no separate requirements-owner review appears on the thread — PM to verify against CODEOWNERS resolution. Head `721d46e`, base `fb629c0`; squash-merged as `762cddc` on 2026-11-20 (18:07:09Z)
- Verdict: APPROVE (final) — review 2026-11-20T08:54:15Z; github.com/CS5351-Group10/contentguard/pull/72#pullrequestreview-5989897511

## RM-042 — PR #75: feat(s2): API intake, lookup and review integration (WIP) — governance chain (final memo shared with RM-050)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; governance lane); PM swordnew123 (LIU Jianwei) round-2/3 verification reviews. Label history: RM-042 posted on the dismissed initial review, and colliding on PR #77 (see append note)
- Spec alignment: S2 API slice consumed against the #51 test-plan contract; governance surface only — API semantics and idempotency design are the architecture/PM lanes and are not signed here
- Architecture alignment: the first round surfaced the S1/S2 contract gap — S2's offline negative test was correct test-first design (typed `MandatoryRuleViolation` → 422, no final effect), but the real S1 engine committed typed failures via `EnforcementAuthority.commit` without a pre-commit validation path. Ruled S1-owned and explicitly not blocking #75; closed by #83 (ADR-002) before this PR merged
- Code quality: initial review at `3aa6b95` (2026-11-21T06:35:53Z, DISMISSED) found three governance blockers — ai-use-log placeholders (`REPLACE_WITH_ACTUAL_MODEL_ID`, `REPLACE_WITH_ACTUAL_COUNT`), `agent: codex` as a red-line question (OpenCode-only per AGENTS.md §4), and the doubled `transcripts/transcripts/` path — plus a WIP/draft-flag mismatch. PM round 2 at `7cae5a6` verified the transcript path and code fixes; PM round 3 at `6bdf85c` verified all four governance blockers closed (`agent: opencode`, real model id, `session_transcript` pointer, interventions 1) and diagnosed the gate-1 red as the lost literal `Test-Plan-Approved: #51` marker in the rewritten body
- Test quality: interim re-review at `b4e86d7` confirmed three of four initial blockers closed; the governance verdict's zero-write 422 HTTP leg was later code-verified at `c5a9b2c` (real engine + real store; case/queue/audit/replay counts and case status asserted unchanged)
- Security / Efficiency: the `agent: codex` question was resolved as a disclosed deviation, not a silent rewrite — the PM pre-authorized "truthful label + explicit disclosure" in round 2; this path-B handling was later formalized as the conditional acknowledgment in RM-047 and recorded as TD-11 (rule text and practice diverged, RM-036 class)
- Operational metadata: memo of record is creator-xiyuan's governance APPROVE at `07b542e` (2026-11-22T09:49:15Z), whose body is summarized under RM-050 — same review, two numbers per the PM's reserved mapping; architecture re-approve by xiaolizi33 (LI Shiyi) at the same head 09:48:45Z. Head `07b542e`, base `257a97a`; squash-merged as `9e189e9` on 2026-11-22 (09:54:33Z; 17:54 HKT). Chain links: initial CHANGES REQUIRED github.com/CS5351-Group10/contentguard/pull/75#pullrequestreview-6003554670; PM round 2 github.com/CS5351-Group10/contentguard/pull/75#pullrequestreview-6005066219
- Verdict: APPROVE (final; governance scope) — final review 2026-11-22T09:49:15Z; github.com/CS5351-Group10/contentguard/pull/75#pullrequestreview-6011567054 (initial CHANGES REQUIRED 2026-11-21T06:35:53Z, github.com/CS5351-Group10/contentguard/pull/75#pullrequestreview-6003554670, superseded)

## RM-043 — PR #78: docs(man-hours): LIU phase-4/5 backfill rows per rule 6 (member-authorized, anchored)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author)
- Spec alignment: the PM's own man-hours backfill under rule 6 member-authorization — with member and reporter the same person, the only hours in the repo no second person had checked. Anchors verified against GitHub timestamps, not the report's description: phase ④ (11-20, declared 11:45–16:53) anchored 12:02–16:50 via #60 policy-review comments, #49 Train-A merge batch comments and the #72 refresh notice — all inside the declared interval; phase ⑤ (11-21, declared 18:15–20:10, marked running) anchored 19:25–20:03, including #76 review id 6004899505 reverse-checked via the API (APPROVED, 19:26 HKT). Arithmetic recomputed: 12.5 + 3.5 + 13.1 + 5.0 + 2.0 = 36.1, matching Report §2; ⑤'s 1h55m booked as 2.0h within the 0.5h step
- Architecture alignment: n/a (docs-only, two files)
- Code quality: n/a; three practices endorsed: a separate PR so no commit lands after the approval (the #39 pattern); the pre-18:15 session with no anchorable GitHub activity recorded as not counted rather than estimated; ⑤ marked running instead of padding to a full day
- Test quality: n/a; CI green on `671330d`
- Security / Efficiency: structural note recorded, not blocking: for PM rows, authorization, aggregation and rounding sit with one person — checkable anchors lower the risk to "the numbers have evidence" but not to "someone independently saw the duration"; recommendation to require a second member to confirm anchors on PM rows (this review performed that check once)
- Operational metadata: head `671330d`, base `d0f38c1`; squash-merged as `3d63057` on 2026-11-21 (12:52:53Z)
- Verdict: APPROVE — review 2026-11-21T12:48:36Z; github.com/CS5351-Group10/contentguard/pull/78#pullrequestreview-6005280814

## RM-044 — PR #80: docs(transcripts): sync README to merged stage-2 reality (#76)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author)
- Spec alignment: post-#76 alignment of the stale README rows. Verified the files themselves on main `56ccc3c`, not just the wording: `60938585-LI-Shiyi.md` is the 123-line stage-2 candidate-evaluation excerpt (1 marker, header "stage-2 candidate evaluation") and `60938585-LI-Shiyi-s3.md` the 7121-line S3 build session (5 markers) — the canonical path now holds the stage-2 file and the misread RM-041 fixed is structurally resolved
- Architecture alignment: n/a (docs-only, single file, no transcript content touched). The single marker is the "都保留" approval carrying the original reply, its context, and the "not originally typed inside OpenCode" declaration — provenance written into the evidence itself
- Code quality: n/a
- Test quality: n/a; CI double-green on `0af3452`
- Security / Efficiency: two non-blocking reminders: (1) keep the "annotated excerpt, compiled from the contemporaneous review draft and #68 evidence" wording in Report §6/§7 — the file header itself declares a compilation, not a D5 "full, raw transcript"; (2) canonical coverage is 3/5 (LIU / HUANG / LI ✅; HAN-Mei stage-1 and DA-Buna stage-5 still supporting-only) — if the two do not land before 23:59, Report must state 3/5 rather than imply five
- Operational metadata: head `0af3452`, base `56ccc3c`; squash-merged as `802c59a` on 2026-11-21 (14:42:28Z)
- Verdict: APPROVE — review 2026-11-21T14:39:45Z; github.com/CS5351-Group10/contentguard/pull/80#pullrequestreview-6006036860

## RM-045 — PR #81: docs(report): assemble member self-reflections from issue #27 (verbatim)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author)
- Spec alignment: §7 verbatim assembly checked on the three axes D6 cares about. Word counts recomputed: LIU 335 / Mei 316 / Li 369 / HUANG 375 / Buna 347 — all within the 300–500 band (the body's "within/near" hedge unnecessary). Verbatim sampling, not the declaration: Mei's and Buna's long sentences char-exact against #27; Li's 16 long sentences verbatim after stripping his own title line; the PM's own section verified with the assembly note removed; `TBD — author to supply` residue = 0 — "no rewording, no translation, no reordering" holds
- Architecture alignment: n/a (docs-only)
- Code quality: two assembly-level edits, both compliant: standard `### NAME (ID)` headings added (Buna's comment body lacked one — format, not content); member title lines and the PM's word-count meta row removed, as declared in the body
- Test quality: n/a; CI (`blocking-gates`) still running at review time — docs-only, expected green; verdict subject to the final CI result
- Security / Efficiency: reminder recorded: the body says Li's section supersedes the AI-assisted draft from #76 — that draft's wording must not survive anywhere in Report or appendix, or the same member has two reflection versions (the "same fact written twice" class)
- Operational metadata: head `66c9715`, base `20f5f7b`; squash-merged as `4c3dc89` on 2026-11-21 (15:04:40Z)
- Verdict: APPROVE — review 2026-11-21T14:59:52Z; github.com/CS5351-Group10/contentguard/pull/81#pullrequestreview-6006152695

## RM-046 — PR #82: docs: refresh Report and README status banners to post-#81 reality

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author)
- Spec alignment: every banner claim machine-checked, because "banner contradicting body" is the defect this PR fixes: #79 approved (merged, squash `20f5f7b`); "draft PR #75" true at review time (the draft flag had just been flipped by Mei — had it still been false, the wording would have had to change); transcripts stages 2/3/4 landed with the LI stage-2 excerpt and `-s3.md` on main, 3/5 canonical; #81 merged (`4c3dc89`) with the five §7 reflections in range
- Architecture alignment: n/a (docs-only; banners only, no numbers changed)
- Code quality: n/a
- Test quality: n/a; CI double-green on `339112b`
- Security / Efficiency: n/a; the per-claim narration collapsed into pointers (issue #49 / debt register) — at close-out the report should point, not restate
- Operational metadata: head `339112b`, base `4c3dc89`; squash-merged as `c24d2be` on 2026-11-21 (17:09:21Z)
- Verdict: APPROVE — review 2026-11-21T15:43:33Z; github.com/CS5351-Group10/contentguard/pull/82#pullrequestreview-6006357909

## RM-047 — PR #83: feat(policy): ADR-002 review_and_commit transition with pre-commit mandatory-rule validation (provenance ruling — superseded by RM-048)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei); Li's architecture P1 (posted 2026-11-22T01:05:05Z on the same head) independently code-read and endorsed
- Spec alignment: the conditional formal acknowledgment of the RM-042 path-B deviation, delivered as requested: AI-017's fields verified real (`agent=zcode`, `model=zai/glm-5.3-flash`, operator LIU Jianwei, interventions 5, `pr: 83`; no placeholders) and the transcript header's "does not claim one [OpenCode session id]" singled out as the disclosure that matters. The acknowledgment is conditional, three conditions: the record never counts as D5 canonical nor is described anywhere as OpenCode session evidence; the rule must follow reality — a TD-11 debt-register row or an AGENTS.md §4 amendment, not neither; the acknowledgment covers provenance only, not code correctness
- Architecture alignment: endorses Li's P1 on the replay identity: `enforcement.py` hashes the projected decision, so distinct review requests (a rationale-only edit, or a requested_outcome flip neutralized by the mandatory REJECT floor) collapse to one `payload_hash` and reconcile instead of returning the ADR-002-required CONFLICT — audit identity erased on a safety-critical path; the fix direction (persist and compare an immutable review-request identity: requested outcome, rationale, actor, case revision, pinned identity) approved, with the two real-store regressions Li required
- Code quality: 7 files, +792/−12, verified via the API because the local `origin/main` was stale (a local diff would have over-reported four unrelated files); the invariants.md sentence placing `MandatoryRuleViolation` as action-refusal (not content judgment) under REQ-INV-002 endorsed; trace-matrix points REQ-FUN-003 / REQ-INV-003 at the new tests while keeping `TBD (S2, PR #75)` honest
- Test quality: `blocking-gates` success on the current head; the gate-1 failed-run explanation (stale body in the event snapshot) accepted, but green counted from the current head only
- Security / Efficiency: blocking gap: `transcripts/README.md` had no row for the new AI-017 transcript — a frozen (human-only) directory carrying an unlisted file; the row must be written by a human, not the session
- Operational metadata: three fixes required (README row; TD-11 or §4 — one of the two; Li's P1 fixed or explicitly split with reasons); review at `2e6dac4`, 2026-11-22T01:33:52Z; superseded by RM-048 (final APPROVE at `7293b51` after all three fixes); #83 squash-merged as `257a97a` on 2026-11-22 (05:11:18Z)
- Verdict: CHANGES REQUIRED — superseded by RM-048 (final); review 2026-11-22T01:33:52Z; github.com/CS5351-Group10/contentguard/pull/83#pullrequestreview-6009400840

## RM-048 — PR #83: re-review at `7293b51` — all three RM-047 items closed (final)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; governance/provenance surface); Li's policy-scope re-approval at the same head 05:09:10Z is separate and not replaced by this vote
- Spec alignment: RM-047's three conditions closed one by one: (1) `transcripts/README.md` rows added for AI-017 and AI-018, the AI-018 row self-disclosing "row and file placed by the session at the PM's explicit instruction (2026-11-22)" — disclosure before discovery, which decides record vs incident; (2) TD-11 chosen over the §4 amendment, preserving what the rule originally said: the rule was not changed, the practice diverged once, disclosed, and is recorded; (3) Li's P1 fixed beyond the ask (see Architecture alignment)
- Architecture alignment: `store.py` adds a `review_request_hash` column with an existence-check migration (not a blind ALTER); the replay path compares `payload_hash` AND `review_request_hash` — the projected-decision semantics kept, the immutable request identity added; four tests cover the three regressions RM-047 endorsed (`test_g5_same_key_different_rationale_conflicts`, `test_g5_same_key_floor_overridden_outcome_conflicts`, `test_g5_review_request_on_evaluate_row_conflicts`) plus the legacy-schema migration test
- Code quality: ai-use-log AI-017 (5 interventions) and AI-018 (2) fields verified real, no placeholders, no duplicate AI IDs; `pr: 83` on both
- Test quality: CI double-green on `7293b51`, 12 files +1114/−19
- Security / Efficiency: new non-blocking record: `transcripts/**` is frozen/human-only while AI-018's file and row were session-written at the PM's explicit instruction — accepted under the same disclosure standard as AI-017, but TD-11's wording does not yet cover frozen-path writes (and `check_structural.py`'s frozen guard covers only `.opencode/**` + `.agent/**`, so `transcripts/**` is a gateless rule); half-sentence in TD-11 or a new TD-12 requested — the same "docs say A, machine does B" structure
- Operational metadata: head `7293b51`, base `c24d2be`; squash-merged as `257a97a` on 2026-11-22 (05:11:18Z)
- Verdict: APPROVE (final) — review 2026-11-22T05:09:07Z; github.com/CS5351-Group10/contentguard/pull/83#pullrequestreview-6010496468

## RM-049 — PR #75: governance pass at `c5a9b2c` (dismissed interim — superseded by RM-050)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; governance lane)
- Spec alignment: full governance pass at `c5a9b2c` (26 files, +4958): `src/contentguard/policy/**` = 0 — the S1/S2 boundary held, one side decides and the other consumes (the root cause of the earlier contract conflict was both sides judging); API semantics explicitly not covered (Li's CHANGES REQUESTED still bound to `b4e86d7` at posting time)
- Architecture alignment: n/a here; the zero-write 422 leg was verified in code, not by test name: real engine + real store, `post` returns 422 with "mandatory rule" in the detail, store counts and the case row (revision 4, escalated) unchanged — ADR-002 acceptance-matrix group 1 with a real HTTP leg; the 503 non-degradation tests present
- Code quality: ai-use-log verified — 18 entries, no duplicates; AI-015 (`opencode/big-pickle`, HAN Mei, 1 intervention, `pr: 75`) and AI-019 (`zcode`, `zai/glm-5.3-flash`, LIU Jianwei, 2 interventions, `pr: 75`) fields real; the AI-019 README row carries the same PM-instruction disclosure as #83's AI-017/018 and is accepted under the same standard
- Test quality: CI double-green on `c5a9b2c`; explicitly unverified and left for Li/PM spot-check: the rationale-only-retry 409 variant was not walked line-by-line (mechanism plausible via #83's `review_request_hash`), and the fastapi/uvicorn version bounds were not dependency-resolved (gate 2c counted instead)
- Security / Efficiency: n/a beyond the governance surface above
- Operational metadata: the author pre-announced this vote's own dismissal — the 09:19 comment said `cdee491` (AI-018/AI-019 corrections, TD-11 session count) was still outside the PR head, and those commits touch exactly the docs under review; also recorded: #83's merge (`257a97a`) removed the "#75 cannot merge before #83" constraint, and the draft had been flipped to ready. Review posted 2026-11-22T09:24:36Z at `c5a9b2c`, dismissed on the head update to `07b542e`; superseded by RM-050 (final)
- Verdict: APPROVE (interim, governance scope) — DISMISSED on the push to `07b542e`; superseded by RM-050; review 2026-11-22T09:24:36Z; github.com/CS5351-Group10/contentguard/pull/75#pullrequestreview-6011484392

## RM-050 — PR #75: re-review at `07b542e` (governance scope) — final

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; governance lane); xiaolizi33's architecture re-approval at the same head landed 09:48:45Z, 30 seconds before this review
- Spec alignment: `07b542e` closes both of Li's `c5a9b2c` P1s: the route-level staleness guard is removed so replay/staleness ordering belongs to the policy engine per ADR-002 — a same-key retry whose expected revision predates a committed transition now reaches the policy-owned reconciliation of the stored result instead of a route 409; and the earliest case read catches `StorageUnavailable` and maps it to 503 before any policy call. Three new tests match Li's asks (`test_real_engine_current_row_replay_reconciles_and_identity_conflicts`, `test_review_case_read_failure_is_503_with_zero_policy_calls`, `test_stale_review_revision_conflicts_through_policy`) — name and placement verified; the semantics left to Li's re-review, which this vote does not replace
- Architecture alignment: governance scope: the S2/policy boundary stays intact and `cdee491`'s docs corrections verified — AI-019's log scope already covers `src/contentguard/api/routes/review.py`, so the `07b542e` edit to that file remains in declared scope without a log change; TD-11 rewritten to the requested form, naming all three disclosed zcode sessions (AI-017/AI-018 in #83, AI-019 in #75 — RM-042 path B) and the "RM-036 class: docs say A, machine runs B" framing
- Code quality: n/a beyond the governance surface (the diff delta over `c5a9b2c` is exactly the two reviewed commits)
- Test quality: CI double-green on `07b542e`, 28 files +5122/−2
- Security / Efficiency: n/a
- Operational metadata: process advice recorded at the reviewer's initiative: this was the second "approved, then head moved" cycle on this PR — push the final head before requesting review; RM-049's dismissal and this re-review are that cycle's cost. Head `07b542e`, base `257a97a`; squash-merged as `9e189e9` on 2026-11-22 (09:54:33Z; 17:54 HKT)
- Verdict: APPROVE (final; governance scope) — review 2026-11-22T09:49:15Z; github.com/CS5351-Group10/contentguard/pull/75#pullrequestreview-6011567054

## RM-051 — PR #84: docs(trace): flip S2 evidence rows to post-#83/#75 reality (dismissed interim — superseded by RM-053)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author)
- Spec alignment: evidence-status flips audited path by path, since a wrong flip forges coverage. 19 referenced test paths checked against main: 16 exist; the 3 missing (`test_demo_flags.py`, `test_evidence_access.py` — TBD (S5); `test_transaction_replay.py` — TBD (S2) on INV-002 and QUA-002) are all TBD-annotated, so the "future paths must be marked TBD" convention held. Three ghost paths cleaned: `test_intake.py` and `test_intake_validation.py` never existed yet hung off REQ-FUN-001, and the bare `test_review_queue.py` reference in requirements.yaml removed — this PR repairs the forged-looking state in reverse
- Architecture alignment: requirements.yaml delta matches the claim exactly: PENDING 9 → 6 (FUN-001 and SEC-002 leave; SEC-004 becomes PARTIAL, not PENDING); keeping the whole table `baselined` accepted — flipping only the S2 rows to `verified` would manufacture inconsistency with the delivered INV rows
- Code quality: the AI-019 provenance correction named the most valuable change: the blanket "no earlier transcript text was modified" replaced by the precise sentence naming the one in-place edit (one excerpt-declaration sentence at the head of its own transcript, branch commit `cdee491`, delivered in #75 and unreachable from main after the squash) plus the Addendum-over-rewrite policy for AI-018/AI-019 corrections; the accompanying "annotated record without a raw dump" caveat flagged for propagation into the README row so the limit does not live only in the yaml
- Test quality: CI double-green cited at `6bb9b35` (an earlier head of this PR); 4 files +27/−20, no code/prompt/CI/policy change
- Security / Efficiency: process note: the body was drafted by the zcode session under the RM-042 path-B disclosure class, no new ai-use-log entry — consistent with the #72/#82 docs-PR precedent, and the disclosure is required precisely because this PR edits trace evidence and provenance wording
- Operational metadata: review attached at `a2e280f`, posted 2026-11-22T11:11:22Z; dismissed by the strict up-to-date requirement when `8b0ece5` landed; superseded by RM-053 (final at `8b0ece5`); #84 squash-merged as `bc30315` on 2026-11-22 (12:03:37Z)
- Verdict: APPROVE (interim at `a2e280f`) — DISMISSED on the push to `8b0ece5`; superseded by RM-053; review 2026-11-22T11:11:22Z; github.com/CS5351-Group10/contentguard/pull/84#pullrequestreview-6011928924

## RM-052 — PR #85: docs(log): append LI Shiyi 11-21 additional 1.5h (issue #28)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author)
- Spec alignment: one row plus one aggregation note, but hours feed D6 directly, so the two base facts were verified: the #28 report comment exists verbatim (xiaolizi33, 2026-11-21T16:31Z: "member-confirmed net personal effort … retrospective estimate … not a reconstructed timesheet") and the row's wording matches — an estimate written as an estimate, not as a timesheet
- Architecture alignment: n/a (docs-only, single file)
- Code quality: +2/−0 — append-only, no existing row touched (the man-hours ledger's baseline rule held)
- Test quality: n/a; CI double-green on `1f5b537`
- Security / Efficiency: all four anchors land on 11-21 (#76 close-out merge 22:31; §7 → #27 22:29; #75 architecture CR 22:39; #79 review + final-head approval 22:52/23:01, merge 23:01). Forward caveat recorded: the anchor covers only the 11-21 CR — the actual #75 re-review happened 11-22 17:24, after this report, and a future audit must not count it into 11-21 hours. Report §2 not yet reflecting the 1.5h (26.5 vs 28.0) accepted as a dated snapshot with a request: add "log rows appended after this timestamp are not yet reflected" and carry the row into the final aggregation. Minor: a missing `##` heading before the n/a section
- Operational metadata: head `1f5b537`, base `9e189e9`; squash-merged as `9a8c08b` on 2026-11-22 (11:31:03Z)
- Verdict: APPROVE — review 2026-11-22T11:13:14Z; github.com/CS5351-Group10/contentguard/pull/85#pullrequestreview-6011934635

## RM-053 — PR #84: re-review at `8b0ece5` (final)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author); Li's architecture approval at the same head 11:53:14Z separate
- Spec alignment: the reviewer's own false positive disclosed first: the re-run audit script swallowed a network error as a 404 and nearly reported `test_api_review_queue.py` as missing from main — recorded in the memo because "a checker that cannot distinguish truly-absent from unread is itself a source of false evidence". Corrected re-run: 19 references, only the 3 TBD-annotated paths missing; the three ghost paths still 0; the AI-019 provenance sentence still verbatim on head, the old sentence still on main (pre-merge)
- Architecture alignment: `8b0ece5`'s change endorses Li's P2 direction: FUN-001 downgraded from delivered evidence to PARTIAL, naming the fake processor / lookup repository boundary and keeping real-chain queue/audit persistence, lost-ack reconciliation and no-duplicate consequential effects as pending — more accurate than either PENDING or full evidence; PENDING set unchanged (6: FUN-006/007, SEC-003/005, QUA-002, PER-001), no opportunistic flips
- Code quality: n/a (docs-only, 4 files +27/−20)
- Test quality: CI double-green on `8b0ece5`
- Security / Efficiency: observation recorded for the PM: Li's 0.5h follow-up review hours were posted on the PR thread (11:54) rather than in `docs/contribution-log.md` — hours belong in the log; the next aggregation must land that row, not leave it in the thread
- Operational metadata: head `8b0ece5`, base `9a8c08b`; squash-merged as `bc30315` on 2026-11-22 (12:03:37Z)
- Verdict: APPROVE (final) — review 2026-11-22T12:02:14Z; github.com/CS5351-Group10/contentguard/pull/84#pullrequestreview-6012101123

## RM-054 — PR #87: docs(log): append endgame tail hours (LI Shiyi 1.0h, LIU 05-tail 10.2h) — issue #28

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author)
- Spec alignment: first computed D6 weights checked on arithmetic and method: LIU 46.3 (⑤ 12.2 = #78's 2.0 + 10.2), LI 29.0 (⑤ 2.5 = 1.5 + 1.0), HUANG 22.75, Buna 11.0, Mei 4.5; sum 113.55, mean 22.71, weights 2.04 / 0.20 / 1.28 / 1.00 / 0.48 summing to 5.00 — the D6 convention (mean = 1.0, weights sum to 5) holds. LI ⑤'s 1.5h aggregation gap fixed at `cc80ef8` (the gap reported at #85); §3's canonical count 2/5 → 3/5 correct; the unverifiable "9 of 11" figures removed
- Architecture alignment: n/a (docs-only, 2 files +17/−9)
- Code quality: blocking finding — HUANG ⑤ 2.0h missing: the reviewer's own hours were posted on #28 at 21:18 HKT with anchors (the 21:18 comment plus seven review ids), while the PR's last commit (`cc80ef8`, 21:23) fixed exactly this class of gap for LI and missed HUANG — a systemic last-reporter gap, not a one-off
- Test quality: CI double-green on `cc80ef8` at review time
- Security / Efficiency: two changes required: (1) a contribution-log row for HUANG ⑤ 2.0h with those anchors; (2) Report §2 HUANG ⑤ 1.5 → 3.5, total 22.75 → 24.75, weights recomputed (sum 115.55, mean 23.11; 2.00 / 0.19 / 1.25 / 1.07 / 0.48 — rounded sum 4.99) plus a "weights sum to 5.00 before per-member rounding" note. The "computed at the #28 close-out" wording must become an as-of snapshot caveat: before the missing row lands, the table is a pre-close-out snapshot, not the close-out result
- Operational metadata: review at `cc80ef8` (head at review time), 2026-11-22T14:40:19Z; base `bc30315`; PR #87 merged as `d16c9d4` on 2026-11-23 (03:38:13Z); the final re-review is RM-060 at `40abaa2`
- Verdict: CHANGES REQUIRED — superseded by RM-060 (final APPROVE at `40abaa2`; squash `d16c9d4`) — review 2026-11-22T14:40:19Z; github.com/CS5351-Group10/contentguard/pull/87#pullrequestreview-6012831606

## RM-055 — PR #88: docs(s5): lock Buna stage-5 transcript evidence

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author)
- Spec alignment: the 216-line `60105888-DA-Buna.md` verified: exactly five `[INTERVENTION]` markers (approve ×4, redirect ×1), each with type/by/rationale — the count the body claims is the count in the file; the excerpt policy states what is and is not reconstructed (no tool payloads, raw session turns or source-corpus text; local paths/credentials sanitized), consistent with the LI canonical excerpt standard; the logbook row's "deterministic offline baseline evidence only; does not establish live-provider or semantic replay acceptance or an approved architecture revision" endorsed as the honest framing
- Architecture alignment: blocking finding — README coverage row 5 marks ✅ for "architecture revision based on test evidence" while the transcript records the release-acceptance audit and the review process, not the revision: its only "Revision verified by tests:" line refers to case revision/status, and the revision itself lives in ADR-002 (#79, `20f5f7b`); a grader opening the file would not find the decision it is claimed to prove. Requested two-line rewrite keeping ✅ with the ADR-002 anchor ("the revision itself is recorded in ADR-002, not in this transcript")
- Code quality: minor: the README heading's em dash was normalized to a hyphen (`## Inventory —` → `## Inventory -`) — restore; after #65's GBK round-trip lesson, silent character normalization is worth tracking even when it introduces no mojibake
- Test quality: the logbook's 535 tests / 47 source files not independently rerun (local venv 3.10 cannot run `conftest.py`'s `datetime.UTC`); accepted on CI green plus continuity with the previous 534/535 runs — disclosed as the review's verification boundary
- Security / Efficiency: n/a beyond the above
- Operational metadata: review at `545e124`, 2026-11-22T16:09:46Z; both points (row-5 anchor, em dash) addressed at `4c8dc7b` per RM-056's independent verification; base `bc30315`; PR #88 merged as `1e2d6db` on 2026-11-23 (04:01:20Z); the final re-review is RM-061 at `84b92bc`
- Verdict: CHANGES REQUIRED — superseded by RM-061 (final APPROVE at `84b92bc`; squash `1e2d6db`) — review 2026-11-22T16:09:46Z; github.com/CS5351-Group10/contentguard/pull/88#pullrequestreview-6013195972

## RM-056 — PR #88: docs(s5): lock Buna stage-5 transcript evidence (PM review at `4c8dc7b`)

- Reviewer(s): PM swordnew123 (LIU Jianwei; non-author)
- Spec alignment: all three files read in full; status claims verified: #20 still open; #50/#27/#49 closed 2026-11-22; #75 merged 2026-11-22; 535 tests / 47 mypy files consistent with the post-#75 suite (#84, docs-only, in between); AI-003/AI-004 correctly framed as corpus-preparation supporting sessions with AI-012 as the stage-5 principal; gate 1 n/a (docs-only) and gate 6 n/a (no new agent session) per the #72/#82/#87 precedent — confirmed
- Architecture alignment: structure endorsed — excerpt policy states what is and is not reconstructed; five `[INTERVENTION]` markers (approve ×4, redirect ×1) with type/by/rationale; no credentials or absolute paths; the lock checklist honestly leaves review/lock unchecked
- Code quality: the `clarify transcript and ADR-002 relation` commit landed during this review and is reflected: the em-dash restore and the ADR-002 anchor on coverage row 5 (`20f5f7b`, #79 — verified) both accepted as improvements
- Test quality: latest-head checks green on `4c8dc7b`
- Security / Efficiency: P1 — "latest main" goes stale the moment #87 lands: transcript §7 ("after fetching latest main") and the evaluation-logbook row label `9e189e9` as latest main, true when fetched on 2026-11-22 (pre-#84) but #84 already moved main to `bc30315`; the evidence itself is sha-anchored so only the label is wrong — reword both to the anchored form ("local verification was performed on `main` at `9e189e9` (fetched 2026-11-22, pre-#84 state)"; the genuinely latest deterministic run is recorded at the freeze sha by the release checklist six-step). P2: §4 "MYPYPATH=mypy:" typo
- Operational metadata: tracked for the PM close-out PR, no action inside #88: after #88 lands canonical = 4/5 (stage 1, Mei, still open) while Report.md:3 and :74 still say "3/5 — stage 5 open" — those lines sit inside #87's diff and will be synced with the late-hours aggregation; sequencing #87 merge → #88 → close-out PR; #88 needs a normal `git merge origin/main` after #87 (strict up-to-date; no force). Review at `4c8dc7b`, 2026-11-22T16:59:54Z; base `bc30315`; PR #88 merged as `1e2d6db` on 2026-11-23 (04:01:20Z); the final PM re-review is RM-058; the canonical 4/5 → 5/5 sync landed via #90.
- Verdict: CHANGES REQUIRED — superseded by RM-058 (PM re-review at `84b92bc`; squash `1e2d6db`) — review 2026-11-22T16:59:54Z; github.com/CS5351-Group10/contentguard/pull/88#pullrequestreview-6013398220

## RM-057 — PR #77: docs(man-hours): aggregate endgame member-reported hours into log and Report §2 (as-reported)

- Reviewer(s): creator-xiyuan (HUANG Hongwei; non-author, code-owner)
- Spec alignment: REQ-INV-005 / REQ-GOV-004 man-hours evidence discipline (D6 weights = individual total / mean); docs-only, two files (`Report.md` §2 + `docs/contribution-log.md`)
- Arithmetic: all five totals and two subtotals recomputed independently and self-consistent — LIU 29.1 (③ 13.1 = 11.5 + 1.6 endgame row), HAN Mei 4.5, LI 26.5 (② 7.5 = 5.0 original row preserved in the log + 2.5 supplement — append-only discipline verified at source), HUANG 22.75, Buna 11.0
- Recording quality: four-state empty-cell legend added (`blank` / `pending` / `not reported` / `unclaimed`) — the §2 table now self-explains its open cells instead of overloading one label
- Evidence-pointer integrity: the three LI rows anchor `docs/evidence/60938585-closeout-handoff-20261120.md`, not yet on main at review time — hard merge-order requirement: #77 after #76. **Order not honored in fact:** #77 squash-merged 12:10:30Z, #76 at 14:31:35Z (`56ccc3c`) — the three anchors pointed at a not-yet-merged file for ~2h21m until #76 landed; final state consistent. Recorded as chain history, no retroactive action
- Recording note: LIU ③ 1.6h is off the 0.5h protocol step (rule 7; 1.55 would step-round to 1.5) — decided and disclosed in #71, now fixed into 13.1/29.1; kept as-is, noted so the provenance of 1.6 stays queryable
- Operational metadata: head `29111e6`, base `af63260`; CI double-green on `29111e6`; squash-merged as `d0f38c1` on 2026-11-21
- Verdict: APPROVE — review 2026-11-21T12:06:39Z; github.com/CS5351-Group10/contentguard/pull/77#pullrequestreview-6005077304
- Chain note: the review body carried the posted label "RM-042", colliding with #75's earlier-posted RM-042; chain-assigned RM-057 in this append per the PM's 2026-11-23 ruling (first-post precedence + later-memo semantics keep RM-042 on the #75 chain; see append note)

## RM-058 — PR #88: re-review at `84b92bc` (PM; final for RM-056)

- Reviewer(s): PM swordnew123 (LIU Jianwei; non-author)
- Spec alignment: re-review of Buna DA's stage-5 canonical transcript after the RM-056 changes, with `main` synced to `d16c9d4` (post-#87) for the strict up-to-date requirement. The RM-056 P1 was fixed in both files: `docs/architecture/evaluation-logbook.md:14` asks "Does the main baseline at `9e189e9…` pass deterministic verification?" and records "fetched `main` in the pre-#84 state"; `transcripts/60105888-DA-Buna.md:163-166` retitles §7 "Historical main baseline" and anchors the same `9e189e9` / pre-#84 wording.
- Architecture alignment: RM-055 remains satisfied at this head — `transcripts/README.md:54` keeps the em dash; row 5 at `:76` still points at ADR-002 (#79, `20f5f7b`) and states the revision is recorded there, not in this transcript.
- Code quality: n/a (docs-only; 3 files, +222/−4)
- Test quality: CI green on `84b92bc`
- Security / Efficiency: the architecture-lane approval by @xiaolizi33 remains recorded at this head; re-review of the RM-055 items was requested from @creator-xiyuan (recorded in RM-061).
- Operational metadata: review posted 2026-11-23T03:53:35Z; head `84b92bc`, merged on top of `d16c9d4`; squash-merged as `1e2d6db` on 2026-11-23 (04:01:20Z). Hours: 11/23 11:45–11:57, 0.2h.
- Verdict: APPROVE (re-review at `84b92bc`; RM-056 CHANGES REQUESTED resolved) — github.com/CS5351-Group10/contentguard/pull/88#pullrequestreview-6016370475

## RM-059 — PR #89: re-review at `3eb71a9` (final)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author)
- Spec alignment: re-review of the release checklist (method). The first pass (posted under the RM-058 label; chain-linked here) requested two changes: a Report-format section was missing from the checklist, and §3's exclusion assertions were largely tool-guaranteed rather than real checks. Both are closed at `3eb71a9`: §0.1 now states the D6 limits (≤10,000 words, >15 pages at 12 pt single spacing) and requires both numbers in the execution record; §3 now filters the step-2 `git ls-tree` output and states that untracked paths cannot enter a `git archive` (tracked junk is the only way the step can fail).
- Architecture alignment: n/a (docs-only; 4 files, +116/−10). The reviewer also verified the canonical count carried by the same PR: the 4/5 statement matched main at that time (Mei stage-1 absent) and README/Report agreed.
- Code quality: the review confirmed the `.gitignore` premise in §3 (no `.tmp` rule), recorded as a real reminder rather than boilerplate.
- Test quality: n/a; CI double-green on `3eb71a9`
- Security / Efficiency: n/a
- Operational metadata: first review at `7dd2463` (2026-11-23T04:10:05Z, CHANGES REQUESTED, github.com/CS5351-Group10/contentguard/pull/89#pullrequestreview-6016475391); final re-review at `3eb71a9` (2026-11-23T04:36:04Z); merged on top of `1e2d6db`; squash-merged as `dc01ad1` on 2026-11-23 (04:37:55Z). Hours: 11/23 12:10–12:40 0.4h (first pass) + 12:35–12:55 0.3h (re-review).
- Verdict: APPROVE (final) — review 2026-11-23T04:36:04Z; github.com/CS5351-Group10/contentguard/pull/89#pullrequestreview-6016623141

## RM-060 — PR #87: re-review at `40abaa2` (final for RM-054; posted label RM-056, chain-assigned)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author)
- Spec alignment: re-review after the RM-054 fixes. Verified the HUANG ⑤ 2.0h row in `docs/contribution-log.md` — including the "per-review `Hours:` headers are not summed" qualifier that blocks a future 3.9h mis-sum — and the §2 recompute: LIU 46.3 / Mei 4.5 / LI 29.0 / HUANG 24.75 / Buna 11.0, sum 115.55, mean 23.11, weights 2.00 / 0.19 / 1.25 / 1.07 / 0.48; the "weights sum to 5.00 before per-member rounding" note was accepted.
- Architecture alignment: n/a (docs-only; 2 files, +26/−9)
- Code quality: the snapshot pinning at `cc80ef8` (2026-11-22 21:23 HKT) and the "rows reported after that … nothing silently dropped" wording were accepted as converting the table from a claimed result into a dated snapshot.
- Test quality: CI double-green on `40abaa2`
- Security / Efficiency: forward warning recorded (not a defect in this PR): the table is computed from reported totals while Mei ①/③, HUANG ① and Buna ④/⑤ were open cells; any later cell changes all five weights, so the table must be recomputed or the as-of basis stated. The close-out PR carries that statement.
- Operational metadata: review posted 2026-11-22T23:07:41Z; head `40abaa2`, base `bc30315`; squash-merged as `d16c9d4` on 2026-11-23 (03:38:13Z). Hours: 11/23 07:10–07:30, 0.3h.
- Verdict: APPROVE — github.com/CS5351-Group10/contentguard/pull/87#pullrequestreview-6015018094; posted label RM-056 collides with the PM's #88 memo (first-post precedence keeps RM-056 there), chain-assigned RM-060.

## RM-061 — PR #88: re-review at `84b92bc` (final for RM-055; posted label RM-057, chain-assigned)

- Reviewer(s): domain CR creator-xiyuan (HUANG Hongwei; non-author, code-owner)
- Spec alignment: verified RM-055's two points fixed at `84b92bc`: README coverage row 5 anchors the revision in ADR-002 (#79, `20f5f7b`) and states it is not in the transcript; the em dash in `## Inventory —` is restored; the file still carries five `[INTERVENTION]` markers. Independently checked the PM's RM-056 P1: the `9e189e9` "latest main" wording in the transcript and logbook is now the fetched pre-#84 snapshot.
- Architecture alignment: n/a (docs-only; 3 files, +222/−4)
- Code quality: one residual non-blocking wording ("Latest main commit" in the checklist) noted for a future pass; not a merge blocker.
- Test quality: CI double-green on `84b92bc`
- Security / Efficiency: process observation recorded: the review chain stalled on a CR pinned to an older head; a direct "your CR is pinned" note would have saved a re-read.
- Operational metadata: review posted 2026-11-23T03:55:54Z; head `84b92bc`, merged on top of `d16c9d4`; squash-merged as `1e2d6db` on 2026-11-23 (04:01:20Z). Hours: 11/23 11:55–12:15, 0.3h.
- Verdict: APPROVE — github.com/CS5351-Group10/contentguard/pull/88#pullrequestreview-6016382138; posted label RM-057 collides with the ledger's #77 memo, chain-assigned RM-061.
