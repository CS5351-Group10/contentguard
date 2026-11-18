# Contribution Log (working file for the D6 relative-contribution table)

> Log man-hours **per phase, same-day, from day one** (the requirement sheet's D6
> method computes each member's weight = individual total / mean total). The final
> table lives in `Report.md` §2; this file is the raw, append-only evidence.
> PM work, review duty, and governance documentation count as real hours — the sheet
> explicitly rewards "difficult tasks and project management". Protocol: § Recording protocol.

## Phase plan (proposal §4.3, agreed 2026-11-15)

| Phase | Dates | Focus | Done |
|---|---|---|---|
| ① Kickoff | 2026-11-15 | topic vote, role claim, repo init, branch protection, ai-use-log | ✅ |
| ② Planning & foundation | 11-16 | requirements final, blueprint + ADR draft, governance drafts, schema gate live, **eval set live** | ⬜ |
| ③ Build (sessions 1–4) | 11-17 → 11-20 | deterministic core, RAG/LLM components, permission model, gates online | ⬜ |
| ④ Refine & evaluate | 11-20 → 11-21 | semantic eval gate live, negative tests + architecture revision — **locked 11-21 23:59** | ⬜ |
| ⑤ Final sprint | 11-22 → 11-24 | report, transcripts annotated (all 5 complete by **11-21 23:59**), demo video, slides | ⬜ |
| ⑥ Deliver & present | 11-25, 11-29, 11-30 | submit zip + video (25th 23:59 HKT, Canvas lock 11/27); slides to TA (29th); presentation **11/30 17:00–17:30, Group 10, YEUNG B5-210** (talk ≤20 min) | ⬜ |

> Deadline source (Canvas, confirmed 2026-11-15): "Project (Zip file)" and
> "Project (Demo Video)" both due **2026-11-25 23:59 HKT**. Zip must NOT contain the
> demo video (sheet slide 23). Phase calendar from team proposal §4.3.

## Recording protocol (set by PM 2026-11-15; amended 2026-11-16 — see the amendment note below; open for objection in PR comments or directly to the PM)

Set before the first logged entry — no historical hours are rewritten.

> Amendment (2026-11-16, PM, before the first logged entry): hours are now reported
> PR-natively — in the description or comments of the PR that carries the work; work
> with no PR goes in the most closely related PR's comments. Urgent/blocking signals
> still go to the group chat; hour figures do not. Rationale: the audit chain stays
> next to the reviewed diff, so every entry anchors to reviewed changes.

1. **Per-phase cadence, not weekly.** The project spans 11-15 → 11-30, so weekly logging
   would give only ~2 data points. Members report at every phase close (table above); the
   PM aggregates into the man-hours log at the same cadence.
2. **Same-day capture.** Hours are reported to the PM the day they are spent (one line:
   date, span, what, hours — PR-native: in the description or comments of the PR that
   carries the work; work that produces no PR is reported in the comments of the most
   closely related PR). End-of-phase recall estimates are not accepted. Cross-check
   anchors at phase close: git commit timestamps, the five locked transcripts
   (due 11-21), and `docs/ai-use-log.yaml`.
3. **Hours only.** Spec D6 computes weights from productive hours (its example uses hrs);
   story points are dropped — a 16-day project does not run sprint planning.
4. **What counts (pre-agreed).** Build, testing, debugging, CR/review duty, memos,
   governance docs, stand-ups, PM coordination, demo/slides work, and required reading
   all count. General course study unrelated to this project does not. Borderline items
   are logged and flagged at aggregation, not dropped.
5. **Defensible granularity.** Every What entry must be verifiable against commits,
   memos, or transcripts ("2.5h: review PR#7 + sign-off memo") — never "worked on project".

Rules 6–9 added 2026-11-16 (PM), same amendment window — still before the first logged
entry, so nothing below rewrites any recorded hours.

6. **Backfill.** The initial backfill (pre-protocol days, before the first logged entry)
   is legitimate and is marked as such in the entry. A missed same-day report may be
   backfilled within 48h **if anchored** (commits / PR / records). Later than that: log
   it anyway, flagged as a phase-close estimate — never silently rewritten.
7. **Net hours.** Report net productive time: subtract work for other courses done in
   parallel; short breaks count, distinct non-project work blocks don't. Round to 0.5h.
8. **AI-assisted logging is allowed.** Having an AI session draft or submit your
   man-hours entry is fine — this is an Agentic SE course, and supervising AI is itself
   reportable work (rule 4). Cite the anchor as "session records".
9. **No-PR work, terminal fallback.** Report in the PR that carries the work; if none
   does, in the most closely related PR's comments; if nothing relates (reading,
   discussions, stand-ups, design sketches), hold the entries and report them in the
   comments of the phase-close **aggregation PR** — the PM opens one at every phase
   close to update the Man-hours log table, and it accepts orphan entries.

## Filling template (copy-paste per entry; live examples: the PM's man-hours comments on PR #8 / #9 / #10, 2026-11-16)

- 2026-11-16, 14:00–16:30, <what — verifiable against commits/PRs/records>, <anchors:
  commit short-hash(es) / PR # / "session records"> — **2.5h**

- One bullet per work block, per day; span is local time (HKT, UTC+8).
- Hours rounded to 0.5h; flag edge items with `[borderline]` — logged and flagged at
  aggregation, not dropped (rule 4).
- End each PR's report with a running-total line.
- Language: keep the skeleton fields (date, span, hours, anchors) in English; the What
  text may be Chinese — the PM normalizes wording at aggregation.

## Man-hours log (append per phase)

| Member | Phase | Hours | What |
|---|---|---|---|
| LIU Jianwei | ① | 12.5 | 11-14 proposal authoring 3.5h + 11-15 repo kickoff/governance 9.0h; anchors: PR #8 man-hours comment |
| LIU Jianwei | ② | 3.5 | 11-16 man-hours protocol + RM-002 backfill + CONTRIBUTING guide (incl. 0.3h [borderline] session wrap-up); anchors: PR #8/#9/#10 comments |
| LI Shiyi | ② | 5.0 | 11-16 architecture blueprint, ADR-001, module interface contracts; anchor: PR #15 body |
| HUANG Hongwei | ② | 4.25 | 11-16 PR #8 re-review 2.0h + PR #17 domain review/debt register 2.0h + PR #30 review follow-up 0.25h; anchors: PR #8/#17/#30 comments |
| HUANG Hongwei | ③ | 1.0 | 11-17 #33 rebase/review fixes 0.5h + #37 data-governance answers 0.5h; anchors: PR #33/#37 comments |
| LIU Jianwei | ③ | 11.0 | 11-17 PM coordination 2.5h (test-plan approval #36, data strategy #37, RM-015 #32, cross-checks #26/#27/#28, merge #34) + 11-18 8.5h (supervised S1 build session 2.0h, #41 review/merge 3.5h, endgame 3.0h); anchors: PR #41 man-hours comment (backfill rule 6, member-authorized estimate from GitHub timestamps) |

> Aggregated by the PM on 2026-11-18 00:50 HKT from anchored, member-reported entries.
> LIU's 16.0h covers the #8/#9/#10 report through early 11/16; later phase-②/③ PM work
> (docs PRs #16/#17/#29, reviews) is not yet in the log. Not yet reported: HAN Mei (no
> anchored phase ①/② entry), HUANG Hongwei phase ①, LI Shiyi phase ①, Buna DA phases
> ①/②/③ (onboarding 11-17; no anchored entry). First-batch deadline: 2026-11-18 18:00
> HKT (issue #28). No end-of-phase estimates are inserted here.
> Aggregated by the PM on 2026-11-19 02:30 HKT: LIU Jianwei phase-③ backfill row (11/17 2.5h + 11/18 8.5h = 11.0h) appended per rule 6 (≤48h, anchored, member-authorized net-hours estimate; spans from GitHub activity timestamps; supervised S1 session 01:50–03:40 per `transcripts/61022208-LIU-Jianwei.md`). First-batch deadline was extended to 2026-11-19 12:00 HKT per issue #28. Still not reported: HAN Mei (phase ①/②), Buna DA (phase ①/②), LI Shiyi phase ①, HUANG Hongwei phase ①.

## CR assignment log (domain-assigned review, proposal §4.2)

| PR # | Domain | Assigned CR (non-author) | PM sign-off | Arch co-sign (safety-critical) |
|---|---|---|---|---|
| — | — | — | — | — |

> Rule: no member self-certifies their own hours at phase close — the PM aggregates
> from this log at every phase close, so the final table is defensible.

## Governance events (append-only)

| Date | Event | Rationale |
|---|---|---|
| 2026-11-15 | Repo transferred `swordnew123/contentguard` → `CS5351-Group10/contentguard`; visibility private → public | Personal repos cannot grant repo-admin to collaborators; the org enables repository-admin roles for CI governance. Public keeps protected branches free on the org's Free plan (private → Free org would drop them) — rules verified intact after transfer (strict `blocking-gates` + 1 review + enforce-admins + linear history). Side effect accepted by PM: roster cards (student IDs) are now publicly readable. |
| 2026-11-15 | Old-URL redirect deliberately retired (PM decision — new link re-announced to the team) | The transferred-repo redirect was broken by recreating the repository name at the old location; an empty private placeholder remains at `swordnew123/contentguard` pending manual deletion via web UI (API token lacks `delete_repo` scope). All members must update remotes to `github.com/CS5351-Group10/contentguard.git` — the old URL now 404s for outsiders. |
| 2026-11-15 | Repository-admin granted to @creator-xiyuan (repo-level only; not an org owner) | Member's CI governance need; repo-scoped role keeps blast radius to this repository. |
| 2026-11-16 | PR #2 merged without a review memo; RM-002 backfilled post-merge via PR #9 (see `docs/review-memo.md` RM-002) | First breach of the memo-before-merge rule (2026-11-15); enforcement gap → Gate 7 (issue #4) closes it machine-side. |
| 2026-11-16 | Man-hours recording protocol v1.1 (this PR, `0c3e07e`): Filling template section + rules 6–9 (backfill, net-hours, AI-assisted logging, no-PR terminal fallback) + downstream sync (`Report.md` §2 per-phase hours-only columns; two stale `Report.md` §1 → §2 refs in README.md / docs/team/README.md; story-points wording dropped) | First-fill dry run (the PM's own 16h report across #8/#9/#10) exposed the gaps: no template, no backfill clause, net-hours undefined, orphan entries with no terminal home, and stale weekly/story-points wording surviving downstream. Rules 1–5 untouched — already cited by the posted entries. |
| 2026-11-16 | Review-memo ledger finalized: RM-005..RM-011 appended after PR #8 merged (RM-004); provisional reviewer labels mapped in the ledger's 2026-11-16 note | D4 audit chain: reviewers post memos in PR threads, but the ledger needs one authoritative, collision-free sequence; #5/#10 provisional labels were renumbered where they collided |
| 2026-11-16 | Repository permission: @Mei-github read → write (PM-authorized; executed via gh api from the PM workstation; verified permission=write, no pending invitation) | Requirements owner needs an org branch to run gate 4 with CI secrets; write is the minimum role (no admin granted). |
| 2026-11-17 | PR #11: @Mei-github implemented the permanent Gate 3 requirements-validator test suite following the Testing Lead-approved Issue #24 test plan (AI-006, session `ses_e170e175cffeErOe3BcXI8zqed`); added 10 named test functions (12 pytest items), completed offline regression testing (20/20 passed), and validated all 31 requirements successfully. | REQ-GOV-003 and REQ-GOV-004 evidence: `test/offline/test_validate_requirements.py`, `test/offline/test-gate3-report.md`, `transcripts/60914643-HAN-Mei-AI-006.md`. Implementation and local verification completed. |
| 2026-11-18 | Phase ② man-hours first batch aggregated (partial: 3 of 5 members anchored; `Report.md` §2 weights pending) via PR #40 / issue #28 | D6 evidence chain: the phase-② close needs per-phase hours; unreported cells stay `pending` rather than being estimated, and the 18:00 HKT deadline remains open for the remaining members. |
