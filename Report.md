# Report.md — Process Report (D6)

> **Status: DRAFT skeleton.** Final report: ≤ 10,000 words (excluding diagrams),
> more than 15 pages, single-line spacing. Written progressively; sections marked TBD.

## 1. Team

| Name | Student ID | Role(s) |
|---|---|---|
| LIU Jianwei | 61022208 | Team lead / PM — report, review-memo sign-off, contribution log, demo video, slides |
| HAN Mei | 60914643 | Requirements — D1 registry/schema, policy sources |
| LI Shiyi | 60938585 | Architecture — D2 artifacts, D9 Prompt.md |
| HUANG Hongwei | 60368210 | Governance & CI — D3 governance files, D7 blocking gates, README, ai-use-log |
| Buna DA | 60105888 | Testing — D4 verification governance, D8 test suites, bug-diary/debt-register |

> DRAFT — roster cards live in `docs/team/`; the final table is transcribed and
> rechecked at submission. Public roster IDs were accepted by the PM on 2026-11-15 (see
> `docs/contribution-log.md` governance events).

## 2. Relative contributions

Computed from productive man-hours logged per phase (hours only; no story points) in
`docs/contribution-log.md` — members report PR-natively per its recording protocol; the
PM aggregates at every phase close. Method (requirement sheet D6): average contribution
= 1.0; weight = individual total / mean total. Final table goes here; the raw,
append-only log and the recording protocol live in `docs/contribution-log.md`.

| Member | Ph ① | Ph ② | Ph ③ | Ph ④ | Ph ⑤ | Ph ⑥ | Total | Weight |
|---|---|---|---|---|---|---|---|---|
| LIU Jianwei (61022208) | 12.5 | 3.5 | | | | | 16.0 | pending |
| HAN Mei (60914643) | pending | pending | | | | | pending | pending |
| LI Shiyi (60938585) | pending | 5.0 | | | | | 5.0 | pending |
| HUANG Hongwei (60368210) | pending | 4.25 | 1.0 | | | | 5.25 | pending |
| Buna DA (60105888) | pending | pending | pending | | | | pending | pending |

> Interim aggregation as of 2026-11-18 00:50 HKT from anchored entries in
> `docs/contribution-log.md`; `pending` = no anchored phase-①/② report yet. Weights are
> computed only after all first-batch entries land (deadline 2026-11-18 18:00 HKT,
> issue #28). LIU's phase ① includes the 11-14 proposal-authoring backfill (3.5h) plus
> the 11-15 kickoff (9.0h). Known phase-③ entries (HUANG #33/#37) are included; phase ③
> is still in progress. See the Man-hours log for anchors.

## 3. Software engineering process and how we optimized it

TBD — narrative of the supervised agentic pipeline: requirements classification →
architecture candidate generation & evaluation → plan approval before code → build →
verification compliance → architecture revision based on test evidence (this is exactly
what the D5 transcripts must collectively demonstrate).

## 4. Process quality evidence

TBD — requirement volatility (registry change log), defect trends (from
`docs/bug-diary.md`), ambiguity resolution (from review memos / transcripts).

## 5. Artifact co-evolution

TBD — how requirements ↔ architecture ↔ code ↔ tests stayed consistent when anything
changed (trace matrix updates, phase-end registry revalidation).

## 6. What human oversight caught that the agent did not

TBD — concrete cases harvested from `docs/review-memo.md` verdicts and the annotated
interventions in `transcripts/`. This section is graded evidence; collect cases from
PR #1 onward.

## 7. Member self-reflections

One short paragraph (300–500 words) per member, with name and student ID.

### TODO (Name, ID)
TBD

### TODO (Name, ID)
TBD
