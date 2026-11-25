# Contribution Log (working file for the D6 relative-contribution table)

> Log man-hours **per phase, same-day, from day one**. The requirement sheet's D6
> allows the team to choose the contribution measure; the team's final decision is
> equal weights (1.00 each, issue #28, 2026-11-25), with these hours retained as the
> raw, append-only effort evidence. The final table lives in `Report.md` §2.
> PM work, review duty, and governance documentation count as real hours — the sheet
> explicitly rewards "difficult tasks and project management". Protocol: § Recording protocol.

## Phase plan (proposal §4.3, agreed 2026-11-15)

| Phase | Dates | Focus | Done |
|---|---|---|---|
| ① Kickoff | 2026-11-15 | topic vote, role claim, repo init, branch protection, ai-use-log | ✅ |
| ② Planning & foundation | 11-16 | requirements final, blueprint + ADR draft, governance drafts, schema gate live, **eval set live** | ✅ (deliverables closed 11-18 via PR #40; hours backfill continued under issue #28) |
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
3. **Hours only.** Spec D6 suggests productive hours (its example uses hrs); story
   points are dropped — a 16-day project does not run sprint planning. The hours are
   retained as the raw effort evidence; the final contribution weights are equal
   (1.00 each) by team decision (issue #28, 2026-11-25) — see the note at the top.
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
| LIU Jianwei | ③ | 11.5 | 11-17 PM coordination 3.0h (test-plan approval #36, data strategy #37, RM-015 #32, cross-checks #26/#27/#28; #34 merge 23:30) + 11-18 8.5h (supervised S1 build session 2.0h, #41 review/merge 3.5h, endgame 3.0h); anchors: PR #41 man-hours comment (backfill rule 6, member-authorized estimate from GitHub timestamps) |
| LIU Jianwei | ③ | 1.6 | 11-19 23:20 → 11-20 00:57 endgame PM batch: #69 independent review (RM-039 CHANGES_REQUESTED) 0.8h + ledger RM-033–039 append on #64 0.6h + BUG-005 #70 + reviewer adds on #63/#64/#65 + #52 AI-014 guidance 0.15h; anchors: issue #28 man-hours comment (backfill rule 6, member-authorized net-hours from GitHub timestamps) |
| HAN Mei | ② | 4.5 | registry/schema + Gate 3 validator suite work (commits 6e45418, 3ea3da5, 62f3c09, PR #11); anchors: issue #28 man-hours comment (2026-11-19) |
| LI Shiyi | ① | 1.5 | member-authorized retrospective estimate (not clock spans; scope: stage-2 candidate evaluation + closeout handoff per evidence file); anchors: issue #28 comment (2026-11-20), `docs/evidence/60938585-closeout-handoff-20261120.md` (PR #76, merge pending) |
| LI Shiyi | ② | 2.5 | supplement to the 5.0h ② row above (② total 7.5h per member-authorized revision; original row preserved); anchors: issue #28 comment (2026-11-20), PR #76 closeout evidence (merge pending) |
| LI Shiyi | ③ | 17.5 | S3 analysis build + review cycle (member-authorized retrospective estimate, not clock spans); anchors: issue #28 comment (2026-11-20), PR #76 closeout evidence (merge pending) |
| Buna DA | ② | 4.0 | member-reported 2026-11-20 (no per-item breakdown given); phase-① entry explicitly not claimed — no verifiable time span, recorded as-is; anchors: issue #28 comment (2026-11-20) |
| Buna DA | ③ | 7.0 | member-reported 2026-11-20 (no per-item breakdown given); anchors: issue #28 comment (2026-11-20) |
| HUANG Hongwei | ④ | 16.0 | 11-18→11-20 endgame governance/CI batch (member-reported with anchors); anchors: issue #28 comment (2026-11-21) |
| HUANG Hongwei | ⑤ | 1.5 | 11-21, member-reported ("so far" — running entry); anchors: issue #28 comment (2026-11-21) |
| LIU Jianwei | ④ | 5.0 | 11-20 11:45–16:53 endgame PM batch: Train A merge train (#65/#70/#52/#68/#73/#64/#71/#74/#63 merged + #43/#66 closed) + #72 refreshed to main `fb629c0` (merge-main, content fix, review request) + #60 governance blocker review + #49 status posts; anchors: issue comments 12:02–16:50 HKT, #49 Train A comments (16:37/16:42 HKT), `HANDOFF.md` session record 11:45–16:53 (backfill rule 6, member-authorized net-hours from GitHub timestamps) |
| LIU Jianwei | ⑤ | 2.0 | 11-21 18:15–20:10 HKT endgame PM batch (running entry): #49 endgame status + #48 Resolution/close + #76 D5 acceptance approve + #75 governance review round 2 + #27 final acceptance run + #77 aggregation PR; anchors: comment timestamps 19:25–20:03 HKT, review `6004899505`, #77 `29111e6` (backfill rule 6, member-authorized net-hours from GitHub timestamps) |
| LI Shiyi | ⑤ | 1.5 | 11-21, member-confirmed net personal effort (retrospective estimate, reported 2026-11-22 via the supervising conversation and posted on issue #28); anchors: PR #75 architecture review/re-review and ownership clarification, PR #79 ADR-002 review/clarification feedback and final-head approval, PR #76 close-out merge, Report §7 reflection review/revision and submission to #27 |
| LI Shiyi | ⑤ | 1.0 | 11-22, PR #84 architecture re-review at head `6bb9b35` (trace/registry evidence check against API and policy tests, real-chain coverage review, FUN-001 P2 evidence-scope qualification, independent 535-test run verification); member-confirmed net estimate reported on PR #84 (2026-11-22 comment; member-stated running total 29.0h — appended as 1.0h only per the member's instruction, not duplicating the 11-21 1.5h row above) |
| LIU Jianwei | ⑤ | 10.2 | 11-21 22:30 → 11-22 20:15 HKT endgame PM tail (rule 6, member-authorized net-hours from GitHub timestamps; unattended AI execution/waiting excluded): (a) §7 reflections assembly → #81 (created 22:48, merged 23:04) 0.6h; (b) #82 banner refresh (created 23:12, merged 01:09) + #83 ADR-002 proposal created 01:10 1.5h; (c) #83 CR round (09:05/09:33) + AI-018 fix-round supervision + double approval/merge 13:11 2.5h; (d) AI-019 S2-alignment supervision + four read-only audit rounds + PR #75 text/comment management + Mei coordination (merge 17:54) + HANDOFF finalization 4.0h; (e) endgame session: #84/#85/#86 + #49/#50/#27 close-out + P2 fix round + merges 1.6h |
| HUANG Hongwei | ⑤ | 2.0 | 11-22, consolidated review rounds on PRs #83/#75/#84/#85 (six review spans, seven review submissions, 09:31–20:15 HKT — the #75 span covers two submissions); member-reported (self) net personal effort — per-review `Hours:` headers are not summed (two span pairs overlap, consolidated figure per the member's reconciliation); anchors: issue #28 comment (2026-11-22T13:18:59Z ≈ 21:18 HKT, posted first per the recording protocol) + review ids 6009400840, 6010496468, 6011484392, 6011567054, 6011928924, 6011934635, 6012101123 |
| HAN Mei | ③ | 12.0 | 11-17–11-20 corrected supplement (net estimate reported on issue #28, 2026-11-22T17:06Z): permanent Gate 3 regression tests and evidence consolidation (#11, #24, AI-006); revised S2 test plan (#51); Community Content Policy v1 update and review feedback (#48, #60); initial S2 API tests (#75) |
| HAN Mei | ④ | 2.0 | 11-21 corrected supplement: regression coverage for duplicate submissions and pending-request recovery; all 51 targeted S2 tests confirmed (PR #75, AI-015) |
| HAN Mei | ⑤ | 1.5 | 11-21 corrected supplement: §7 individual reflection submitted (#27) |
| Buna DA | ③ | 4.5 | 11-19 continuation (itemized on issue #28, 2026-11-22T16:54Z): PR #62 release-acceptance correction and verification (AI-012) |
| Buna DA | ④ | 2.0 | 11-20 member-reported: PR #60/#75 QA, S2/S3 integration status follow-up and S5 evidence preparation; anchors: PR #60/#75, #20, #49 |
| Buna DA | ④ | 3.0 | 11-21 member-reported: latest-main verification, S5 evidence/evaluation-logbook work and canonical transcript draft; anchors: main `9e189e9` (the #75 squash, merged 2026-11-22 17:54 — post-dates the 11-21 label; `[borderline]`, clarification requested), S5 evidence, transcript draft |
| Buna DA | ⑤ | 3.0 | 11-22 member-reported: final transcript/S5 evidence review and close-out; anchors: PR #88, #28, #50 |
| LI Shiyi | ⑤ | 0.5 | 11-22 PR #84 follow-up architecture review (FUN-001 evidence-scope correction); member-confirmed and authorized, posted 2026-11-22T11:54Z |
| LI Shiyi | ⑤ | 0.5 | 11-23 PR #88 architecture re-review at `84b92bc` (Stage-5/ADR-002 evidence boundary; verification-baseline and mypy-wording corrections); member-reported in the review body (2026-11-23T03:40Z, review 6016299785) |
| HUANG Hongwei | ⑤ | 2.2 | 11-22 22:40–23:05 0.4h + 11-23 five spans (00:10–00:45 0.5, 07:10–07:30 0.3, 11:55–12:15 0.3, 12:10–12:40 0.4, 12:35–12:55 0.3) on PRs #87/#88/#89; all six after the existing 2.0h batch's 09:31–20:15 window; consolidated by wall-clock union (`[borderline]` precision exception to rule 7, consistent with LIU 1.6/10.2/3.9 and the earlier 4.25); confirmation requested |
| LIU Jianwei | ⑤ | 3.9 | 11-22 20:15 → 11-23 01:49 HKT endgame takeover tail (rule 6, member-authorized v3): #87 tail continuation, deliverables verification, #88 review and close-out; anchors: issue #28 comment (2026-11-22T18:17Z) |
| LIU Jianwei | ⑤ | 1.2 | 11-23 11:39–12:37 HKT close-out: #89 release-checklist PR authoring/merge 1.0h net (excluding the #88 re-review) + RM-058 #88 re-review 0.2h (11:45–11:57); anchors: #89 PR timestamps, review 6016370475; anchored by the issue #28 close-out comment |
| HAN Mei | ② | 2.0 | 11-25 final report (retrospective): community-guidelines research and initial Community Content Policy; evidence PR #11; anchor: issue #28 comment 2026-11-25T03:04:02Z |
| HAN Mei | ⑤ | 4.0 | 11-25 final report: interactive web demo frontend, offline→live DeepSeek API integration exploration, human-review UI refinement; evidence issue #86; anchor: issue #28 comment 2026-11-25T03:04:02Z |
| HAN Mei | ⑤ | 12.0 | 11-25 final report: demo video structure, narration and editing (baseline vs enhanced comparison); evidence issue #86 + demo video; anchor: issue #28 comment 2026-11-25T03:04:02Z |
| HAN Mei | ⑥ | 0.5 | 11-25 final report: D5 stage-1 canonical transcript cross-check (intervention classifications/rationales); evidence PR #90; anchor: issue #28 comment 2026-11-25T03:04:02Z |
| HAN Mei | ⑥ | 0.5 | 11-25 final report: final Spec §5 / D1/D7 compliance audit (structure, README, Gate 3, traceability, AI-use log); evidence issue #86; anchor: issue #28 comment 2026-11-25T03:04:02Z |
| HUANG Hongwei | ⑤ | 2.0 | 11-25 final report: #92/#90/#91/#95 review passes, 08:25–15:10 HKT (per-review Hours headers not summed; the 11-23 portion is in the existing 2.2h row); anchors: issue #28 comment 2026-11-25T11:18:43Z, reviews 6049708804 / 6052232928 / 6052663370 / 6052855260 / 6053014892 |
| LI Shiyi | ⑤ | 2.0 | 11-25 final report ("11.25补充工时 2h"): Report §3/§5 architecture consistency audit (#93); phase ⑤ assigned by the PM from the task type; anchor: issue #28 comment 2026-11-25T12:33:41Z |
| Buna DA | ⑥ | 6.0 | 11-25 final report: independent submission audit + content suitability (REQ-SEC-005, #94); prior 23.5h → 29.5h; anchor: issue #28 comment 2026-11-25T12:33:48Z |
| LIU Jianwei | ⑥ | 5.0 | 11-25 submission close-out (member-authorized, PM estimate): 12:00–13:08 pre-session #90/#92 review + HANDOFF 1.0h; 13:08–15:10 #90–#95 PR chain (comments/reviews/merges) 2.0h; 15:10–16:20 #86 delta check + freeze/tag + zip build + verify_zip + Report render 1.5h; 20:20–20:50 final hours aggregation + #96 0.5h; waiting/idle excluded; anchors: this session's GitHub comments/reviews/merges, tag `submission-20261125`, zip/verify timestamps |

> Aggregated by the PM on 2026-11-18 00:50 HKT from anchored, member-reported entries.
> LIU's 16.0h covers the #8/#9/#10 report through early 11/16; later phase-②/③ PM work
> (docs PRs #16/#17/#29, reviews) is not yet in the log. Not yet reported: HAN Mei (no
> anchored phase ①/② entry), HUANG Hongwei phase ①, LI Shiyi phase ①, Buna DA phases
> ①/②/③ (onboarding 11-17; no anchored entry). First-batch deadline: 2026-11-18 18:00
> HKT (issue #28). No end-of-phase estimates are inserted here.
> Aggregated by the PM on 2026-11-19 02:55 HKT: LIU Jianwei phase-③ backfill row (11/17 3.0h + 11/18 8.5h = 11.5h) appended per rule 6 (≤48h, anchored, member-authorized net-hours estimate; spans from GitHub activity timestamps; supervised S1 session 01:50–03:40 per `transcripts/61022208-LIU-Jianwei.md`). First-batch deadline was extended to 2026-11-19 12:00 HKT per issue #28. Still not reported: HAN Mei phase ①/②, LI Shiyi phase ① and phase ③ (S3 build 11/18 not yet reported), Buna DA phases ①/②/③, HUANG Hongwei phase ①; phase ③ remains open for all members.
> Aggregated by the PM on 2026-11-20 01:00 HKT: LIU Jianwei phase-③ endgame row (11-19 23:20 → 11-20 00:57 batch, 1.6h = 0.8 + 0.6 + 0.15, rounded up per member authorization) appended per rule 6 (≤48h, anchored, member-authorized net-hours; spans from GitHub activity timestamps; entry posted on issue #28 first). Phase ③ remains open for all members through 11-20.
> Aggregated by the PM on 2026-11-21 19:45 HKT: appended member-reported rows — HAN Mei ② (4.5h), LI Shiyi ①/②-supp/③ (1.5/2.5/17.5h; member-authorized retrospective estimates, not clock spans; the original ② 5.0h row is preserved, supplement appended, ② total 7.5h), Buna DA ②/③ (4.0/7.0h; phase-① explicitly unclaimed — recorded as-is), HUANG Hongwei ④/⑤ (16.0/1.5h). Not reported by the 11-21 15:00 phase-③ deadline: HAN Mei phase ①/③ (kept pending, not estimated — as-reported rule). Still open: LIU Jianwei phase-④/⑤ endgame entries (rule-6 backfill pending self-report), Buna DA phase-④/⑤. `Report.md` §2 refreshed accordingly; weights remain pending until all cells land.
> Supplemented by the PM on 2026-11-21 20:20 HKT: LIU ④/⑤ rows appended per rule 6 (member-authorized net-hours; anchored on GitHub comment/review timestamps and the 11-20 session record in `HANDOFF.md`; ⑤ is a running entry through 20:10 HKT). The 11-21 session that ended before 18:15 HKT left no anchored GitHub activity and is therefore not counted. Still open: HAN Mei ①/③, HUANG ①, Buna ④/⑤.
> Supplemented by the PM on 2026-11-22: LI Shiyi ⑤ row (1.5h for 11-21) appended per rule 6 — member-confirmed retrospective estimate reported on issue #28 (2026-11-21T16:31Z comment, after the 20:20 aggregation above) with anchors (PR #75 review/re-review, PR #79 ADR-002 review and final-head approval, PR #76 close-out merge, Report §7 submission to #27); the member explicitly authorized reporting through the supervising conversation. Still open: HAN Mei ①/③, HUANG ①, Buna ④/⑤, LIU ⑤ tail (11-21 20:10 → session end; rule-6 backfill at session close).
> Supplemented by the PM on 2026-11-22 (evening close-out batch): LI Shiyi ⑤ 1.0h (11-22 PR #84 architecture review; member-reported on PR #84 with stated running total 29.0h — appended as the 1.0h increment only) and LIU ⑤ tail 10.2h (11-21 22:30 → 11-22 20:15, five anchored sub-blocks, rule 6 net-hours) appended. Still open: HAN Mei ①/③, HUANG ①, Buna ④/⑤, HUANG ⑤ tail for 11-22 review work (not yet reported — if unreported at #28 close it stays a recorded open cell, no estimate inserted). `Report.md` §2 aggregation synced in the same PR; #28 closes after this lands.
> Supplemented by the PM on 2026-11-22 (night, PR #87 review round): HUANG Hongwei ⑤ row (2.0h, 11-22 consolidated review batch) appended — member-reported (self), anchored, appended per rule 6; on issue #28 (2026-11-22T13:18:59Z ≈ 21:18 HKT) with six anchored review spans (seven review submissions), per-review `Hours:` headers not summed per the member's own reconciliation (two span pairs overlap), consolidated figure 2.0h used; supersedes the "HUANG ⑤ tail not yet reported" line above. Also posted on issue #28 after the aggregation snapshot head (`cc80ef8`, 21:23 HKT) — to land as-reported in the next close-out PR before the submission freeze, nothing silently dropped: HAN Mei phase-③ supplement (2026-11-22T13:41:04Z; itemized 11.0h, member-stated total 15.5h including "S2 testing entries" — figure to be confirmed with the member at aggregation), Buna DA phase-③ continuation 9.5h + phase-⑤ 3.0h (2026-11-22T13:59:35Z), and the PR #87 reviewer's own 0.4h review entry (22:40–23:05 HKT, PR review body). Still open: HAN Mei ①, HUANG ①, Buna ④.

> **Close-out aggregation — 2026-11-25 01:00 HKT.** Appended after the 11/24 soft
> cutoff: HAN Mei ③–⑤ (15.5h, corrected breakdown 2026-11-22T17:06Z); Buna DA ③
> continuation 4.5h, ④ 2.0 + 3.0 = 5.0h and ⑤ 3.0h (itemized 23.5h — reply "A"
> reads as option (a); the stated 28.5h total double-counts the 5.0h moved from ③
> to ④; the 11-21 3.0h anchor discrepancy is flagged `[borderline]`); LI Shiyi ⑤ +1.0h (two
> 0.5h review entries); HUANG Hongwei ⑤ +2.2h (six review-body spans, wall-clock
> union, `[borderline]` precision exception); LIU Jianwei ⑤ +3.9h (v3 tail) and
> +1.2h (11-23 close-out: #89 1.0h net + RM-058 0.2h). Open cells remain as-is:
> Mei ① and demo-recording hours, HUANG ①; Buna ① remains `unclaimed`.
> `Report.md` §2 is recomputed in the same PR (mean 30.37h); the final weights are
> equal at 1.00 each by team decision (issue #28, 2026-11-25), with the hours retained
> as the raw effort evidence.

> **Final 11-25 reports (pre-submission).** Appended from issue #28 after the
> 01:00 HKT close-out: HAN Mei +19.0h (② 2.0; ⑤ 4.0 demo frontend + 12.0 demo
> video; ⑥ 0.5 D5 canonical + 0.5 Spec §5 audit) → 39.0h cumulative; HUANG
> Hongwei ⑤ +2.0h (11-25 review passes; the 11:18Z consolidation supersedes the
> interim 05:20Z 2.0h figure) → 28.95h cumulative; LI Shiyi ⑤ +2.0h (11-25
> close-out report; phase ⑤ assigned by the PM from the task type) → 32.0h;
> Buna DA ⑥ +6.0h (11-25 independent submission audit, REQ-SEC-005) → 29.5h;
> LIU Jianwei ⑥ +5.0h (11-25 submission close-out: 1.0h pre-session reviews +
> 2.0h PR chain/merges + 1.5h delta check/freeze/zip/verify + 0.5h final hours
> aggregation; waiting excluded) → 56.4h. Recomputed totals: LIU 56.4 / Mei 39.0 /
> LI 32.0 / HUANG 28.95 / Buna 29.5; mean 37.17h. The final weights remain
> **equal at 1.00 each** by team decision (issue #28); hours are the raw effort
> evidence, not the ratio. Mei's demo-recording hours are now reported; open
> cells remain Mei ①, HUANG ①, Buna ① (`unclaimed`).

## CR assignment log (domain-assigned review, proposal §4.2)

| PR # | Domain | Assigned CR (non-author) | PM sign-off | Arch co-sign (safety-critical) |
|---|---|---|---|---|
| — | — | — | — | — |

> Status (2026-11-20): the authoritative domain-CR record is the Reviewer/domain
> column of each memo in `docs/review-memo.md`. Main carries RM-001–RM-040 after
> PR #64 (`3cfdbc9`). Backfilling the domain assignments into
> this index before the 11-21 lock is not scheduled — this table stays an
> index-only view and is populated at the D6 aggregation only if the report needs it.

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
| 2026-11-21 | Endgame man-hours aggregation into `Report.md` §2 via PR #77 / issue #28 (partial: Mei ①/③ not reported, LIU ④/⑤ backfill pending, Buna ① unclaimed / ④/⑤ open — open cells recorded as-is, no estimates inserted) | D6 evidence chain: aggregation happens after the 11-21 15:00 phase-③ deadline; late entries go in as-reported with a note (issue #28). |
| 2026-11-21 | LIU phase-④/⑤ backfill rows appended (rule 6: member-authorized, anchored on GitHub timestamps + the 11-20 session record; ⑤ running) via this PR, merged after PR #77's approved head — a separate PR by design, so no commit lands after a reviewer's approval | Completes the PM's own §2 cells without re-triggering the #39 author-merge incident pattern; the 11-21 pre-18:15 session has no anchored activity and is not counted. |
