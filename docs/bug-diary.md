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

## BUG-003 — Engine-minted decision can be tampered after minting and still commit

- Date found: 2026-11-19 | Found by: DA Buna (60105888) / PR #62 review | Fixed in: not fixed — requires separate safety-critical ADR/PR
- Symptom: A `PolicyDecision` returned by `PolicyEngine.evaluate` carries the private authority token. Replacing its outcome/reason via `dataclasses.replace` while preserving `_authority_token` still commits, and the audit row records the tampered outcome.
- Reproduction: mint an `allow/low` decision with `PolicyEngine.evaluate`; run `dataclasses.replace(decision, outcome=Outcome.REJECT, reason_id="RULE-REJECT-VIOLATE", reason_text="tampered")`; call `EnforcementAuthority.commit(...)` with the original case revision and a fresh replay key. Observed result: `COMMITTED`, stored outcome `reject`, reason `RULE-REJECT-VIOLATE`.
- Classification: security / authority boundary / safety-critical
- Root cause: `EnforcementAuthority.commit` verifies only that `_authority_token is _AUTHORITY_TOKEN` (`src/contentguard/policy/enforcement.py:65`); it does not rebind the decision's identity/fields to an engine-produced decision, and `decision_id` remains the pre-tamper digest.
- Fix: Not applied in PR #62 (deliberately out of scope). Proposed: bind the full decision payload at mint time and verify it at commit (recompute/compare `decision_id` or use an opaque minted envelope), or re-evaluate inside the protected write path. Requires ADR addendum + explicit human approval and a negative test proving a replaced token-bearing decision is rejected before any write.
- Invariant gap exposed: REQ-INV-001 was verified for token absence and forged object construction, but not for post-mint field mutation. Add a negative test for `dataclasses.replace` tampering.

## BUG-004 — CommitStatus.PENDING_UNCONFIRMED is declared but unreachable

- Date found: 2026-11-19 | Found by: DA Buna (60105888) / PR #62 review | Fixed in: not fixed — contract decision required
- Symptom: `CommitStatus.PENDING_UNCONFIRMED` exists in `src/contentguard/policy/contracts.py:104`, but no code path emits it; commit returns only `COMMITTED`, `CONFLICT`, or `FAILED`.
- Reproduction: `rg -n 'PENDING_UNCONFIRMED' src test scripts .github` returns only the enum declaration; exercise commit success/conflict/failure paths and observe no `PENDING_UNCONFIRMED` result.
- Classification: contract drift / dead code / audit-status semantics
- Root cause: the enum mirrors the interface-contract status set, but the current persistence path has no "write succeeded but confirmation pending" state; the value was never wired or removed.
- Fix: Not applied in PR #62. Decide with the architecture/policy owner: either implement the pending-confirmation path and document exactly when it is returned, or remove the value and update `docs/architecture/interface-contracts.md`; add a contract test so the enum and emitted statuses stay in lockstep.
- Invariant gap exposed: REQ-INV-004 / REQ-GOV-004 — commit status and audit evidence must be complete and traceable; a declared-but-unreachable status weakens the status contract used by callers and evidence checks.

## BUG-005 — Corpus digest gate fails on Windows checkouts (CRLF vs recorded LF sha256)

- Date found: 2026-11-19 | Found by: LIU Jianwei (PM) / independent verification of PR #69 | Fixed in: not fixed — environmental; needs a line-ending policy decision. Prior attempt: closed PR #1 on `chore/line-endings-policy` (`6e2daf6`) proposes exactly this fix — revive or supersede it rather than opening a duplicate
- Symptom: `test/offline/test_evaluation_dataset.py::test_readme_corpus_hash_matches_file` fails on Windows working copies while Linux CI is green on the same commits. Observed on PR #69's head `fd17f6d` (1 failed / 270 passed) and on a clean `main` checkout (`6f47cc2`) — so it is pre-existing, not introduced by any open PR.
- Reproduction: on Windows with `core.autocrlf=true`, check out `main` and run `python -m pytest "test/offline/test_evaluation_dataset.py::test_readme_corpus_hash_matches_file" -q` → FAILED. The test hashes the corpus with `hashlib.sha256(EVAL_PATH.read_bytes())` (test_evaluation_dataset.py:686) and asserts the digest appears in the eval README.
- Classification: integration / environment (line-ending policy), not product logic
- Root cause: no `.gitattributes` on `main`, so text files are checked out with CRLF on Windows (`core.autocrlf=true`); `read_bytes()` hashes working-copy bytes (CRLF) while the README records the LF blob digest — the assertion cannot pass on a CRLF checkout.
- Fix: not applied here. Candidates: (a) `.gitattributes` pinning LF for corpus/fixture data — closed PR #1 (`chore/line-endings-policy`, `6e2daf6`, closed unmerged 2026-11-15) already proposes `* text=auto eol=lf` + repo-level `autocrlf=false`; review why it was closed, then revive or supersede; (b) hash the Git blob instead of working-copy bytes. Either needs a small PR plus a Windows-checkout verification note.
- Invariant gap exposed: the corpus provenance digest ("REQ-INV-005: README records the actual generated corpus digest") assumes checkout-invariant bytes; the gate is only trustworthy on LF checkouts, so acceptance evidence is platform-dependent. Strengthening: pin line endings for corpus/fixture data so the recorded digest is reproducible on every platform.
