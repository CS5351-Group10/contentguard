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

## BUG-001 — CI gates 1/4/6 failed with 401 on every pull request

- Date found: 2026-11-15 | Found by: HUANG Hongwei (governance & CI) / CI run #18 (PR #2) | Fixed in: PR #7 (`9cd38f7`)
- Symptom: every pull request's `blocking-gates` job died at gate 1 with an `HTTPError` 401 traceback; gates 4 and 6 never ran.
- Reproduction: `GET /repos/CS5351-Group10/contentguard/pulls/2/files` with no `Authorization` header → 200; with `Authorization: Bearer ` (empty token) → 401; with `Bearer xxx` → 401. Gate 1's step had no `GITHUB_TOKEN`, so `os.environ.get("GITHUB_TOKEN", "")` produced an empty token and `pr_files._headers()` emitted the malformed header.
- Classification: integration / CI plumbing (not a product-logic bug)
- Root cause: `scripts/pr_files.py::_headers()` set `Authorization` unconditionally; the workflow passed `GITHUB_TOKEN` only to gate 6.
- Fix: omit the header when the token is blank; raise an actionable `RuntimeError` on API failure; add per-step `GITHUB_TOKEN` for gates 1/4; declare least-privilege `permissions`; add `test/offline/test_pr_files_headers.py` with ID-citing docstrings.
- Invariant gap exposed: REQ-INV-005's audit chain depends on gates actually running; an infrastructure failure silently prevented gate 1/4/6 evidence. Strengthened by fail-closed gate behavior and offline tests for the helper.

## BUG-002 — Requirements registry expanded to 31 but the trace matrix still covered 8

- Date found: 2026-11-16 | Found by: CI run 43816456713 (PR #11) | Fixed in: PR #11 (pending; the 31 matrix rows will be delivered with that PR)
- Symptom: `test/offline/test_smoke.py::test_trace_matrix_covers_every_registry_requirement` failed; 23 registry IDs (REQ-COS-001, REQ-FUN-004..007, REQ-GOV-001..009, REQ-PER-001, REQ-QUA-001..003, REQ-SEC-001..005) were absent from `docs/architecture/trace-matrix.md`.
- Reproduction: in PR #11, run `pytest test/offline -v` (CI gate 5) against the 31-requirement registry; the coverage assertion lists the missing IDs.
- Classification: integration / artifact co-evolution (requirements ↔ architecture)
- Root cause: the requirements baseline changed in PR #11, but the trace matrix is architecture-owned and was not updated in the same change; the only cross-domain check was the offline coverage assertion.
- Fix: add 31 trace-matrix rows (component / test-evidence / runtime monitor) in PR #11; keep the ID-coverage assertion; add a review-checklist item for registry changes and consider extending the existing smoke test to reject `TBD` in released rows (do not add a separate script before deciding).
- Invariant gap exposed: REQ-GOV-004 (trace acceptance evidence) was only partially enforced; the registry and matrix could drift. Strengthened by the same-PR co-evolution rule and the CI coverage test.
