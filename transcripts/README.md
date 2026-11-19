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
is the one named exactly `<student-id>-<student-name>.md`.

## Annotation convention

Inside the transcript, mark **every human intervention** inline:

```
>>> [INTERVENTION] type: <interrupt|redirect|approve|reject> — by: <member name>
    rationale: <why the team interrupted / redirected / approved / rejected here>
```

The rationale is mandatory (project sheet D5). Choose the intervention point where
the human action actually happened — not where the agent replied.

**Format note:** the HUANG-series transcripts use a tabular "Annotated
interventions" section instead of the inline `>>> [INTERVENTION]` marker; the type
column uses the same four canonical types (`interrupt | redirect | approve |
reject`). This is accepted as equivalent evidence; if inline normalization is
done at all, it must happen before the 11-21 lock.

**Excerpt policy (honesty over volume):** where a full raw dump is unavailable, a
transcript may carry an annotated excerpt set; the file must state at the top that
it is excerpted and what was omitted. Excerpted evidence is still intervention
evidence — it is not a claim of a complete session record.

## Sanitization rule (red line)

Raw transcripts may contain API keys, tokens, or personal paths. **Sanitize before
committing**: replace any credential with `[REDACTED]`. The team reviews each file
before commit (risk RSK-4). Never commit a `.env`/token file — `.gitignore` also
guards this, but sanitization is the human responsibility here.

## Inventory (main, as of 2026-11-20)

| File(s) | Member | Session line | Annotation status |
|---|---|---|---|
| `61022208-LIU-Jianwei.md` | LIU Jianwei (PM) | S1 build; report citation realignment | inline ✓ |
| `60368210-HUANG-Hongwei.md` + `-gate4.md`, `-gate4-strict.md`, `-td2.md`, `-td3.md` | HUANG Hongwei (governance & CI) | gates 2/4, TD-1/TD-2/TD-3 sessions | table format ✓ (see format note) |
| `60914643-HAN-Mei-AI-002.md`, `-AI-006.md` | HAN Mei (requirements) | D1 registry; policy v1 | raw — inline annotation due 11-21 |
| `60105888-DA-Buna-AI003.md`, `-AI004.md`, `-AI012.md` | Buna DA (testing) | evaluation corpus; release acceptance tests | inline ✓; canonical `-DA-Buna.md` lands with S5 |
| `60938585-LI-Shiyi.md` | LI Shiyi (architecture) | S3 analysis slice | lands with PR #52 (annotation attached there) |

## Coverage checklist

| # | Pipeline stage demonstrated | Owner (annotator) | Status |
|---|---|---|---|
| 1 | Requirements classification | HAN Mei | 🟨 raw sessions in repo; inline annotation due 11-21 |
| 2 | Architecture candidate generation & evaluation | LI Shiyi | 🟨 stage-2 evidence record in flight (PR #68); transcript lands with PR #52 |
| 3 | Plan approval before code | LIU Jianwei + HUANG Hongwei | ✅ annotated (S1 plan-approval interventions; gate/plan approvals) |
| 4 | Build + verification compliance | LIU, HUANG, Buna | ✅ annotated (S1 build; governance/CI sessions; acceptance-test session) |
| 5 | Architecture revision based on test evidence | Buna DA + LI Shiyi | ⬜ S5 session scheduled 2026-11-20 (`evaluation-logbook.md` is the linked artifact) |

Collective intervention-type coverage across the canonical set: approve ✓,
redirect ✓, reject ✓, interrupt ✓ (HUANG canonical, "Accidental interruption").
D5 requires the pipeline to be demonstrated **collectively**; per-file four-type
completeness is not required.

> Every team member must own at least one transcript's interventions (contribution
> evidence for Report.md §2 and D6 weighting).
