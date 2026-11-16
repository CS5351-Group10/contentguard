# Team Roster (D6 working file — Report.md §1 feeds from here)

> One card per member: `docs/team/<student-id>-<name>.md` (same naming convention
> as the D5 transcripts). Members add themselves via pull request — this is the
> team's first PR exercise. Per-member files keep PRs **conflict-free** (nobody
> edits the same file). The main-line assignment below is the team's agreed fact
> (proposal §4.2); the PM maintains this index. Name + student ID are the roster's
> primary key; GitHub IDs are kept for commit attribution and access control only.

## Index

| Main line (proposal §4.2) | Member | Card | GitHub |
|---|---|---|---|
| PM — Report, review-memo sign-off, contribution log, demo video, slides | LIU Jianwei (61022208) | [61022208-LIU-Jianwei.md](61022208-LIU-Jianwei.md) | @swordnew123 |
| Requirements — D1 registry + req-schema + policy docs | HAN Mei (60914643) | pending (PR #11) | @Mei-github |
| Architecture — D2 artifacts (multi-round ADD) + D9 Prompt.md | LI Shiyi (60938585) | [60938585-LI-Shiyi.md](60938585-LI-Shiyi.md) | @xiaolizi33 |
| Governance & CI — D3 + D7 gates + README + ai-use-log | HUANG Hongwei (60368210) | [60368210-HUANG-Hongwei.md](60368210-HUANG-Hongwei.md) | @creator-xiyuan |
| Testing — D4 verification governance + D8 suites + bug-diary/debt-register | Buna DA | pending onboarding | — |

## Add yourself (first PR exercise)

1. Branch: `git checkout -b roster/<your-student-id>`
2. Copy the template: `cp docs/team/_TEMPLATE.md docs/team/<student-id>-<name>.md`
   (`<name>` = pinyin/English name, no spaces — same convention as the D5
   transcript files, e.g. `61022208-LIU-Jianwei.md`)
3. Fill in the card (name, student ID, main line, GitHub ID) — keep exactly the
   template's fields.
4. Commit (`roster: add <student-id>`), push, open a PR to `main`.
   Docs-only PR: **no test-plan marker needed** — gate 1 passes docs-only changes
   automatically; gates 2 (lint/type), 3 (schema) and 5 (regression) run as usual.
5. PM reviews (the reviewer's memo lands in `docs/review-memo.md` with the next RM
   number), approves, merges, and logs ~0.5 h in `docs/contribution-log.md`.

Final names + student IDs are transcribed into `Report.md` §1 (roster), and the
relative-contribution table into §2, at submission; man-hours evidence lives in
`docs/contribution-log.md`. No emails in
this directory — the submitted zip carries no PII beyond what D6 requires.
