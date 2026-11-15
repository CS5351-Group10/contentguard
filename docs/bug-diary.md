# Bug Diary (D4) — one entry per significant bug

> Symptom → reproduction → classification → root cause → fix → **which invariant gap it
> exposed**. Feed for Report.md §4 defect trends.

## Entry template (copy per bug)

```
## BUG-<NNN> — <short title>
- Date found: | Found by: | Fixed in: PR #<n>
- Symptom: <what was observed>
- Reproduction: <exact steps/inputs>
- Classification: <logic / boundary / concurrency / integration / agent-induced / ...>
- Root cause: <technical cause, not the symptom>
- Fix: <change made + tests added>
- Invariant gap exposed: <which INV/REQ-INV-* verification was missing or weak, and how it was strengthened>
```

## Entries

<!-- Append entries below, newest last. -->
