# Release checklist (submission zip)

Authoritative procedure for building and verifying the Canvas submission zip
(`REQ-SEC-005`; trace-matrix evidence cell `release checklist + secret scan`).
This file is the checklist itself; the executed result record is appended to the
"Execution record" section after the zip is built.

Deadline source: `docs/contribution-log.md` — Canvas "Project (Zip file)" and
"Project (Demo Video)" are both due 2026-11-25 23:59 HKT; the zip must NOT contain
the demo video (sheet slide 23); no API keys in the submission.

## 0. Spec conformance (course project sheet §5)

- Required structure present: `README.md`, `AGENTS.md`, `architecture-blueprint.md`,
  `Prompt.md`, `Report.md`; `docs/req/{requirements.yaml, req-schema.json}`;
  `docs/architecture/` (ADR, invariants, trace-matrix, memory-design,
  permission-model, evaluation-table, runtime-policy-catalog, evaluation-logbook,
  risk-list, interface-contracts, option-ledger); `docs/code-governance/`
  (structural-constraints,
  verification-constraints, mcp-tool-manifest); `docs/{ai-use-log.yaml,
  review-memo.md, debt-register.md, bug-diary.md}`; `.opencode/{permissions.jsonc,
  rules.md}`; `.agent/rules.md`; `.github/workflows/ci.yml`;
  `prompts/{prompt_v1.0.yaml, prompt_v1.1.yaml}`; `src/`; `test/{offline, live}`;
  `transcripts/student-id-<student-name>.md`.
- README four required items: purpose + architecture; project file organization;
  how to run the offline tests, the live tests, and the full suite; the GitHub
  repo URL.
- D5 canonical annotated transcripts, one per member (5 expected; all five are
  present — stage 1 landed post-lock via #90 with the re-verification note in
  `docs/ai-use-log.yaml`; the canonical set and its disposition are recorded in
  the execution record).
- AI-use log up to date at submission (submission-model hard requirement).

## 0.1 Report format (D6)

`Report.md` must contain at most 10,000 words excluding diagrams and render to
more than 15 pages in 12-point font with single-line spacing (course sheet D6:
"more than 15 pages in Point 12 with single-line spacing"). Measure both before
the freeze: `wc -w` for words (record the counting convention used for code
fences and diagrams) and a page-count render at 12 pt/single spacing with the
reviewed heading and table structure unchanged. Record both numbers in the
execution record.

## 1. Freeze

Record the snapshot sha (`git ls-remote origin main`) and the build timestamp.
All planned merges must be complete before freezing; any later main change
invalidates the manifest reconciliation in step 2.

## 2. Build + manifest reconciliation

`git -c core.autocrlf=false archive --format=zip -o <name>.zip <sha>`; then list
the archive (`tar -tf`, or PowerShell `Expand-Archive`) and reconcile against
`git ls-tree -r --name-only <sha>` — names and counts must match exactly (±0).

The `core.autocrlf=false` flag is mandatory on Windows checkouts: without it the
archive smudges text blobs to CRLF, which changes `test/eval/moderation_eval.jsonl`
bytes and breaks the REQ-INV-005 corpus-digest check
(`test_readme_corpus_hash_matches_file`) that gate 5 runs in CI on LF blobs
(rehearsed and verified 2026-11-22).

## 3. Exclusion assertions

Using the step-2 `git ls-tree -r --name-only <sha>` output, match each path by
substring or path component (directory names as components) and require no hit
on: `*.mp4` / `*.mov` / `*.webm` / `*.mkv` / `*.avi` (demo video, sheet slide
23); `*.sqlite3` / `*.db`; `.env` / `*.env` / `.env.*` / `token.txt` / `*.token`
/ `*_token.json` (the `.gitignore` red-line block); `__pycache__/`; `.venv/`;
`node_modules/`; `*.log`.

`git archive` cannot include untracked paths (`.venv/`, `__pycache__/`, a local
`.tmp/`), so untracked paths need no assertion; tracked junk is the only way this
step can fail. `.git/` is structurally impossible in a tree listing and is not
asserted. The repository `.gitignore` does not currently list `.tmp/` — if the
team keeps temporary artifacts there, keep them untracked or add the ignore rule
after submission.

## 4. Secret scan (REQ-SEC-005)

Full-text regex scan of the extracted tree for known credential formats
(`ghp_` / `github_pat_`, `AKIA`, `sk-`, `xox[bap]-`, PEM private-key blocks,
`password=`, high-entropy bearer strings) plus the `.gitignore` filename list.
Seeded dummy credentials also count (fit criterion: the dummy-bearing archive is
rejected). Triage rule, fixed in advance: a hit inside `transcripts/`,
`prompts/` or `fixtures/` that is an example, placeholder, or truncated string is
recorded as `example/placeholder` (still listed); a complete well-formed
credential (e.g. `ghp_` + full alphanumeric body) is recorded as a finding.
Result recorded as 0 findings or itemized as-is.

## 5. PII scan

Email / student-ID regex scan. D6-permitted names + student IDs in Report §1/§2
are allowed; anything else is recorded as-is (the transcripts are already public
in the repository, so the exposure surface is identical).

## 6. Round-trip regression

Extract to a clean temporary directory, `pip install -r requirements.txt`, then
`pytest test/offline -v` must pass — the zip is self-contained and runnable.
Record the zip sha256 and byte size.

## Execution record

**Final submission — 2026-11-25 (attempt 1).**

- Freeze: main `e8d22a4830798605e288ec8cde4e10ec25e9da90`; tag
  `submission-20261125-final`; built 2026-11-25 20:52 HKT.
- Zip: `contentguard-group10-submission-20261125-final.zip` — **1,035,413 bytes**,
  sha256 `5a08f976bb171613ce1f30308f26219c3deb82ba86570aeb11da2481ce9b8ed3`,
  md5 `3735f80b80cbf61105a522da7898962f`.
- Manifest: 187 tracked files / 187 archive entries; two-way name diff empty (±0).
- Exclusions: 0 hits (no video/db/log/.env/token/`__pycache__`/.venv/node_modules/.git).
- Secret scan (REQ-SEC-005): 1,474 regex hits; 1,436 triaged `example/placeholder`;
  38 itemized false positives (long markdown links, long test names, comment
  separators, and the #94 audit report's own scan output); **0 valid credentials**;
  filename list 0 hits.
- PII scan: no real emails; only the `user@example.com` fixture placeholder and
  `n@pytest.mark.parametrize` regex false positives; D6-permitted member names and
  student IDs appear in Report §1/§2 as expected.
- Round-trip: `pip install -r requirements.txt` rc=0; `pytest test/offline -q` —
  **535 passed**, 2 warnings, 10.34s.
- D6 report: **9,202 words** (<10,000); **22 pages** at 12pt single spacing
  (A4 Word render). Contribution weights are **equal at 1.00 each** by team
  decision (issue #28); raw hours are 56.4 / 39.0 / 32.0 / 28.95 / 29.5.
- D5: canonical transcripts **5/5** present (stage 1 post-lock via #90 with the
  `docs/ai-use-log.yaml` re-verification note).
- Canvas: Project (Zip file) assignment 324835 — **attempt 1, 2026-11-25 20:53 HKT,
  late=False**, file_id `16687385`; Project (Demo Video) assignment 327885 —
  **attempt 1, 2026-11-25 21:03 HKT, late=False**, 198,630,139 B, md5
  `a222a6d103706877c6712aedf9614150`.
- Verification report: `contentguard-demo-work/outputs/verify_e8d22a4_20261125.txt`
  (external to the repository).
