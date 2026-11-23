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
- D5 canonical annotated transcripts, one per member (5 expected; the current
  4/5 state (Mei stage 1 open) and its disposition are recorded in the
  execution record).
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

(to be appended by the release pass; REQ-SEC-005 evidence and the trace-matrix
cell are flipped only after this section exists with the scan results, the D6
word/page numbers, and the submitted sha.)
