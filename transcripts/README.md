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

| # | Pipeline stage demonstrated | Owner (annotator) | Status |
|---|---|---|---|
| 1 | Requirements classification | TBD | ⬜ |
| 2 | Architecture candidate generation & evaluation | TBD | ⬜ |
| 3 | Plan approval before code | TBD | ⬜ |
| 4 | Build + verification compliance | TBD | ⬜ |
| 5 | Architecture revision based on test evidence | TBD | ⬜ |

> Every team member must own at least one transcript's interventions (contribution
> evidence for Report.md §2 and D6 weighting).
