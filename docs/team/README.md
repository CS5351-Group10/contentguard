# Team Roster (D6 working file — Report.md §1 feeds from here)

> One card per member: `docs/team/<github-id>.md`. Members add themselves via
> pull request — this is the team's first PR exercise. Per-member files keep PRs
> **conflict-free** (nobody edits the same file). The main-line assignment below is
> the team's agreed fact (proposal §4.2); the PM maintains this index.

## Index

| Main line (proposal §4.2) | Member | Card |
|---|---|---|
| PM — Report, review-memo sign-off, contribution log, demo video, slides | @swordnew123 | [swordnew123.md](swordnew123.md) |
| Requirements — D1 registry + req-schema + policy docs | — | pending |
| Architecture — D2 artifacts (multi-round ADD) + D9 Prompt.md | — | pending |
| Governance & CI — D3 + D7 gates + README + ai-use-log | — | pending |
| Testing — D4 verification governance + D8 suites + bug-diary/debt-register | — | pending |

## Add yourself (first PR exercise)

1. Branch: `git checkout -b roster/<your-github-id>`
2. Copy the template: `cp docs/team/_TEMPLATE.md docs/team/<your-github-id>.md`
3. Fill in the card (name, student ID, main line) — keep exactly the template's fields.
4. Commit (`roster: add <your-github-id>`), push, open a PR to `main`.
   Docs-only PR: **no test-plan marker needed** — gate 1 passes docs-only changes
   automatically; gates 2 (lint/type), 3 (schema) and 5 (regression) run as usual.
5. PM reviews (the first memo lands in `docs/review-memo.md` as RM-001), approves,
   merges, and logs ~0.5 h in `docs/contribution-log.md`.

Final names + student IDs + contributions are transcribed into `Report.md` §1 at
submission; man-hours evidence lives in `docs/contribution-log.md`. No emails in
this directory — the submitted zip carries no PII beyond what D6 requires.
