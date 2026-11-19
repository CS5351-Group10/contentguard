# D5 — Annotated agent session transcript (TD-2: gate 1 verifies its own precondition)

- **Student:** HUANG Hongwei (60368210)
- **Main line:** Governance & CI (D3 governance files, D7 blocking gates, README, ai-use-log)
- **Task:** make gate 1 stop trusting the PR-body marker. It must resolve the cited test-plan
  issue, find an independent approval comment, and prove that approval predates the first
  implementation commit. Pays down **TD-2** / implements **REQ-GOV-002**.
- **Agent:** opencode 1.18.34 · **Model:** cityucs/CS5351/DeepSeek-V4-Flash
- **Session:** `ses_e0d3f5810ffe0jIw2uEYkUy9Bd`
- **Working directory:** `/mnt/d/CS/CityU/CS5351_SE/project/contentguard`
- **Started / ended:** 2026-11-19 15:41:14 → 2026-11-19 15:57:33 (HKT)
- **Tokens:** 54665 in / 32318 out · **Messages:** 2 human, 78 agent, 97 tool calls
- **Outcome:** `scripts/check_test_approval.py` 47 → 347 lines (paginated fetch layer, approval
  selection, commit selection, fail-closed paths); `test/offline/test_gate1_approval.py` with 15
  tests; `issues: read` added to the workflow. 219 offline tests pass.

## Annotated interventions

| # | Phase | Type | What the human did | Why |
|---|---|---|---|---|
| 1 | Task brief | **Scope + spec source** | Pointed the agent at issue #58 **and its PM sign-off comment** as the spec (not the issue body alone), and pre-committed the technical rules: `commit.author.date` (never committer), merges skipped, fail closed, four distinct failure messages, docstring rewritten rather than trimmed | The three field incidents (#7 no sign-off, #37 approval after implementation, #11 self-declared post-hoc) only matter if the gate distinguishes *which* precondition failed; a single "test plan not approved" message would let an author fix the wrong thing. Putting the PM's amendments in scope up front avoided a second plan round. |
| 2 | Plan approval | **Approve with two amendments** | A1: a qualifying approval must also **not** be authored by the pull-request author, with its own distinct message (self-approval ≠ missing approval). A2: paginate `/issues/{n}/comments` and `/pulls/{n}/commits` (per_page=100 + Link), define bot detection as `user.type=="Bot"` or a `[bot]` login, and normalise both timestamps to UTC before comparing | A1 closes a hole the sign-off left open: the implementer could otherwise approve their own plan on the issue. A2 is a correctness bug, not a nicety — GitHub's default page size is 30, so a PR with more than 30 commits would hand the gate a *later* commit and turn a legitimate pre-implementation approval into a false "post-hoc". Both amendments were recorded on #58 before implementation started, so the plan of record and the code agree. |

## How to read this transcript

- Human messages are the supervision: the task brief and the plan approval carrying A1/A2.
- `> \`tool\` …` lines are tool invocations; tool **outputs** are elided for size. The raw
  session is reproducible with `opencode export ses_e0d3f5810ffe0jIw2uEYkUy9Bd`.
- The agent never ran `git commit`/`git push` (repository convention GR-4); the human commits and
  opens the PR.
- Environment note: the local sandbox is Python 3.10 while the repo targets 3.11+; the agent used
  a throwaway `/tmp` compatibility shim (never committed) to execute the suite locally. CI runs
  3.12, where the same suite passes without a shim.

## Raw conversation

---

### Human — 2026-11-19 15:41:14
Project: ContentGuard (CS5351 Group 10). You are the coding agent; I am the human operator and
Governance & CI owner. Read AGENTS.md and Prompt.md, then AGENTS.md §2 reading order.

## Task: tighten gate 1 (TD-2, REQ-GOV-002) — approved plan is issue #58

Fetch the issue AND its comments (the PM sign-off comment is part of the spec, not a side note):

    curl -s https://api.github.com/repos/CS5351-Group10/contentguard/issues/58
    curl -s https://api.github.com/repos/CS5351-Group10/contentguard/issues/58/comments

The sign-off comment (2026-11-19T07:25Z) amends the plan with technical rules. Follow them
exactly:

### Approval record
- A **non-author issue comment** (author = issue author; bot accounts excluded) whose body
  contains `Test-Plan-Approved: #<issue>`.
- Use the **earliest** such comment.
- If that comment was edited (`updated_at != created_at`), its **updated_at** is the effective
  approval time; say so in the failure message when it matters.

### First implementation commit
- `GET /repos/{repo}/pulls/{n}/commits` order; skip commits with more than one parent (merges).
- For each remaining commit, fetch its own file list (`GET /repos/{repo}/commits/{sha}`) and take
  the first commit whose files include any `CODE_PREFIXES` path (`scripts/pr_files.py`). Earlier
  docs-only commits do not count.
- Compare the approval's effective time against that commit's **`commit.author.date`** — never the
  committer date (a rebase must not turn a pre-implementation approval into a post-hoc one).
- If no non-merge code commit exists, or a per-commit file list is unavailable, FAIL CLOSED with an
  actionable `GATE 1 FAIL` message. Do not guess and do not fall back to the marker alone.

### Messages (keep all four distinct)
`no approval recorded` / `issue not found` / `cited number is a pull request, not an issue` /
`post-hoc approval` (quoting both timestamps).

## Deliverables

1. `scripts/check_test_approval.py` — implement the above; docs-only early pass and push-event pass
   unchanged (no lookup); fail closed on any API/parse error (`GATE 1 FAIL: <reason>`, exit 1, no
   traceback). Rewrite the module docstring to describe the new behaviour (do not merely delete the
   "W12 tightening" sentence).
2. `test/offline/test_gate1_approval.py` — offline, mocked fetches, no network. The seven cases in
   #58, plus: merge commit skipped, docs-only commit before the real one skipped, edited approval
   comment uses `updated_at`, bot comment ignored. Docstrings cite `REQ-GOV-002` and `TD-2`.
3. `.github/workflows/ci.yml` — add `issues: read` to `permissions:`. Per-step `env:` only; job name
   `blocking-gates` unchanged.
4. `docs/ai-use-log.yaml` — entry **AI-011**, operator `HUANG Hongwei (60368210)`, transcript
   `transcripts/60368210-HUANG-Hongwei-td2.md`.

## Constraints

- Do not touch `docs/req/**`, `docs/architecture/**`, `.opencode/**`, `.agent/**`,
  `transcripts/**`, `.github/CODEOWNERS`, `.github/CONTRIBUTING.md`, templates, `docs/team/**`,
  `docs/review-memo.md`.
- Stdlib only (`urllib` + `re`). No new dependencies.
- Do not soften "no approval" into a warning; it blocks.
- Approval *authority* (which role may sign) is explicitly out of scope.

## Process

1. Execution plan first; STOP for my approval before writing code.
2. Tests first — the "no approval", "late approval" and "cited a PR" cases must be red before the
   fix.
3. Self-verify: `pytest test/offline -v`, `ruff check src scripts test`,
   `mypy --ignore-missing-imports scripts test`, `python scripts/validate_requirements.py`, workflow
   YAML parse + job name check, and a synthetic-payload run of gate 1 for all four failure modes
   plus the docs-only pass.
4. Print the PR description in one fenced block citing `Test-Plan-Approved: #58`. Do not commit.

---

### Agent — 2026-11-19 15:41:14
I'll start by reading the governance files in the mandated order, then fetch issue #58 and its comments.
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/AGENTS.md
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/Prompt.md
> `bash` command=curl -s https://api.github.com/repos/CS5351-Group10/contentguard/issues/58; echo "=====COMMENTS====="; curl -s…

---

### Agent — 2026-11-19 15:41:24
Now let me read the mandated reading-order docs and the existing gate code.
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/architecture-blueprint.md
> `bash` command=ls docs/architecture/adr/ docs/architecture/ docs/code-governance/ docs/req/ .opencode/ scripts/ test/ test/of…

---

### Agent — 2026-11-19 15:41:28
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_test_approval.py
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/pr_files.py
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/.github/workflows/ci.yml
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/architecture/invariants.md

---

### Agent — 2026-11-19 15:41:33
> `bash` command=grep -n "REQ-GOV-002" -A 40 docs/req/requirements.yaml | head -80
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/.opencode/permissions.jsonc
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_gate2_safety.py
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/conftest.py

---

### Agent — 2026-11-19 15:41:38
Now let me read the remaining docs, ai-use-log, and related scripts/tests.
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/code-governance/verification-constraints.md
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/code-governance/structural-constraints.md
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/ai-use-log.yaml; limit=80

---

### Agent — 2026-11-19 15:41:44
> `bash` command=tail -60 docs/ai-use-log.yaml
> `bash` command=grep -rn "check_test_approval\|Test-Plan-Approved\|test_gate1\|gate1" test/ scripts/ .github/ 2>/dev/null | gr…
> `bash` command=cat test/offline/test_pr_files_headers.py; echo ===; cat requirements.txt 2>/dev/null; echo ===; cat pytest.in…

---

### Agent — 2026-11-19 15:41:50
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_ai_use_log.py
> `bash` command=grep -n "date:\|id: AI-\|operator:" docs/ai-use-log.yaml | tail -20; echo ===; git log --oneline -5; echo ===;…

---

### Agent — 2026-11-19 15:41:57
> `bash` command=cat docs/ai-use-log.yaml | sed -n '178,247p'
> `bash` command=grep -n "TD-2" docs/debt-register.md | head; echo ===; cat .github/PULL_REQUEST_TEMPLATE.md

---

### Agent — 2026-11-19 15:42:04
> `bash` command=sed -n '1,60p' docs/architecture/adr/001-grounded-advisory-transactional-policy.md; echo "=== test count ===";…

---

### Agent — 2026-11-19 15:42:12
> `bash` command=which python3; python3 -m pytest test/offline -q 2>&1 | tail -12; echo "=== mypy/ruff ==="; python3 -m mypy --…

---

### Agent — 2026-11-19 15:42:19
> `bash` command=ls /usr/bin/python3* /usr/local/bin/python3* 2>/dev/null; which -a python3.12 python3.11 uv 2>/dev/null; pytho…

---

### Agent — 2026-11-19 15:42:25
> `bash` command=ls -a | head -40; ls ~/.venv .venv venv 2>/dev/null; find / -maxdepth 4 -name "python3.12" -type f 2>/dev/null…

---

### Agent — 2026-11-19 15:42:30
No Python 3.12 here (only 3.10), so `conftest.py` (which uses `datetime.UTC`) won't import locally. I'll run my tests with `-p no:cacheprovider --noconftest` and install a 3.10-compatible shim only for verification. Let me check the remaining relevant pieces.
> `bash` command=cat scripts/check_safety_paths.py | head -40; echo "=== gov scaffold test (workflow) ==="; grep -n "permission…
> `bash` command=python3 -c "import yaml; print('yaml ok')" 2>&1; python3 -c "import pytest; print(pytest.__version__)" 2>&1; p…

---

### Agent — 2026-11-19 15:42:37
Let me check what the workflow/scaffold tests assert about `ci.yml` so I don't break them, and see how gate4 tests mock fetches (style to mimic).
> `bash` command=sed -n '1,70p' test/offline/test_governance_scaffold.py
> `bash` command=grep -n "def test_\|monkeypatch\|fetch\|urlopen\|_api\|_get" scripts/check_semantic_eval.py | head -40; echo =…

---

### Agent — 2026-11-19 15:42:47
> `bash` command=grep -n "ci.yml\|workflow\|permissions\|yaml.safe_load\|blocking-gates" test/offline/test_governance_scaffold.…

---

### Agent — 2026-11-19 15:42:52
> `bash` command=sed -n '120,180p' test/offline/test_governance_scaffold.py

---

### Agent — 2026-11-19 15:42:57
> `bash` command=python3 -m ruff check src scripts test 2>&1 | tail -15; echo "=== mypy ==="; python3 -m mypy --ignore-missing-…

---

### Agent — 2026-11-19 15:43:04
I have everything I need. Both `ruff` and `mypy` are clean except for pre-existing `datetime.UTC` errors (Python 3.10 local env only; CI uses 3.12). Here is the execution plan.

---

## Stage 0 — Context confirmation

- **Task.** Tighten CI gate 1 (`scripts/check_test_approval.py`, TD-2, REQ-GOV-002) to resolve the cited test-plan issue and verify a **non-author, non-bot approval comment exists and predates the first implementation commit** (by `commit.author.date`), failing closed on ambiguity. Plan is issue #58 + its PM sign-off comment `7002644577` (`swordnew123`, 2026-11-19T07:25:03Z, unedited).
- **IDs touched.** REQ-GOV-002 (must, gate 1). No runtime invariants (REQ-INV-*) in play — this is CI tooling, not `src/contentguard/policy/**`. TD-1 (semantic gate) not triggered (no `prompts/**` change).
- **Environment note (found ambiguity, resolved, not a spec ambiguity).** This box has only Python 3.10; `test/offline/conftest.py` (uses `datetime.UTC`, needs ≥3.11) can't import locally. I'll run my new test module with `--noconftest -p no:cacheprovider` locally and also report the full-suite result honestly. CI runs 3.12. My new test file will use a local import of the target module only (no `conftest` deps), matching `test_pr_files_headers.py` / `test_gate2_safety.py` style.

---

## Stage 1 — Execution plan

### 1. Traceability

| Planned file / test | ID served |
|---|---|
| `scripts/check_test_approval.py` (rewrite body + docstring) | REQ-GOV-002, TD-2 |
| `test/offline/test_gate1_approval.py::test_approved_before_implementation_passes` | REQ-GOV-002, TD-2 |
| `::test_no_approval_comment_fails` (negative, "no approval recorded") | REQ-GOV-002, TD-2 |
| `::test_approval_after_implementation_fails` (negative, "post-hoc approval", both ts) | REQ-GOV-002, TD-2 |
| `::test_cited_number_is_a_pr_fails` (negative, "cited number is a pull request, not an issue") | REQ-GOV-002, TD-2 |
| `::test_cited_issue_missing_fails` (negative, "issue not found") | REQ-GOV-002, TD-2 |
| `::test_docs_only_pr_passes_without_issue_lookup` | REQ-GOV-002, TD-2 |
| `::test_push_event_passes` | REQ-GOV-002, TD-2 |
| `::test_merge_commit_skipped` (extra from sign-off) | REQ-GOV-002, TD-2 |
| `::test_docs_only_commit_before_real_one_skipped` (extra) | REQ-GOV-002, TD-2 |
| `::test_edited_approval_uses_updated_at` (extra) | REQ-GOV-002, TD-2 |
| `::test_bot_comment_ignored` (extra) | REQ-GOV-002, TD-2 |
| `::test_fail_closed_when_no_code_commit` / `::test_fail_closed_when_commit_files_unavailable` (fail-closed) | REQ-GOV-002, TD-2 |
| `.github/workflows/ci.yml` (`issues: read`) | REQ-GOV-002 (enabling) |
| `docs/ai-use-log.yaml` AI-011 | gate 6 / D1 |

### 2. Interface contract

`scripts/check_test_approval.py` — I will factor the network layer into small, separately-testable functions (mirrors `pr_files.py` style; added at module top, plus one earlier-file-list helper). Signatures:

```python
def _api_json(url: str, token: str) -> object          # GET; raises RuntimeError on HTTP/URL error (actionable)
def _issue_approval(repo, issue, issue_author, token) -> tuple[str, datetime] | None
    # None if issue/PR 404; returns (effective_iso, dt) of earliest non-author non-bot marker comment,
    # uses updated_at when edited; raises RuntimeError on malformed comment payload
def _pull_commits(repo, number, token) -> list[dict]   # GET /pulls/{n}/commits (respects returned order)
def _commit_is_merge(commit) -> bool                    # len(parents) > 1
def _commit_code_files(repo, sha, token) -> list[str]  # GET /commits/{sha} → commit.files[].filename; RuntimeError if files missing
def _commit_author_date(commit) -> datetime            # commit.commit.author.date, UTC; RuntimeError if absent
def _first_implementation_commit(repo, number, token) -> dict   # skip merges, first commit whose files hit CODE_PREFIXES; RuntimeError if none
def main() -> int
```

- `MARKER` stays `re.compile(r"Test-Plan-Approved:\s*#(\d+)")`.
- Docs-only early-pass and push-event pass stay **before** any issue lookup (unchanged byte-for-byte in behaviour).
- Reuses `pr_files` (`event_payload`, `pull_request`, `changed_files`, `changed_code_files`, `CODE_PREFIXES` — importing the constant directly so `CODE_PREFIXES` matches the issue's wording).
- **Distinguishing three failure sources** at the issue stage via return/exception: 404-not-found vs. cited-PR vs. no-marker vs. post-hoc. To keep messages distinct while `_api_json` stays generic, I'll add a focused `_issue_or_none` returning `("issue"|"pr"|None, obj)` by trying `/issues/{n}` (GitHub returns PRs there with a `pull_request` key) — actually: GET `/issues/{n}` 404 ⇒ "issue not found"; 200 with `"pull_request" in obj` ⇒ "cited number is a pull request, not an issue"; else it's the issue. This keeps a single call and clean classification.

### 3. Scope boundaries

- **Create:** `test/offline/test_gate1_approval.py`.
- **Modify:** `scripts/check_test_approval.py`, `.github/workflows/ci.yml` (add `issues: read` under `permissions:`), `docs/ai-use-log.yaml` (append AI-011).
- **NOT touched:** `docs/req/**`, `docs/architecture/**`, `.opencode/**`, `.agent/**`, `transcripts/**`, `.github/CODEOWNERS`, `.github/CONTRIBUTING.md`, PR/issue templates, `docs/team/**`, `docs/review-memo.md`, `scripts/pr_files.py`, `prompts/**`.
- Confirmed: none of the four target files are frozen/human-owned (`docs/ai-use-log.yaml` is `docs/**` = readable; write via gate-6 flow is expected and precedented by AI-001..AI-009).

### 4. Testing strategy (tests first, red before fix)

Write `test/offline/test_gate1_approval.py` **before** rewriting the script, mocking `check_test_approval`'s fetch functions (`_api_json` / `_issue_or_none`, `_pull_commits`, `_commit_code_files`, `event_payload`, `changed_files`) — no network. The unmocked current script has none of these names, so the suite is **red**. Then implement.

- Red-first critical three: `test_no_approval_comment_fails`, `test_approval_after_implementation_fails`, `test_cited_number_is_a_pr_fails`.
- Negatives per feature (above). Existing suites must keep passing (zero regressions).

### 5. Steps

1. Write `test_gate1_approval.py` (all cases, docstrings cite `REQ-GOV-002`/`TD-2`). Prove red.
2. Rewrite `scripts/check_test_approval.py` (docstring rewritten to describe new behaviour; remove "W12 tightening" sentence, not merely delete it).
3. Add `issues: read` to `ci.yml` permissions.
4. Append AI-011 to `docs/ai-use-log.yaml`.
5. Verify: `pytest test/offline -v` (via shim/3.10 caveat), `ruff check src scripts test`, `mypy --ignore-missing-imports scripts test`, `python scripts/validate_requirements.py`, YAML parse + job name, and a synthetic-payload runner for all four failure modes + docs-only pass.
6. Emit PR description (one fenced block, cites `Test-Plan-Approved: #58`). No commit.

---

```
=== EXECUTION PLAN READY — REQUESTING HUMAN APPROVAL ===
```

---

### Human — 2026-11-19 15:48:17
Plan approved with two amendments I just recorded on #58 (2026-11-19 comment).

A1 — approval must not come from the PR author either. A qualifying approval comment's author
must not be a bot, not the issue author, AND not the pull-request author. If the only marker
comment is by the PR author, fail with this distinct message: "the approval comment is by the
pull-request author (self-approval does not count)" — do not reuse "no approval recorded".

A2 — paginate both list endpoints: GET /issues/{n}/comments and GET /pulls/{n}/commits must
follow per_page=100 pagination (Link header). With the default 30, a PR over 30 commits hands you
a later commit and turns a legitimate pre-implementation approval into a false "post-hoc".
Bot detection: user.type == "Bot" OR login ending in "[bot]". Normalise both timestamps to UTC
before comparing.

Add two tests for these: test_self_approval_by_pr_author_fails and
test_pagination_finds_earliest_comment (a marker on page 2, an approval comment beyond the first
page, and a >30-commit PR where only the last commit touches code).

Everything else in your plan stands — the factored fetch layer, GET /issues/{n} + pull_request
detection, commit.author.date, merge skipping, fail-closed paths, docs-only/push early passes,
issues: read, stdlib only. Proceed: tests first, the three cases (no approval / late approval /
cited a PR) plus the two new ones must be red before the fix.

---

### Agent — 2026-11-19 15:48:17
> `bash` command=curl -s https://api.github.com/repos/CS5351-Group10/contentguard/issues/58/comments | python3 -c "import sys,j…
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/pr_files.py; offset=27; limit=55

---

### Agent — 2026-11-19 15:48:23
Let me read the amendments comment so I follow it exactly.
> `bash` command=curl -s https://api.github.com/repos/CS5351-Group10/contentguard/issues/comments/7003057988 | python3 -c "impo…

---

### Agent — 2026-11-19 15:48:27
Plan approved + A1/A2 confirmed. Locking the design: a single paginated `requests`-free fetch layer using `Link` headers, self-approval as a distinct failure, and UTC-normalised comparisons. Tests first.
> `todowrite` todos=[{'content': 'Write test/offline/test_gate1_approval.py (all cases incl A1/A2); prove red', 'status': 'in_prog…

---

### Agent — 2026-11-19 15:48:31
> `write` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_gate1_approval.py; content="""Gate-1 test-plan-approval tests (deterministic, offline).  Verifies: REQ-GOV-002 / TD-2 — gate 1 (``scripts…

---

### Agent — 2026-11-19 15:48:56
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m pytest test/offline/test_gate1_approval.py -p …

---

### Agent — 2026-11-19 15:49:02
Red as expected for all the negative paths. Let me confirm the specific three + two new ones are among the failures, then implement.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m pytest test/offline/test_gate1_approval.py -p …

---

### Agent — 2026-11-19 15:49:09
The 3 named + self-approval are red. Now implement the gate.
> `todowrite` todos=[{'content': 'Write test/offline/test_gate1_approval.py (all cases incl A1/A2); prove red', 'priority': 'high'…

---

### Agent — 2026-11-19 15:49:13
> `write` content="""CI gate 1: no code change merges unless its tests were approved before implementation.  Verifies: REQ-GOV-0…; filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_test_approval.py

---

### Agent — 2026-11-19 15:49:34
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m pytest test/offline/test_gate1_approval.py -p …

---

### Agent — 2026-11-19 15:49:41
Two failures are test-data bugs, not gate bugs: my fake `_commit_code_files` filters nothing, so `files_by_sha` values must already be code paths. In pagination test I filled every commit with `docs/x.md`, but `fake_commit_files` returns them verbatim so the gate sees them as code. The fake should apply the `CODE_PREFIXES` filter (as the real one does). Let me fix the test's fake to mirror the real function's filtering.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_gate1_approval.py; oldString=    resolved = commit_files if commit_files is not None else {}      def fake_commit_files(repo: str, sha: str…; newString=    resolved = commit_files if commit_files is not None else {}      def fake_commit_files(repo: str, sha: str…

---

### Agent — 2026-11-19 15:49:49
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m pytest test/offline/test_gate1_approval.py -p …

---

### Agent — 2026-11-19 15:49:54
All 15 green. Now clean up the messy `json` import in the gate (I left an awkward late import).
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_test_approval.py; oldString=import os import re import sys import urllib.error import urllib.request from datetime import datetime, timezo…; newString=import json import os import re import sys import urllib.error import urllib.request from datetime import date…
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_test_approval.py; oldString=# ``json`` import kept separate so the monkeypatched test layer only needs ``_api_json``. import json  # noqa:…; newString=def _json_load(resp: object) -> object:     """Decode a urlopen response body as JSON."""     return json.load…

---

### Agent — 2026-11-19 15:50:03
Now the workflow and ai-use-log edits.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/.github/workflows/ci.yml; newString=permissions:   contents: read   pull-requests: read   issues: read; oldString=permissions:   contents: read   pull-requests: read

---

### Agent — 2026-11-19 15:50:14
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/ai-use-log.yaml; offset=240

---

### Agent — 2026-11-19 15:50:22
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/ai-use-log.yaml; newString=    pr: 47   # opened 2026-11-18 from issue #26    - id: AI-011     date: 2026-11-19     agent: opencode     m…; oldString=    pr: 47   # opened 2026-11-18 from issue #26 

---

### Agent — 2026-11-19 15:50:36
I assumed PR #59 — I shouldn't invent that. Let me make the `pr:` field honest ("opened by operator from issue #58") without a fabricated number.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/ai-use-log.yaml; oldString=    pr: 59   # opened 2026-11-19 from issue #58; newString=    pr: pending   # opened 2026-11-19 from issue #58 (number assigned at PR creation)

---

### Agent — 2026-11-19 15:50:45
Now full verification. First the lint/type/validate/YAML checks, then a synthetic-payload runner for the real (non-mocked) fetch layer.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m ruff check src scripts test 2>&1 | tail -20; e…

---

### Agent — 2026-11-19 15:50:55
Ruff flags issues in my script. mypy's only errors are the pre-existing 3.10 `datetime.UTC` ones (not mine). Let me see all 5 ruff errors.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m ruff check scripts/check_test_approval.py test…

---

### Agent — 2026-11-19 15:51:00
Interesting — ruff wants `datetime.UTC` (3.11+) but the rest of `scripts/` must already comply. Let me check how `pr_files.py` and others handle timezone/datetime to match the configured target.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && grep -rn "UTC\|timezone\|from datetime" scripts/ | grep -…

---

### Agent — 2026-11-19 15:51:07
ruff defaults to `py39` target when unconfigured, hence `UP017`/`TRY004`. CI likely has a ruff config? Let me check if `ruff check src scripts test` on untouched files also flags TRY — i.e. whether these rules are even enabled project-wide.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && ls -a | grep -iE "ruff|pyproject"; echo "---git stash che…

---

### Agent — 2026-11-19 15:51:12
No ruff config exists, so the project relies on ruff defaults (stable rules E/F). The `TRY004`/`UP017` hits appear because `.ruff_cache` is stale or my invocation differs. Let me check what ruff version CI vs local use and whether `--isolated` on my file also flags them.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m ruff check --isolated scripts/check_test_appro…

---

### Agent — 2026-11-19 15:51:18
Local ruff 0.17.5 enables a broader default rule set than CI's pinned `<1` (observed 0.6+). The old file passes under `--isolated` too, so these are real style asks in newer ruff. Since there's no config, CI's ruff could be any `<1` version. To be robust and match the "extend in place, stdlib only" spirit, I'll just satisfy the newer defaults: use `UTC` (3.11+, and CI is 3.12; the 3.10 local box can't import anyway) and raise `TypeError` for non-dict payloads.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m ruff check --select UP017,TRY004 --fix scripts…

---

### Agent — 2026-11-19 15:51:24
The auto-fix left `timezone` imported but unused and `UTC` after `timezone` (ordering). Let me fix import cleanly and the remaining three `TRY004` TypeError raises.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_test_approval.py; oldString=from datetime import datetime, timezone, UTC; newString=from datetime import UTC, datetime

---

### Agent — 2026-11-19 15:51:29
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m ruff check scripts/check_test_approval.py 2>&1…

---

### Agent — 2026-11-19 15:51:32
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && sed -n '130,140p;172,180p' scripts/check_test_approval.py

---

### Agent — 2026-11-19 15:51:36
These are `isinstance` guards meant as fail-closed API errors, not programmer type errors — but ruff's TRY004 wants `TypeError`. Since callers catch `RuntimeError`, raising `TypeError` would escape the catch and produce the traceback we must avoid. Better: keep them fail-closed by converting to `RuntimeError` but satisfy the linter with a `# noqa` and a reason. Actually cleaner is to restructure so the guard raises via a helper that ruff accepts. I'll use `noqa` with explicit rationale (these are data-validation guards on untrusted API payloads, deliberately RuntimeError so `main()` fails closed).
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 - <<'EOF' import re, pathlib p = pathlib.Path("sc…

---

### Agent — 2026-11-19 15:51:42
Now I need to verify `raises RuntimeError` in the tests still work and that the real function raises RuntimeError (not TypeError). Also re-run tests. But first, the `parse_time` for `ValueError` — TRY004 only. Let me run the full gate1 test file and the whole-offline with the shim.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m pytest test/offline/test_gate1_approval.py -p …

---

### Agent — 2026-11-19 15:51:49
All 15 now fail — my `sed`/python rewrite likely broke the module (the `UTC` import on 3.10 raises ImportError at load). Right, `datetime.UTC` doesn't exist in 3.10. The tests load the module, which now fails import.

Two options: keep `timezone.utc` (3.10-safe) and `# noqa: UP017`, or accept 3.11+ only. Since I set up tests to run on this 3.10 box, I'll keep it 3.10-compatible in *tests* but the module is CI-targeted 3.12. Let me check the import error.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -c "import sys; sys.path.insert(0,'scripts'); imp…

---

### Agent — 2026-11-19 15:51:58
Confirmed. I'll revert to `timezone.utc` with a `noqa: UP017` and rationale (CI is 3.12, but keeping 3.10-compatible keeps the module importable in the dev box and doesn't hurt). This is the honest choice given no config pins 3.12 semantics.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 - <<'EOF' import pathlib p = pathlib.Path("script…

---

### Agent — 2026-11-19 15:52:05
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m ruff check scripts/check_test_approval.py 2>&1…

---

### Agent — 2026-11-19 15:52:12
The `timezone.utc` inside `replace(...)` on line 207 (not the one with noqa) is the culprit. Let me see and noqa it too.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && sed -n '204,211p' scripts/check_test_approval.py

---

### Agent — 2026-11-19 15:52:21
Let me hoist a single module-level constant `_UTC = timezone.utc` with one noqa, and use it in both spots — cleaner than two noqas.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_test_approval.py; newString=    parsed = datetime.fromisoformat(text)     if parsed.tzinfo is None:         parsed = parsed.replace(tzinfo…; oldString=    parsed = datetime.fromisoformat(text)     if parsed.tzinfo is None:         parsed = parsed.replace(tzinfo…
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_test_approval.py; newString=MARKER = re.compile(r"Test-Plan-Approved:\s*#(\d+)") API_ROOT = "https://api.github.com" # 3.10-compatible UTC…; oldString=MARKER = re.compile(r"Test-Plan-Approved:\s*#(\d+)") API_ROOT = "https://api.github.com"

---

### Agent — 2026-11-19 15:52:29
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m ruff check src scripts test 2>&1 | tail -3; py…

---

### Agent — 2026-11-19 15:52:37
Ruff clean, 15/15 green. Now the `timezone` import is used; confirm no unused-import error and run the synthetic-payload end-to-end runner against the **real** fetch layer (monkeypatching `urlopen`/`event_payload`) to exercise all failure modes + docs-only pass.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 - <<'EOF' import io, json, sys sys.path.insert(0,…

---

### Agent — 2026-11-19 15:52:47
My fake `json.load` reads via `.read()` but `_json_load` uses `json.load(resp)` which iterates `.read()`—actually `json.load` calls `.read()` on the file-like, but my FakeResp's `headers` is a plain dict and `json.load` needs `.read()` to return bytes/str; it returned via `BytesIO` inside `read`. The non-list error means `_json_load` got something odd. The real issue: `json.load(resp)` where resp has `.read()` — but I defined `__iter__` returning empty iter, and `json.load` prefers `.read()`. Let me simplify the fake to be a real BytesIO subclass wrapper. This is a harness bug, not a gate bug (the mocked-pytest suite already exercises the logic). Let me fix the harness with `io.BytesIO`-like objects properly.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 - <<'EOF' import io, json, sys, contextlib sys.pa…

---

### Agent — 2026-11-19 15:52:56
Still non-list. The `_api_paginate` reads `resp.headers.get("Link")` and `json.load(resp)` — but `HttpResponse` here is a `BytesIO`; `json.load` calls `.read()` which works. The bug: `_json_load` calls `json.load(resp)`, fine. But `_api_paginate` checks `if getattr(resp, "headers", None)` then `resp.headers.get(...)`. For my Resp, `.headers` is a dict → truthy → `.get("Link")`. Fine. Why non-list?

Wait — `_api_paginate` appends `batch` but the non-list check is on `batch`. If `json.load` returned a dict... Let me debug directly.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 - <<'EOF' import io, json, sys sys.path.insert(0,…

---

### Agent — 2026-11-19 15:53:03
That works. So in the harness the issue endpoint returns a dict for comments? No — in `no-approval` route I map `/issues/58` prefix, and `/issues/58/comments` also matches the `/issues/58` prefix first! Dict iteration order picks the shorter key. Fix: match longest prefix. That's a harness bug.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 - <<'EOF' import io, json, sys, contextlib sys.pa…

---

### Agent — 2026-11-19 15:53:13
All four failure modes + docs-only pass + happy path + self-approval + committer-vs-author + offset-normalisation behave correctly through the **real** fetch layer. Note the committer date was 2099 yet it passed (author date used). 

Now the workflow YAML parse + job-name check, and `validate_requirements.py`.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 - <<'EOF' import yaml d = yaml.safe_load(open(".g…

---

### Agent — 2026-11-19 15:53:21
Now run the full offline suite. Since `conftest.py` needs `datetime.UTC` (3.11+), I'll run with a tiny `sitecustomize`-style shim that patches `datetime.UTC` for 3.10 only, so I can honestly report the full suite.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && mkdir -p /tmp/opencode/pyshim && cat > /tmp/opencode/pysh…

---

### Agent — 2026-11-19 15:53:26
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && PYTHONPATH=/tmp/opencode/pyshim python3 -c "import confte…

---

### Agent — 2026-11-19 15:53:30
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && PYTHONPATH=/tmp/opencode/pyshim python3 -m pytest test/of…

---

### Agent — 2026-11-19 15:53:36
`from datetime import UTC` imports the name directly, so patching the module attribute doesn't help. I'll temporarily inject a `.pth`-free approach: run pytest via a small wrapper that patches datetime before importing conftest. Simplest: use `pytest` with `-p` pointing at a plugin that patches `datetime.UTC` at import time — but conftest loads before? Let me use a wrapper script that sets it then invokes pytest.main.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && cat > /tmp/opencode/run_offline.py <<'EOF' import datetim…

---

### Agent — 2026-11-19 15:53:45
`StrEnum` is also 3.11+. `src/` isn't my scope and I mustn't modify it. The full suite genuinely needs 3.11+/3.12 (CI target). I'll add a shim for `enum.StrEnum` too, purely in the test runner (outside the repo).
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && cat > /tmp/opencode/run_offline.py <<'EOF' import datetim…

---

### Agent — 2026-11-19 15:54:03
Full offline suite: **219 passed** (with a 3.10 compatibility shim only for the pytest process; the repo code is unchanged). Let me confirm my test file is part of that count and run the exact verbatim commands the PR should cite, then finish the ai-use-log YAML validity check.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 /tmp/opencode/run_offline.py 2>&1 | grep -c "test…

---

### Agent — 2026-11-19 15:54:24
`grep -c test_gate1` returned 0 because `-q` suppresses per-test names. Let me confirm my tests are collected/passing via the shim runner explicitly.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && cat > /tmp/opencode/run_one.py <<'EOF' import datetime, e…

---

### Agent — 2026-11-19 15:54:38
All 15 pass. Let me review the final gate script once end-to-end for quality and confirm the docstring rewrite is complete (the "W12 tightening" sentence is replaced, not merely deleted).
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && grep -n "W12\|Current enforcement\|TD-2" scripts/check_te…

---

### Agent — 2026-11-19 15:54:54
The "W12 tightening" sentence is gone (replaced by a full behaviour description). But 429 lines is large; let me check I didn't duplicate logic (e.g., `_api_json` may be unused now). Let me verify each helper is used.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && for f in _api_json _json_load _next_link _api_paginate _i…

---

### Agent — 2026-11-19 15:55:03
`_api_json` appears only once (its own def) — dead code. Let me remove it; `_api_paginate` and `_issue_or_none`/`_commit_code_files` inline their fetch. Removing reduces size and avoids an unused public-looking helper.
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_test_approval.py; offset=63; limit=30

---

### Agent — 2026-11-19 15:55:12
I'll remove the unused `_api_json`.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_test_approval.py; newString= def _json_load(resp: object) -> object:     """Decode a urlopen response body as JSON."""     return json.loa…; oldString= def _api_json(url: str, token: str) -> object:     """GET a GitHub API URL and decode JSON; raise RuntimeErro…

---

### Agent — 2026-11-19 15:55:22
Now the 401 message lives only in `_issue_or_none`; `_api_paginate` and `_commit_code_files` don't give the tailored 401 hint, but they surface the status code — acceptable and still actionable. Re-verify everything.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m ruff check src scripts test 2>&1 | tail -2 && …

---

### Agent — 2026-11-19 15:55:40
The 3 mypy errors are the pre-existing `datetime.UTC` ones (py3.10 env only; CI is 3.12 and these files are untouched by me). Let me confirm they're exactly those and none are mine.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m mypy --ignore-missing-imports scripts test 2>&…

---

### Agent — 2026-11-19 15:55:50
Pre-existing only (all in untouched files, `datetime.UTC` on Python 3.10; clean under CI's 3.12). Now re-run the test suite and the synthetic runner after the `_api_json` removal.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 /tmp/opencode/run_one.py 2>&1 | tail -2; echo "==…

---

### Agent — 2026-11-19 15:56:11
Re-run the synthetic-payload harness to confirm the real fetch layer still behaves after the removal.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 - <<'EOF' import io, json, sys, contextlib sys.pa…

---

### Agent — 2026-11-19 15:56:22
All failure modes distinct and actionable, docs-only passes, happy path passes, self-approval distinct, fail-closed on missing file list. Let me do a final review of the complete gate script for readability.
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_test_approval.py; offset=1; limit=63

---

### Agent — 2026-11-19 15:56:28
`ApprovalError` is defined but unused — remove it. Let me check.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && grep -c "ApprovalError" scripts/check_test_approval.py

---

### Agent — 2026-11-19 15:56:37
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_test_approval.py; newString=_UTC = timezone.utc  # noqa: UP017   def _json_load(resp: object) -> object:; oldString=_UTC = timezone.utc  # noqa: UP017   class ApprovalError(RuntimeError):     """A classified issue-approval fai…

---

### Agent — 2026-11-19 15:56:50
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m ruff check src scripts test 2>&1 | tail -2 && …

---

### Agent — 2026-11-19 15:57:08
All green. Final scope check: confirm only the four intended files changed and nothing frozen/human-owned was touched.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && git status --short; echo "=== diffstat ==="; git diff --s…

---

### Agent — 2026-11-19 15:57:14
Exactly the four deliverables; no forbidden paths touched. Let me finalize the todos and show the ci.yml diff snippet for the record.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && git diff .github/workflows/ci.yml
> `todowrite` todos=[{'content': 'Write test/offline/test_gate1_approval.py (all cases incl A1/A2); prove red', 'priority': 'high'…

---

### Agent — 2026-11-19 15:57:19
Implementation complete. Here's the summary.

## What was built

- **`scripts/check_test_approval.py`** — gate 1 now resolves the cited issue, reads its comments (paginated), takes the earliest qualifying approval (human, not bot, not issue author, **not PR author** per A1; edited comment uses `updated_at`), and compares against the first **non-merge** implementation commit's `commit.author.date` (never committer), both UTC-normalised. Four distinct messages plus self-approval; fails closed on any API/parse/no-file-list/no-code-commit case. Docs-only and push early passes unchanged. Docstring rewritten to describe the new behaviour (W12 sentence replaced, not merely deleted).
- **`test/offline/test_gate1_approval.py`** — 15 offline, mocked tests: the 7 from #58, plus merge-skip, docs-only-commit-skip, edited-`updated_at`, bot-ignored, self-approval (A1), pagination >30 commits + page-2 marker (A2), and two fail-closed cases.
- **`.github/workflows/ci.yml`** — `issues: read` added; job `blocking-gates` intact; per-step env only.
- **`docs/ai-use-log.yaml`** — AI-011.

## Verification (local env caveat)

This box is Python 3.10; `conftest.py`/`src` use `datetime.UTC`/`enum.StrEnum` (3.11+), so I ran pytest through a process-level shim (no repo files altered). CI is 3.12.
- `pytest test/offline` → **219 passed** (15 new). Red-before-fix confirmed for no-approval / late / cited-PR / self-approval.
- `ruff check src scripts test` → clean.
- `mypy --ignore-missing-imports scripts test` → only the **3 pre-existing** `datetime.UTC` errors in untouched files (3.10 env only).
- `validate_requirements.py` → 31 valid. Workflow YAML parse + job-name + per-step-env asserted. Synthetic-payload runs through the **real** fetch layer verified all four failure modes, docs-only pass, happy path, self-approval, committer-vs-author, offset-normalisation, and fail-closed.

`git status`: only the four deliverables changed — no frozen/human-owned paths.

## PR description

```markdown
test(gate1): verify the cited test plan exists, is independently approved, and predates implementation (TD-2, REQ-GOV-002)

## Requirement / invariant IDs
REQ-GOV-002 (must); pays down TD-2. No runtime invariants touched (CI tooling, not src/contentguard/policy/**).

## Test plan approval (gate 1)
Test-Plan-Approved: #58

## Summary
Gate 1 no longer trusts the PR-body marker alone. For a code/prompt PR it:
- Resolves the cited number via GET /issues/{n}: 404 ⇒ "issue not found"; a `pull_request` key ⇒
  "cited number is a pull request, not an issue".
- Reads the issue's comments (paginated per_page=100 + Link) and takes the earliest qualifying
  approval: marker body; human (not `user.type=="Bot"`, not a `[bot]` login); not the issue author;
  not the PR author (A1) — a solo PR-author marker fails with a distinct self-approval message;
  edited comments use `updated_at`.
- Selects the first non-merge commit from GET /pulls/{n}/commits (paginated, returned order; merges
  with >1 parent skipped; per-commit GET /commits/{sha} file list, first commit touching a
  CODE_PREFIXES path) — docs-only commits earlier do not count.
- Compares the approval's effective time to that commit's `commit.author.date` (never committer),
  both normalised to UTC (A2), so a rebase cannot turn an approval into "post-hoc".
Fails closed (GATE 1 FAIL: <reason>, exit 1, no traceback) on any API/parse error, a missing
per-commit file list, or no non-merge code commit. Docs-only PRs and push events keep their early
pass with no issue lookup. Approval authority (which role may sign) remains out of scope.

## Changes
- scripts/check_test_approval.py — rewrite + docstring describing the new behaviour (W12 sentence replaced).
- test/offline/test_gate1_approval.py — 15 offline, mocked-fetch tests: the #58 cases (happy, no
  approval, late, cited-a-PR, missing issue, docs-only no-lookup, push), plus merge-skip,
  docs-only-commit-skip, edited `updated_at`, bot-ignored, self-approval (A1), pagination >30 commits
  + page-2 marker (A2), and fail-closed (no code commit / missing file list). Each docstring cites
  REQ-GOV-002 and TD-2.
- .github/workflows/ci.yml — `issues: read` under `permissions:`; per-step env only; job name
  `blocking-gates` unchanged.
- docs/ai-use-log.yaml — AI-011.

## AI agent session (gate 6 / D5)
- ai-use-log entry: AI-011
- Transcript: transcripts/60368210-HUANG-Hongwei-td2.md

## Verification
- pytest test/offline -v — 219 passed (15 new). New negatives were red before the fix.
- ruff check src scripts test — clean.
- mypy --ignore-missing-imports scripts test — clean on touched files (the 3 pre-existing
  datetime.UTC errors appear only on the 3.10 dev box; CI runs 3.12).
- python scripts/validate_requirements.py — 31 valid.
- Workflow YAML parses; `issues: read` present; `blocking-gates` intact; per-step env only.
- Synthetic-payload run of gate 1: all four failure modes, docs-only pass, happy path, self-approval,
  committer-vs-author, and offset-normalisation behave as specified.

## Checklist
- [x] One logical change (small PR)
- [x] Every touched fit criterion has ≥1 test; negatives per failure mode
- [x] Offline suite green locally
- [x] docs/ai-use-log.yaml updated in this PR
- [ ] Trace matrix row (gate 1 status) — noted for the requirements owner if desired
- [x] Not a safety-critical path (no src/contentguard/policy/** change)

test plan: #58 (Z)
```

Note: `mypy` shows 3 pre-existing `datetime.UTC` errors **only** on this 3.10 box (untouched files, clean on CI's 3.12). Reminder for the human: save/annotate the transcript at `transcripts/60368210-HUANG-Hongwei-td2.md` (D5), and set the real PR number in AI-011's `pr:` field when you open it (currently `pending`).
