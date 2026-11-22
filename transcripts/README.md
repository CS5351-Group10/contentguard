# Agent Session Transcripts (D5)

> The full, raw transcripts of OpenCode sessions are the **primary evidence of
> authentic human authorship** (course slide 23). The canonical set is one
> annotated transcript per member (five); collectively the set must demonstrate the
> entire supervised pipeline: requirements classification → architecture
> candidate generation & evaluation → plan approval before code → build →
> verification compliance → architecture revision based on test evidence.
>
> **Lock: 2026-11-21 23:59 HKT.** After the lock, transcripts are frozen; any later
> edit requires a re-verification note in `docs/ai-use-log.yaml`.

## File naming

`<student-id>-<student-name>.md` — one file per annotated transcript; session
series carry a suffix (`-gate4`, `-AI-006`, `-td3`, …). A member's canonical file
is the one named exactly `<student-id>-<student-name>.md`. **LI Shiyi:** resolved
via PR #76 — the canonical `60938585-LI-Shiyi.md` is now the stage-2 candidate
evaluation excerpt (one inline `[INTERVENTION]` marker), and the former S3 build
session lives at `60938585-LI-Shiyi-s3.md` as stage-4 supporting evidence.

## Annotation convention

Inside the transcript, mark **every human intervention** inline:

```
>>> [INTERVENTION] type: <interrupt|redirect|approve|reject> — by: <member name>
    rationale: <why the team interrupted / redirected / approved / rejected here>
```

The rationale is mandatory (project sheet D5). Choose the intervention point where
the human action actually happened — not where the agent replied.

**Format note:** the canonical HUANG transcript now carries the inline
`>>> [INTERVENTION]` markers (PR #73). The supporting HUANG-series transcripts
(`-gate4`, `-gate4-strict`, `-td2`, `-td3`, `-td4`) use a tabular "Annotated
interventions" section whose descriptive types map onto the four canonical types
(`interrupt | redirect | approve | reject`); that tabular form is accepted as
equivalent evidence. If inline normalization is done, it must happen before the
11-21 lock.

**Excerpt policy (honesty over volume):** where a full raw dump is unavailable, a
transcript may carry an annotated excerpt set; the file must state at the top that
it is excerpted and what was omitted. Excerpted evidence is still intervention
evidence — it is not a claim of a complete session record.

## Sanitization rule (red line)

Raw transcripts may contain API keys, tokens, or personal paths. **Sanitize before
committing**: replace any credential with `[REDACTED]`. The team reviews each file
before commit (risk RSK-4). Never commit a `.env`/token file — `.gitignore` also
guards this, but sanitization is the human responsibility here.

## Inventory - the five canonical files (main, as of 2026-11-22 HKT)

| Canonical file | Member | Pipeline stage / session line | Status |
|---|---|---|---|
| `61022208-LIU-Jianwei.md` | LIU Jianwei (PM) | S1 build session (AI-007, CP1–CP6); stage-3/4 markers added in #53 | ✅ inline markers |
| `60368210-HUANG-Hongwei.md` | HUANG Hongwei (governance & CI) | stages 3/4 (plan approval + build/verification); inline markers added in #73 | ✅ inline markers |
| `60914643-HAN-Mei.md` | HAN Mei (requirements) | stage 1 (requirements classification) | ⬜ not yet assembled; `-AI-002`/`-AI-006` are supporting |
| `60938585-LI-Shiyi.md` | LI Shiyi (architecture) | stage 2 (architecture candidate evaluation) | ✅ canonical stage-2 excerpt landed via #76 (one inline marker); S3 build record moved to `-s3.md` |
| `60105888-DA-Buna.md` | Buna DA (testing) | stage 5 (architecture revision on test evidence) | ✅ canonical Stage-5 excerpt with inline intervention markers; `-AI003`/`-AI004`/`-AI012` remain supporting |

## Coverage checklist

State as of 2026-11-22 HKT (issue #50 deadlines: 11/20 23:00 all five final,
11/21 23:59 lock). "✅" means the file exists **and** carries inline `[INTERVENTION]`
markers; a file without markers does not count as done.

| # | Pipeline stage demonstrated | Canonical file | Annotator | Status |
|---|---|---|---|---|
| 1 | Requirements classification | `60914643-HAN-Mei.md` | HAN Mei | ⬜ not present (only `-AI-002` / `-AI-006` supporting files) |
| 2 | Architecture candidate generation & evaluation | `60938585-LI-Shiyi.md` | LI Shiyi | ✅ canonical stage-2 excerpt landed via #76 (annotated, one inline marker); the S3 build record is preserved at `60938585-LI-Shiyi-s3.md` as stage-4 supporting |
| 3 | Plan approval before code | `61022208-LIU-Jianwei.md`, `60368210-HUANG-Hongwei.md` | PM / HUANG Hongwei | ✅ both present, inline markers in place (#73 added HUANG's) |
| 4 | Build + verification compliance | same two files as row 3 | PM / HUANG Hongwei | ✅ both present, inline markers in place |
| 5 | Architecture revision based on test evidence | `60105888-DA-Buna.md` | Buna DA | ✅ canonical Stage-5 excerpt with inline intervention markers; `-AI003` / `-AI004` / `-AI012` remain supporting |

Collective intervention-type coverage across the canonical set: approve ✓,
redirect ✓, reject ✓, interrupt ✓ (HUANG canonical, "Accidental interruption").
D5 requires the pipeline to be demonstrated **collectively**; per-file four-type
completeness is not required.

## Supporting sessions (in the repo, not one of the five)

| File | Session | Why it stays |
|---|---|---|
| `60368210-HUANG-Hongwei-td3.md` | scaffold regeneration (TD-3/TD-8, PR #45) | session evidence for the debt-register payoff; not a pipeline stage |
| `60368210-HUANG-Hongwei-gate4.md` | gate 4 replay harness (PR #47) | idem |
| `60368210-HUANG-Hongwei-gate4-strict.md` | gate 4 `--strict` enforcement (PR #57) | idem |
| `60368210-HUANG-Hongwei-td2.md` | gate 1 tightening (TD-2, PR #61) | idem |
| `60368210-HUANG-Hongwei-td4.md` | TD-4 structural checks, gate 2e (PR #69) | idem |
| `60914643-HAN-Mei-AI-002.md`, `60914643-HAN-Mei-AI-006.md` | requirements validator / tests | idem |
| `60938585-LI-Shiyi-s3.md` | S3 analysis build (PR #52) | original S3 build-session record; preserved as stage-4 supporting after #76 installed the stage-2 canonical excerpt |
| `60105888-DA-Buna-AI003.md`, `60105888-DA-Buna-AI004.md`, `60105888-DA-Buna-AI012.md` | eval corpus build; release acceptance tests | idem |
| `61022208-LIU-Jianwei-AI-017.md` | ADR-002 S1 implementation (AI-017, PR #83) | non-OpenCode agent session (zcode), disclosed per RM-042 |
| `61022208-LIU-Jianwei-AI-018.md` | ADR-002 S1 review-response fix (AI-018, PR #83) | non-OpenCode agent session (zcode), disclosed per RM-042; row and file placed by the session at the PM's explicit instruction (2026-11-22), disclosed in PR #83 |
| `61022208-LIU-Jianwei-AI-019.md` | S2 review-contract alignment + Mei-approved follow-up scope (AI-019, PR #75) | non-OpenCode agent session (zcode), disclosed per RM-042; row and file placed by the session at the PM's explicit instruction (2026-11-22), disclosed in PR #75 |

> PR #76 resolved the naming caveat: the canonical `60938585-LI-Shiyi.md` is the
> stage-2 candidate-evaluation excerpt; the S3 build session is preserved as
> `60938585-LI-Shiyi-s3.md` (stage-4 supporting evidence, also in #76).

> Every team member must own at least one transcript's interventions (contribution
> evidence for Report.md §2 and D6 weighting).
