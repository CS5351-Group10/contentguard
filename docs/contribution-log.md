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

## Recording protocol (set by PM 2026-11-15; open for objection at any stand-up)

Set before the first logged entry — no historical hours are rewritten.

1. **Per-phase cadence, not weekly.** The project spans 11-15 → 11-30, so weekly logging
   would give only ~2 data points. Members report at every phase close (table above); the
   PM aggregates into the man-hours log at the same cadence.
2. **Same-day capture.** Hours are reported to the PM the day they are spent (one line:
   date, span, what, hours — stand-up or group chat). End-of-phase recall estimates are
   not accepted. Cross-check anchors at phase close: git commit timestamps, the five
   locked transcripts (due 11-21), and `docs/ai-use-log.yaml`.
3. **Hours only.** Spec D6 computes weights from productive hours (its example uses hrs);
   story points are dropped — a 16-day project does not run sprint planning.
4. **What counts (pre-agreed).** Build, testing, debugging, CR/review duty, memos,
   governance docs, stand-ups, PM coordination, demo/slides work, and required reading
   all count. General course study unrelated to this project does not. Borderline items
   are logged and flagged at aggregation, not dropped.
5. **Defensible granularity.** Every What entry must be verifiable against commits,
   memos, or transcripts ("2.5h: review PR#7 + sign-off memo") — never "worked on project".

## Man-hours log (append per phase)

| Member | Phase | Hours | What |
|---|---|---|---|
| — | — | — | — |

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
