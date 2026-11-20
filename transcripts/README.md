# Agent Session Transcripts (D5)

> The full, raw transcripts of OpenCode sessions are the **primary evidence of
> authentic human authorship** (course slide 23). Five annotated transcripts are
> submitted; collectively they must demonstrate the entire supervised pipeline:
> requirements classification → architecture candidate generation & evaluation →
> plan approval before code → build → verification compliance → architecture
> revision based on test evidence.

## File naming

`<student-id>-<student-name>.md` — one file per annotated transcript.

## Annotation convention

Inside the transcript, mark **every human intervention** inline:

```
>>> [INTERVENTION] type: <interrupt|redirect|approve|reject> — by: <member name>
    rationale: <why the team interrupted / redirected / approved / rejected here>
```

The rationale is mandatory (project sheet D5). Choose the intervention point where
the human action actually happened — not where the agent replied.

## Sanitization rule (red line)

Raw transcripts may contain API keys, tokens, or personal paths. **Sanitize before
committing**: replace any credential with `[REDACTED]`. The team reviews each file
before commit (risk RSK-4). Never commit a `.env`/token file — `.gitignore` also
guards this, but sanitization is the human responsibility here.

## Coverage checklist (for the five final transcripts)

State as of 2026-11-20 14:00 HKT (issue #50 deadlines: 11/20 23:00 all five final,
11/21 23:59 lock). "✅" means the file exists **and** carries inline `[INTERVENTION]`
markers; a file without markers does not count as done.

| # | Pipeline stage demonstrated | Canonical file | Annotator | Status |
|---|---|---|---|---|
| 1 | Requirements classification | `60914643-HAN-Mei.md` | HAN Mei | ⬜ not present (only `-AI-002` / `-AI-006` supporting files) |
| 2 | Architecture candidate generation & evaluation | `60938585-LI-Shiyi.md` | LI Shiyi | ⬜ not present (the S3 build session in #52 is stage-4 evidence only) |
| 3 | Plan approval before code | `61022208-LIU-Jianwei.md`, `60368210-HUANG-Hongwei.md` | PM / HUANG Hongwei | ✅ both present, inline markers in place |
| 4 | Build + verification compliance | same two files as row 3 | PM / HUANG Hongwei | ✅ both present, inline markers in place |
| 5 | Architecture revision based on test evidence | `60105888-DA-Buna.md` | Buna DA | ⬜ not present (only `-AI003` / `-AI004` supporting files) |

## Supporting sessions (in the repo, not one of the five)

| File | Session | Why it stays |
|---|---|---|
| `60368210-HUANG-Hongwei-td3.md` | scaffold regeneration (TD-3/TD-8, PR #45) | session evidence for the debt-register payoff; not a pipeline stage |
| `60368210-HUANG-Hongwei-gate4.md` | gate 4 replay harness (PR #47) | idem |
| `60368210-HUANG-Hongwei-gate4-strict.md` | gate 4 `--strict` enforcement (PR #57) | idem |
| `60368210-HUANG-Hongwei-td2.md` | gate 1 tightening (TD-2, PR #61) | idem |
| `60914643-HAN-Mei-AI-002.md`, `-AI-006.md` | requirements validator / tests | idem |
| `60105888-DA-Buna-AI003.md`, `-AI004.md` | eval corpus build | idem |

> Every team member must own at least one transcript's interventions (contribution
> evidence for Report.md §2 and D6 weighting).
