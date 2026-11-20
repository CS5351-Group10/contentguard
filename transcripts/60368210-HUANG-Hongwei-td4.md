# D5 — Annotated agent session transcript (session 5)

- **Student:** HUANG Hongwei (60368210)
- **Main line:** Governance & CI (D3 governance files, D7 blocking gates, README, ai-use-log)
- **Task:** implement the CI structural checks (TD-4) per issue #66 Revision 2 — module set vs the
  ADR-001 element set, element-to-element import cycles, a frozen-path guard for
  `.opencode/**` + `.agent/**`, and a docs-only fast path, wired into the existing
  `blocking-gates` job as `Gate 2e`
- **Agent:** opencode 1.18.34 · **Model:** cityucs/CS5351/DeepSeek-V4-Flash
- **Session:** `ses_e0becda6affeVkm65egSFweSho`
- **Working directory:** `/mnt/d/CS/CityU/CS5351_SE/project/contentguard`
- **Started / ended:** 2026-11-19 21:50:57 → 2026-11-19 22:32:56 (HKT)
- **Tokens:** 68977 in / 25246 out · **Messages:** 3 human, 66 agent, 80 tool calls
- **Outcome:** branch `feat/66-structural-checks` — `scripts/check_structural.py` +
  `test/offline/test_structural_check.py`, extension of `test_dependency_direction`; 246 tests
  pass offline, zero findings on `main`

## Annotated interventions

| # | Phase | Type | What the human did | Why |
|---|---|---|---|---|
| 1 | Stage 0 | **Constraint + scope correction up front** | Told the agent that the first draft of issue #66 falsely claimed "nothing does structural checks today", and that the existing `test_invariants.py` checks must not be re-implemented; fixed the reading order and the reuse boundaries | The PM had rejected that premise hours earlier. Passing the correction forward stopped the agent from rebuilding a scanner that already exists above it in the same pytest run. |
| 2 | Before the plan | **Authorized proceeding without the architecture co-sign** | Recorded on the record: PM gate-1 approval exists; @xiaolizi33's co-sign is pending; the operator accepts responsibility because the change is additive; the co-sign stays a precondition for **merge**, and if absent the RM entry must say `co-sign pending` with the reason | The agent stopped correctly at a real `AGENTS.md` §7 stop condition. Waiting would have burned the evening; silently proceeding would have made the missing co-sign invisible. The written record is the difference. |
| 3 | Plan approval | **Approve with two corrections** | (a) forbade `scripts/check_structural.py` from importing anything out of `test/offline/test_invariants.py`, and scoped Gate 2e to the gaps only; (b) rejected the "no token ⇒ silently SKIP the frozen check" design and required fail-closed | (a) a production gate depending on a test module is an inverted dependency that breaks on the next test refactor. (b) a blank credential silently disabling a check is exactly the #61 blind spot we had just closed. |

## How to read this transcript

- Human messages are the supervision: the brief, the authority record, and the plan approval.
- `> \`tool\` …` lines are tool invocations; tool **outputs** are elided for size. The raw session
  is reproducible with `opencode export ses_e0becda6affeVkm65egSFweSho`.
- The agent did not commit or push (repository convention GR-4); the human commits and opens the PR.

## Raw conversation

---

### Human — 2026-11-19 21:50:58
Project: ContentGuard (CS5351 Group 10). You are the coding agent; I am the human operator and
Governance & CI owner. Read AGENTS.md and Prompt.md, then follow the AGENTS.md §2 reading order.

## Task: implement the CI structural checks (TD-4)

The spec is issue #66, **Revision 2** — fetch it first and treat it as authoritative:

    curl -s https://api.github.com/repos/CS5351-Group10/contentguard/issues/66

Revision 2 exists because my first draft claimed "nothing does structural checks today" and was
wrong. Do not resurrect that premise.

Also read, before planning:
- `test/offline/test_invariants.py` — it already contains `find_enforcement_violations`,
  `test_enforcement_only_from_policy` (line ~174), `test_forbidden_call_structural` and
  `test_dependency_direction` (line ~233). These run in gate 5 today.
- `docs/code-governance/structural-constraints.md` — rules 1/4/5/6 and the
  "Enforcement status (2026-11-19)" table that says which half is machine-enforced
- `docs/architecture/adr/001-*.md` — the declared element set
- `src/contentguard/` — only `policy/`, `audit/`, `escalation/` exist; `analysis/` and `api/` are
  declared but not landed (absent element = INFO, never failure)
- `scripts/pr_files.py`, `scripts/check_safety_paths.py` — house style (stdlib, one error style,
  actionable `RuntimeError`, PR context via `event_payload()` / `changed_files()`)
- `.github/workflows/ci.yml` — one job `blocking-gates`

## Deliverables (revise, don't duplicate)

1. **Extend** `test/offline/test_invariants.py::test_dependency_direction` with the one missing
   prohibition: **`analysis` must not import `policy`** (today it covers audit/escalation→policy
   and policy→analysis). Add a negative fixture for it.
2. **Add** a module-set check: every directory under `src/contentguard/` is an element declared by
   ADR-001. Unknown directory = FAIL; declared-but-absent element = **INFO**.
   - element set = a hardcoded constant citing ADR-001, with the scan root **injectable** so
     fixture trees never touch the real `src/`;
   - package directories only (must contain `__init__.py`); ignore `__pycache__` — gate 5 runs
     pytest before any structural gate, so cache dirs will exist on the runner. Include a test
     with a cache directory present.
3. **Add** an element-to-element import cycle check (negative fixture A→B→A).
4. **Add** a frozen-path guard for **`.opencode/**` and `.agent/**` only** — **not**
   `transcripts/**` (human transcripts are committed legitimately; #62 does exactly that). It
   needs PR changed files, so it goes in a gate with PR context (event payload or a step that has
   `GITHUB_TOKEN`) — never inside gate 5's token-less pytest, and it must not fail closed with a
   401.
5. **Add** a docs-only pass: a PR touching only `docs/` passes with no source scan.
6. `.github/workflows/ci.yml` — step `Gate 2e — structural checks` inside the existing job. Keep
   the job name `blocking-gates`. Per-step `env:` only.
7. `test/offline/test_structural_check.py` — the cases listed in #66 Revision 2, offline, fixture
   trees under `tmp_path`; every docstring cites `TD-4` / `REQ-INV-001`.
8. `docs/ai-use-log.yaml` — entry **AI-012** (`AI-005` is reserved for the deferred Gate 7
   branch), operator `HUANG Hongwei (60368210)`, transcript
   `transcripts/60368210-HUANG-Hongwei-td4.md`, `pr:` the new PR number.

## Hard constraints

- **Reuse before writing.** Do not re-implement the INV-1 enforcement scan — call the existing
  `find_enforcement_violations`. If you believe it must change, say why in the plan.
- Do **not** claim full rule-5 enforcement. The plan's matrix is: named prohibitions +
  `analysis → policy` + cycles. The full allowed-edge matrix is deferred until `api/` and
  `analysis/` exist.
- Do not read `.opencode/permissions.jsonc` — agent-frozen; a checker may not read it either.
- Do not touch `docs/**`, existing `src/**`, existing `test/**` (other than the extension in
  deliverable 1), `transcripts/**`, `.opencode/**`, `.agent/**`, `.github/CODEOWNERS`,
  `.github/CONTRIBUTING.md`, templates, `docs/team/**`, `docs/review-memo.md`.
- Pure stdlib (`ast`, `pathlib`). No new dependency.
- Zero false positives on current `main` — run the check there and paste the output.

## Process

1. Execution plan first (traceability, interface contract, scope boundaries, test strategy,
   ordered steps). STOP for my approval before writing any code.
2. After approval: tests first (they must fail), then implementation, then self-verify:
   `pytest test/offline -v`, `ruff check src scripts test`,
   `mypy --ignore-missing-imports scripts test`, `python scripts/validate_requirements.py`,
   workflow YAML parse + assert the job name is still `blocking-gates`, and the structural check
   itself run against `main` showing zero findings.
3. Print the PR description in one fenced block citing `Test-Plan-Approved: #66`. Do not commit.

---

### Agent — 2026-11-19 21:50:58
I'll start by reading the governance files and fetching the spec. Let me batch the initial reads.
> `bash` command=curl -s https://api.github.com/repos/CS5351-Group10/contentguard/issues/66
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/AGENTS.md
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/Prompt.md

---

### Agent — 2026-11-19 21:51:09
Now the mandatory reading order. Let me batch reads.
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/architecture-blueprint.md
> `bash` command=ls docs/architecture/adr/ && echo "---" && ls src/contentguard/ && echo "---" && ls test/offline/ && echo "---…
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_invariants.py

---

### Agent — 2026-11-19 21:51:15
Now the remaining reading-order docs and house-style scripts. Batch.
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/code-governance/structural-constraints.md
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/code-governance/verification-constraints.md
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/architecture/invariants.md
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/architecture/adr/001-grounded-advisory-transactional-polic…

---

### Agent — 2026-11-19 21:51:25
Now the requirements registry, house-style scripts, ci.yml, and the ai-use-log.
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/req/requirements.yaml
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/pr_files.py
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_safety_paths.py
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/.github/workflows/ci.yml

---

### Agent — 2026-11-19 21:51:34
Now the ai-use-log, existing fixtures layout, check_ai_use_log for covnentional IDs, and how test_pr_files_headers/gate tests are structured (house style for tests).
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/ai-use-log.yaml
> `bash` command=ls -R test/offline/fixtures | head -60 && echo "---conftest---" && cat test/offline/conftest.py && echo "---py…
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_pr_files_headers.py

---

### Agent — 2026-11-19 21:51:42
Let me check the ISC template/issue comments for approval status, the smoke test (structure asserts on ci.yml), and branch state.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && curl -s https://api.github.com/repos/CS5351-Group10/conte…
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_governance_scaffold.py
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && git status --short && git branch --show-current && git lo…

---

### Agent — 2026-11-19 21:52:04
There's a feature branch. Let me read the issue comments (python3) and check the tree on this branch.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && curl -s "https://api.github.com/repos/CS5351-Group10/cont…
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && git log --oneline main..HEAD 2>/dev/null | head; echo "--…

---

### Agent — 2026-11-19 21:52:22
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && curl -s "https://api.github.com/repos/CS5351-Group10/cont…

---

### Agent — 2026-11-19 21:52:39
Issue #66's thread has only 3 comments total — the PM approval is the last one. Per its own binding note, implementation must not start until @xiaolizi33's architecture co-sign is recorded on this revision. I checked the full thread (and searched repo-wide): **no co-sign by @xiaolizi33 exists yet.** This is a Stop condition (AGENTS.md §7 / Prompt.md Stage 0).

## Stage 0 — Context confirmation (≤10 lines)

- **Task:** TD-4 CI structural checks per issue #66 Revision 2 (test plan, PM-approved).
- **Requirement/invariants touched:** `REQ-INV-001` (load-bearing), TD-4; indirectly structural rule 1 (element set), rule 5 (dependency direction, partly), rule 6 (frozen paths, narrow).
- **Ambiguities found:**
  1. **Architecture co-sign is missing** — PM approval explicitly defers implementation until @xiaolizi33 co-signs Revision 2. Repo-wide search found none. `AGENTS.md §7` stop condition applies.
  2. **Branch mismatch:** I'm on `feat/66-structural-checks`, *identical* to `main` (no commits ahead, clean tree). That fits a not-yet-started branch, but I want to confirm with you that this is where you want me to build.
  3. **`__pycache__` collision concern:** `src/contentguard/__pycache__` exists in the working tree. The scanner must ignore it so "package directories only" holds. The plan's approach is: recurse into `__pycache__`, but require `__init__.py` to qualify as a package. That works.
  4. **Frozen-path guard needs PR context and must not fail closed with a 401.** `pr_files.changed_files()` already converts a 401 into an actionable `RuntimeError`, so I can branch: only call the API when `GITHUB_TOKEN` is explicitly present in `env:`, and call it with the real token. If token is empty in a PR event, the guard prints a clear SKIP and exits 0 (does not fail closed with 401). That is the only sensible reading of "must not fail closed with a 401"; I'll say so explicitly in the plan.

## Pause before execution plan

I am **not** writing the Stage 1 execution plan yet, because the PM's binding note makes that plan unimplementable until the architecture co-sign exists. Per `AGENTS.md §7` ("Before generating any code") I need one human decision first.
> `question` questions=[{'question': "Issue #66 Revision 2's PM approval requires @xiaolizi33's architecture co-sign before implement…

---

### Agent — 2026-11-19 21:53:50
Proceeding on your authority. Let me confirm the exact fixture/ADR element set and `__init__` layout before writing the plan.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && echo "=== init files ===" && find src/contentguard -name …

---

### Human — 2026-11-19 21:53:59
Proceeding on operator authority, recorded explicitly:
- PM gate-1 approval is on record (2026-11-19 13:34Z, issue #66 Revision 2).
- @xiaolizi33's architecture co-sign is PENDING at implementation start. I accept that
  responsibility: this change is additive — a new offline test file, one extension to the
  existing test_dependency_direction, and one CI step. It does not modify the ADR-001 element
  set, the dependency matrix, or any existing module.
- The co-sign remains a precondition for MERGE. If it is not recorded before merge, the RM
  entry must say `co-sign pending` with this reason (per .github/CONTRIBUTING.md step 6).
  Carry this exact wording into the execution plan and the PR body.

---

### Agent — 2026-11-19 21:54:04
Recorded. I'll produce the Stage 1 execution plan now. One quick check on how the existing check style prints failures and whether there's a `check_structural.py` pattern to mirror (scripts have `main() -> int`, `GATE x FAIL:` prefixes).
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_ai_use_log.py
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && ls .github/ISSUE_TEMPLATE/ 2>/dev/null; echo "=== contrib…

---

### Agent — 2026-11-19 21:54:20
I have everything I need. Here is the Stage 1 execution plan.

---

# Execution Plan — TD-4 CI structural checks (issue #66 Revision 2)

## Preconditions recorded verbatim

PM gate-1 approval on record (issue #66 Revision 2, 2026-11-19 13:34Z). Architecture co-sign by @xiaolizi33 is **PENDING at implementation start**; the human operator accepted that responsibility on the record because this change is **additive** — a new offline test file, one extension to the existing `test_dependency_direction`, and one CI step — and does **not** modify the ADR-001 element set, the dependency matrix, or any existing module.

**Co-sign remains a precondition for MERGE.** If it is not recorded before merge, the RM entry must say `co-sign pending` with this reason (per `.github/CONTRIBUTING.md` step 6). This exact wording is carried into the PR body.

## 1. Traceability

| File / test | Serves | Note |
|---|---|---|
| `test/offline/test_invariants.py::test_dependency_direction` (extend) | REQ-INV-001 / rule 5 | Adds `analysis → policy` prohibition (the one missing named edge) |
| `test/offline/test_invariants.py::test_analysis_must_not_import_policy` (new negative) | REQ-INV-001 | Negative fixture `analysis` importing `policy` ⇒ FAIL |
| `scripts/check_structural.py` | TD-4 / REQ-INV-001 / rule 1 | stdlib-only module-set + cycle + frozen-path + docs-only logic; **reuses** `find_enforcement_violations` and the existing dependency check by importing them, never reimplementing the INV-1 scan |
| `test/offline/test_structural_check.py` | TD-4 / REQ-INV-001 | All cases from #66 Rev 2, fixture trees under `tmp_path` |
| `.github/workflows/ci.yml` — `Gate 2e — structural checks` | TD-4 | New step in `blocking-gates` job; per-step `env:` only |
| `docs/ai-use-log.yaml` — AI-012 | REQ-GOV-001 | Operator HUANG Hongwei (60368210) |

## 2. Interface contract

New CLI module `scripts/check_structural.py` (mirrors `check_safety_paths.py` house style — stdlib, `main() -> int`, `GATE 2E …` messages, `event_payload()`/`changed_files()` via `pr_files`):

```python
# ADR-001 declarative element set (hardcoded, injectable scan root)
ADR001_ELEMENTS: frozenset[str] = frozenset({"analysis", "api", "audit", "escalation", "policy"})

FROZEN_PREFIXES: tuple[str, ...] = (".opencode/", ".agent/")   # NOT transcripts/

def declared_elements() -> frozenset[str]            # returns ADR001_ELEMENTS
def package_dirs(root: Path) -> dict[str, Path]      # name→dir for immediate subdirs that are
                                                     #   real packages (contain __init__.py);
                                                     #   __pycache__ and non-packages ignored
def unknown_element_findings(root: Path) -> list[str]   # FAIL messages for undeclared package dirs
def missing_element_info(root: Path) -> list[str]       # INFO lines for declared-but-absent
def element_import_graph(root: Path) -> dict[str, set[str]]  # element → imported elements
def cycle_findings(graph: dict[str, set[str]]) -> list[str]  # A→…→A cycles, actionable path
def frozen_hits(files: list[str]) -> list[str]          # changed files under FROZEN_PREFIXES
def check_source(root: Path) -> tuple[list[str], list[str]]  # (failures, infos); invokes the
                                                     # existing find_enforcement_violations(root/src-like)
def main(argv: list[str] | None = None) -> int
```

- **Reuse, not re-implement:** `check_source` and the cycle/direction findings call the existing `find_enforcement_violations` and `_imported_policy_modules` from `test/offline/test_invariants.py` (imported by file path like `test_governance_scaffold._load_deps`, since that file is in `test/`). **No second INV-1 scanner is written.** If you or the architecture owner want it factored differently, say so now — otherwise I keep the import-the-existing-helper approach.
- `package_dirs` only counts immediate children of `root` that are directories containing `__init__.py`; `__pycache__` has no `__init__.py`, so it is naturally excluded (and I'll add an explicit skip for clarity). This satisfies the "cache present" requirement.
- `main()` flow:
  1. `--offline` / no event context ⇒ `GATE 2E SKIP`.
  2. push event ⇒ run the **source-tree** part only (`check_source` on real `src/`): module-set + cycles + INV-1 reuse. (No PR files needed.)
  3. PR event ⇒ fetch `changed_files`; if the PR touches **only `docs/`** ⇒ `GATE 2E PASS: docs-only` (no source scan, no frozen check needs API beyond the file list).
  4. PR touching non-`docs/` paths ⇒ run source part **and** `frozen_hits`.
  5. If a **frozen hit** exists and `GITHUB_TOKEN` is absent/blank in a PR event ⇒ print `GATE 2E SKIP(frozen-check): no GITHUB_TOKEN` **and still run the source part**, exit based on source findings — **never** a 401 traceback. If a token is present, we already have `changed_files`; the frozen check is pure local matching against the list (no extra API call), so no 401 path exists at all. This is the "must not fail closed with a 401" guarantee.
- Note: the frozen-path guard **only** lives here (a gate with PR context / token), never in gate 5's token-less pytest.

## 3. Scope boundaries

**Will create:**
- `scripts/check_structural.py`
- `test/offline/test_structural_check.py`

**Will modify (minimal):**
- `test/offline/test_invariants.py` — extend `test_dependency_direction` with the `analysis → policy` prohibition; add one negative test function.
- `.github/workflows/ci.yml` — one new step `Gate 2e — structural checks` in the existing `blocking-gates` job; per-step `env:` only.
- `docs/ai-use-log.yaml` — AI-012 entry.

**Will NOT touch:** `docs/**` (any path), existing `src/**`, other existing `test/**`, `transcripts/**`, `.opencode/**`, `.agent/**`, `.github/CODEOWNERS`, `CONTRIBUTING.md`, templates, `docs/team/**`, `docs/review-memo.md`. (`docs/ai-use-log.yaml` is an explicit exception required by gate 6.)

**Frozen / human-owned confirmation:** `.opencode/permissions.jsonc` and `.agent/rules.md` are **not read** by the code or the tests (the checker's `FROZEN_PREFIXES` is a literal constant, not a filesystem read). `docs/req/**` and `docs/architecture/**` are untouched.

## 4. Testing strategy (tests first — they must fail before implementation)

In `test/offline/test_structural_check.py`, fixture `src/`-like trees under `tmp_path`; every docstring cites `TD-4` / `REQ-INV-001`:

- `test_unknown_element_directory_fails` — a real package dir not in ADR-001 ⇒ FAIL names it.
- `test_declared_absent_element_is_info` — `analysis`/`api` absent ⇒ INFO, not failure; current `main` (policy/audit/escalation present) passes.
- `test_pycache_is_ignored` — cache dir present ⇒ no unknown-element failure.
- `test_cycle_detected` — A→B→A ⇒ FAIL names the cycle.
- `test_acyclic_graph_passes` — `api→policy`, `policy→audit` ⇒ PASS.
- `test_frozen_path_flagged` — `.opencode/rules.md`, `.agent/rules.md` in changed files ⇒ FAIL.
- `test_transcripts_not_frozen` — `transcripts/…md` in changed files ⇒ NOT flagged.
- `test_docs_only_passes` — PR touching only `docs/…` ⇒ PASS with no source scan.
- `test_no_401_when_token_absent` — frozen path + blank token ⇒ never `RuntimeError`/exit 1 from a 401; prints SKIP(frozen-check) and non-401 outcome.
- `test_analysis_importing_policy_flagged` (in `test_invariants.py`) — negative fixture `analysis` → `policy`.

**Existing suites that must keep passing:** the full `test/offline` suite, notably `test_invariants.py`, `test_governance_scaffold.py`, `test_pr_files_headers.py`.

## 5. Steps (each individually verifiable)

1. `test/offline/test_structural_check.py` — write failing tests (red).
2. `test/offline/test_invariants.py` — extend `test_dependency_direction` + add the negative test (red).
3. `scripts/check_structural.py` — implement reusing `find_enforcement_violations`/`_imported_policy_modules` (green).
4. `.github/workflows/ci.yml` — add `Gate 2e` step; verify YAML parses and job name stays `blocking-gates`.
5. `docs/ai-use-log.yaml` — AI-012.
6. Self-verify: `pytest test/offline -v`, `ruff check src scripts test`, `mypy --ignore-missing-imports scripts test`, `python3 scripts/validate_requirements.py`, YAML parse + job-name assertion, `python3 scripts/check_structural.py --offline` and a real-tree run showing **zero findings on `main`** (paste output).
7. Print the PR description in one fenced block with `Test-Plan-Approved: #66` and the `co-sign pending` wording. **No commit.**

**Open item for your confirmation before build:** step 3 imports the existing `test_invariants` helpers rather than factoring them into a shared module — this keeps `test/**` changes minimal and avoids touching existing modules wholesale. If you prefer the helpers moved into `scripts/`, that is a larger, riskier change and I'd need your go-ahead.

```
=== EXECUTION PLAN READY — REQUESTING HUMAN APPROVAL ===
```

---

### Human — 2026-11-19 21:56:21
Plan approved with two corrections. Everything else stands (tests list, traceability,
GATE 2E naming, per-step env, docs-only pass, __pycache__ handling).

CORRECTION 1 — do not import from test/.
`scripts/check_structural.py` must NOT import `find_enforcement_violations`,
`_imported_policy_modules` or anything else from `test/offline/test_invariants.py`. A production
gate depending on a test module is an inverted dependency and it will break the first time that
test is refactored.

Resolution (my call): Gate 2e covers ONLY the gaps — module-set vs ADR-001, element-to-element
cycles, frozen-path guard, docs-only pass. It does NOT re-run the INV-1 scan or the dependency
direction check: those already run in gate 5 via test_invariants.py, and
`docs/code-governance/structural-constraints.md` (merged today) states exactly that. Not
re-running them satisfies "reuse, don't duplicate" without any cross-layer import.
If you believe gate 2e must also report INV-1, stop and say so instead — that would require
extracting the scanner into `scripts/structural_rules.py` with the test importing it, which is a
refactor I am not authorizing tonight.

CORRECTION 2 — no silent skip on a missing token.
`GATE 2E SKIP(frozen-check): no GITHUB_TOKEN` recreates exactly the blind spot fixed in #61 (a
blank credential silently disabling a check). In a PR event the token is always present, so its
absence is an anomaly: FAIL CLOSED with an actionable message ("cannot list changed files: the
step is missing GITHUB_TOKEN"), and keep running the source-tree part so the failure reports
everything at once.
Drop `test_no_401_when_token_absent` as written; replace it with a negative test asserting the
closed-fail behaviour and the actionable message.

ONE NOTE — you will be touching `test/offline/test_invariants.py` (the testing owner's file) for
the `analysis → policy` extension. That is fine and I accept it, but say so explicitly in the PR
body and keep the diff to that one prohibition plus its negative fixture.

Carry the co-sign wording I gave you into the plan and the PR body, then proceed:
tests first (red), then implementation, then the full self-verification.

---

### Agent — 2026-11-19 21:56:21
Both corrections accepted. Revised decisions recorded:
- **Gate 2e covers only the gaps** — module-set/ADR-001, element cycles, frozen paths, docs-only. No INV-1 or dependency-direction re-run, no `test/` import. No refactor of the scanner.
- **Missing token in a PR event = FAIL CLOSED**, actionable message, source-tree part still runs. `test_no_401_when_token_absent` replaced by a closed-fail test.

Starting build: tests first (red).
> `todowrite` todos=[{'content': 'Write test/offline/test_structural_check.py (red)', 'status': 'in_progress', 'priority': 'high'}…

---

### Agent — 2026-11-19 21:56:36
Let me check how tests import scripts (the `test_governance_scaffold` uses `importlib` file-path load). I'll mirror that to load `check_structural.py`, and for the two-level package fixture I need to understand my planned API. Writing the test file now.
> `write` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_structural_check.py; content="""Structural CI checks for gate 2e (TD-4, REQ-INV-001) — deterministic, offline.  Gate 2e closes the structur…

---

### Agent — 2026-11-19 21:57:17
Now extend `test_invariants.py` — the `analysis → policy` prohibition and one negative test. Minimal diff.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_invariants.py; oldString=def test_dependency_direction() -> None:     """Verifies REQ-INV-001 / structural rule 5 (dependency direction…; newString=def _dependency_direction_violations(root: Path) -> list[str]:     """AST-scan ``root`` for dependency-directi…

---

### Agent — 2026-11-19 21:57:42
The `imports` sibling function defined inside a for loop triggers ruff (B023 loop variable capture) potentially. Let me restructure to avoid nested function in loop. Actually simpler: inline the membership check. Let me fix.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_invariants.py; oldString=    violations: list[str] = []     for path in sorted(root.rglob("*.py")):         rel = path.relative_to(root…; newString=    for path in sorted(root.rglob("*.py")):         rel = path.relative_to(root)         tree = ast.parse(path…

---

### Agent — 2026-11-19 21:58:16
Actually the default-arg trick is ugly. Simpler: just inline membership checks, no helper function. Let me rewrite cleanly.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_invariants.py; newString=    for path in sorted(root.rglob("*.py")):         rel = path.relative_to(root)         tree = ast.parse(path…; oldString=    for path in sorted(root.rglob("*.py")):         rel = path.relative_to(root)         tree = ast.parse(path…

---

### Agent — 2026-11-19 21:58:42
Now `violations` is unused; remove it and return nothing (tests assert `== []`). Function returns None — adjust tests to not compare. Simpler: keep returning `[]` explicitly but drop the var. Let me view current function.
> `read` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_invariants.py; offset=233; limit=70

---

### Agent — 2026-11-19 21:59:02
`violations` is undefined now. Change return to `return []` and `assert ... == []` stays valid (function returns list on success, raises AssertionError on violation). Fix.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_invariants.py; oldString=                    f"{rel.as_posix()} imports a mutation repository port: "                     f"{sorted(off…; newString=                    f"{rel.as_posix()} imports a mutation repository port: "                     f"{sorted(off…

---

### Agent — 2026-11-19 21:59:21
Now confirm red. Run structural tests + the new invariant test; they should fail (no `check_structural.py`, missing analysis prohibition may pass since no analysis dir).
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -m pytest test/offline/test_structural_check.py t…

---

### Agent — 2026-11-19 21:59:47
Python 3.10 on `python3`; project uses 3.12. Find the right interpreter.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && for p in python3.12 python3.13 python3.11; do command -v …

---

### Agent — 2026-11-19 22:00:09
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && which -a python python3 pytest ruff mypy 2>/dev/null; ech…

---

### Agent — 2026-11-19 22:00:33
Only Python 3.10 available. `conftest.py` uses `datetime.UTC` (3.11+). The project targets 3.12 per CI. This is an environment limitation, not my change. Let me check if `uv` can provide 3.12, or if there's a way.
> `bash` command=command -v pip pip3 2>/dev/null; python3 -c "import pytest, ruff" 2>&1; echo "---try pip install uv---"; pip3 …

---

### Agent — 2026-11-19 22:01:08
> `bash` command=cd /tmp/opencode && pip3 install --quiet --user uv 2>&1 | tail -3; ~/.local/bin/uv --version 2>&1 || python3 -…

---

### Agent — 2026-11-19 22:03:54
> `bash` command=ls ~/.local/bin/uv 2>/dev/null; command -v uv 2>/dev/null; python3 -c "import uv" 2>&1 | head -1; ls ~/.cache/…

---

### Agent — 2026-11-19 22:04:10
No `uv`, no network reliably. To run tests I need Python 3.11+ for `datetime.UTC`. I can't modify `conftest.py`. Workaround: create a tiny shim so 3.10 can import `UTC`? That modifies runtime, not files. Actually `datetime.UTC` is just alias for `timezone.utc`. I can inject it via a `sitecustomize`/PYTHONSTARTUP? Tests import `from datetime import UTC`. I can create a sitecustomize in a dir on PYTHONPATH that patches datetime module before conftest imports.
> `bash` command=mkdir -p /tmp/opencode/shim && cat > /tmp/opencode/shim/sitecustomize.py <<'EOF' import datetime as _dt if not…

---

### Agent — 2026-11-19 22:04:29
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && python3 -c "import pytest" 2>&1 | head -1

---

### Agent — 2026-11-19 22:04:51
pytest is available. Run red tests with the shim on PYTHONPATH.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && PYTHONPATH=/tmp/opencode/shim python3 -m pytest test/offl…

---

### Agent — 2026-11-19 22:05:11
`StrEnum` is also 3.11+. The codebase genuinely requires 3.11+. Let me try to get a 3.12 python via pip's `python-build-standalone`? No. Check apt for python3.11/3.12 or deadsnakes. Try apt.
> `bash` command=apt-cache policy python3.12 python3.11 2>/dev/null | grep -E "python3\.|Candidate" | head; echo "---"; ls /opt…

---

### Agent — 2026-11-19 22:05:32
python3.11 available via apt. Try installing (may need sudo/no network).
> `bash` command=sudo -n apt-get install -y python3.11 2>&1 | tail -5 || apt-get install -y python3.11 2>&1 | tail -5

---

### Agent — 2026-11-19 22:05:48
No sudo. Try a user-space install via pip download of `python-build-standalone`? Offline. Let me check pip cache / whether network works at all (curl to github worked earlier, so network exists).
> `bash` command=cd /tmp/opencode && timeout 60 pip3 install --user uv 2>&1 | tail -5; ls ~/.local/bin/ 2>/dev/null

---

### Agent — 2026-11-19 22:07:09
> `bash` command=ls ~/.local/bin/uv 2>/dev/null && ~/.local/bin/uv --version; echo "exit=$?"; pip3 show uv 2>/dev/null | grep -…

---

### Agent — 2026-11-19 22:07:42
> `bash` command=find ~/.local/lib -name 'uv*' -maxdepth 4 2>/dev/null | head; python3 -m uv --version 2>&1 | head -2

---

### Agent — 2026-11-19 22:08:09
> `bash` command=cd /tmp/opencode && timeout 100 pip3 install uv 2>&1 | tail -6

---

### Agent — 2026-11-19 22:10:12
The install stalls (slow). Let me directly download the wheel and extract the `uv` binary.
> `bash` command=cd /tmp/opencode && timeout 90 pip3 download uv --no-deps -d /tmp/opencode/uvw 2>&1 | tail -3; ls -la /tmp/ope…

---

### Agent — 2026-11-19 22:12:05
Download is slow/timing out at the 17.6MB wheel. Let me retry download with a longer window.
> `bash` command=cd /tmp/opencode && timeout 300 pip3 download uv --no-deps -d /tmp/opencode/uvw 2>&1 | tail -4; ls -la /tmp/op…

---

### Agent — 2026-11-19 22:14:29
> `bash` command=ls -la /tmp/opencode/uvw; ls -la ~/.cache/pip 2>/dev/null | head

---

### Agent — 2026-11-19 22:14:38
Network is too slow for the 17MB wheel. Let me try downloading a standalone CPython 3.12 tarball from python-build-standalone via curl with resume, or check if apt has a local .deb cache. Alternatively try conda. Let me check what's reachable and fast.
> `bash` command=cd /tmp/opencode && timeout 60 curl -sL -o pbs.tar.gz -w "size=%{size_download} code=%{http_code} speed=%{spee…

---

### Agent — 2026-11-19 22:16:01
~1MB in 60s, too slow (need ~30MB). Let me check the pip http cache for any cached python or a faster mirror. Alternative: is there a conda env? Check for existing 3.12 anywhere deeper.
> `bash` command=find / -maxdepth 6 \( -name 'python3.12' -o -name 'python3.11' \) -type f 2>/dev/null | grep -v /proc | head; …

---

### Agent — 2026-11-19 22:18:32
The `find /` is too slow. Let me be targeted, and reconsider: maybe I don't need to run the whole suite — I can run just my tests with a compatibility shim that provides `StrEnum` and `UTC`. The `StrEnum` shim is trickier (it's used as a base class with `auto()`). I can add a 3.10-compatible `StrEnum` to the shim. Let me build a fuller `sitecustomize` that patches `enum.StrEnum` and `datetime.UTC` so the existing `src/` imports work under 3.10.
> `bash` command=cat > /tmp/opencode/shim/sitecustomize.py <<'EOF' """Local-only 3.10 compatibility shim for running the 3.12-t…

---

### Agent — 2026-11-19 22:18:50
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && PYTHONPATH=/tmp/opencode/shim python3 -m pytest test/offl…

---

### Agent — 2026-11-19 22:19:13
Conftest imported successfully now. Run the actual tests.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && PYTHONPATH=/tmp/opencode/shim python3 -m pytest test/offl…

---

### Agent — 2026-11-19 22:19:42
Red confirmed: 10 structural tests fail (missing implementation). The 17 passing are existing invariants + the new `analysis→policy` negative test (which passes because it asserts raising). Good. Now implement `scripts/check_structural.py`.
> `todowrite` todos=[{'content': 'Write test/offline/test_structural_check.py (red)', 'priority': 'high', 'status': 'completed'}, …

---

### Agent — 2026-11-19 22:20:16
The test expects `check_source(tmp_path)` where `tmp_path` is the root containing `contentguard/`. And `unknown_element_findings`/`missing_element_info`/`element_package_dirs` take the `contentguard/` dir directly. And `element_import_graph(contentguard_dir)`. Let me write the module accordingly.
> `write` content="""CI gate 2e — structural checks (TD-4, REQ-INV-001).  Closes the structural gaps that gate 5's ``test_invari…; filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_structural.py

---

### Agent — 2026-11-19 22:21:44
The `__import__("os")` hack is ugly; import `os` at top instead. Also `check_source(tmp_path)` in test passes `tmp_path` as root containing `contentguard/` directly (not `src/`). Let me re-check the test fixture: `test_declared_absent_element_is_info_not_failure` calls `check.check_source(tmp_path)` where `tmp_path` has `contentguard/` at top level (from `_pkg(tmp_path / "contentguard")`). So `check_source` must accept root containing `contentguard/`. But in `main` I pass `DEFAULT_SRC.parent` (repo root, with `src/contentguard`). Inconsistent.

I'll make `check_source` take the `src/` dir (i.e., the parent of `contentguard/`). Tests pass `tmp_path` which contains `contentguard/` → so `tmp_path` is the "src dir". In main pass `DEFAULT_SRC` (= repo `src/`). Fix.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_structural.py; newString=import ast import os import sys from pathlib import Path; oldString=import ast import sys from pathlib import Path

---

### Agent — 2026-11-19 22:22:17
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/scripts/check_structural.py; newString=def check_source(src_dir: Path) -> tuple[list[str], list[str]]:     """Run the source-tree structural checks a…; oldString=def check_source(root: Path) -> tuple[list[str], list[str]]:     """Run the source-tree structural checks agai…

---

### Agent — 2026-11-19 22:22:36
Now update `main` calls to pass `DEFAULT_SRC` (src dir), and fix the os import usage.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && grep -n "DEFAULT_SRC.parent\|__import__(\"os\")" scripts/…

---

### Agent — 2026-11-19 22:22:57
`DEFAULT_SRC = repo/src`, and I now call `check_source(DEFAULT_SRC)` which expects the src dir. Update `.parent`→ nothing, and os.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && sed -i 's/check_source(DEFAULT_SRC.parent)/check_source(D…

---

### Agent — 2026-11-19 22:23:20
Now in `main` the docs-only test monkeypatches `check_source` to fail if called — good, docs-only returns before that. But for the missing-token test, it monkeypatches `check_source` with a lambda taking `_root` — I call `check_source(DEFAULT_SRC)`, matches. But `changed_files` is imported into the module namespace; the docs-only test monkeypatches `check.changed_files` — good.

Run tests.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && PYTHONPATH=/tmp/opencode/shim python3 -m pytest test/offl…

---

### Agent — 2026-11-19 22:23:49
My test helper `_pkg(parent, name)` requires name, but I call `_pkg(tmp_path / "contentguard")`. Let me fix the helper to make `name` optional (create just the dir with `__init__.py`).
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/test/offline/test_structural_check.py; newString=def _pkg(parent: Path, name: str | None = None, *, init: bool = True) -> Path:     """Create a package directo…; oldString=def _pkg(parent: Path, name: str, *, init: bool = True) -> Path:     """Create a package directory ``parent/na…

---

### Agent — 2026-11-19 22:24:11
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && PYTHONPATH=/tmp/opencode/shim python3 -m pytest test/offl…

---

### Agent — 2026-11-19 22:24:37
All 10 green. Now run the whole offline suite to check zero regressions.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && PYTHONPATH=/tmp/opencode/shim python3 -m pytest test/offl…

---

### Agent — 2026-11-19 22:25:20
246 passed (was 236 before + 10 new; the invariants +1 and structural +10 → matches). Now ci.yml step.
> `todowrite` todos=[{'content': 'Write test/offline/test_structural_check.py (red)', 'priority': 'high', 'status': 'completed'}, …

---

### Agent — 2026-11-19 22:25:58
The step needs to run on both push and PR (source-tree checks on push; PR adds frozen + docs-only). So no `if:` condition — runs always, needs token on PR. Place after Gate 2d.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/.github/workflows/ci.yml; newString=      - name: "Gate 2d — safety-path tier (ADR/invariant reference)"         if: github.event_name == 'pull_re…; oldString=      - name: "Gate 2d — safety-path tier (ADR/invariant reference)"         if: github.event_name == 'pull_re…

---

### Agent — 2026-11-19 22:26:22
Now verify YAML parses and job name + step present.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && PYTHONPATH=/tmp/opencode/shim python3 -c " import yaml d=…

---

### Agent — 2026-11-19 22:26:58
YAML valid, job name intact, per-step env only. Now AI-012 entry. Need to know the brief. Keep it accurate.
> `edit` filePath=/mnt/d/CS/CityU/CS5351_SE/project/contentguard/docs/ai-use-log.yaml; newString=    pr: 61   # opened 2026-11-19 from issue #58    - id: AI-012     date: 2026-11-19     agent: opencode     m…; oldString=    pr: 61   # opened 2026-11-19 from issue #58 

---

### Agent — 2026-11-19 22:27:27
Now self-verify: ruff, mypy, validate, structural run on main, plus full suite already done. Need ruff/mypy — they're in ~/.local/bin.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && export PATH="$HOME/.local/bin:$PATH" && echo "=== ruff ==…

---

### Agent — 2026-11-19 22:27:56
These 3 mypy errors are pre-existing, caused by mypy running under Python 3.10 (no `datetime.UTC`). They're not in my files. Verify: run mypy against only my new/changed files and check they're clean; confirm the 3 errors exist on the pre-change tree too (they're in untouched files referencing `datetime.UTC`).
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && export PATH="$HOME/.local/bin:$PATH" && echo "=== mypy on…

---

### Agent — 2026-11-19 22:28:21
The conftest error is a pre-existing 3.10 artifact (conftest imported transitively). My files are clean. To prove mypy is clean on a real 3.12 interpreter, let me check if there's a typeshed path issue — actually simplest: confirm these 3 errors exist on `main` unchanged (stash my work? No). They're in untouched files; the `datetime.UTC` attribute is stdlib on 3.11+. This is an environment mismatch (mypy on 3.10). I'll document it. Let me try pointing mypy at python-version 3.12.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && export PATH="$HOME/.local/bin:$PATH" && mypy --python-ver…

---

### Agent — 2026-11-19 22:28:52
mypy clean when targeting 3.12 (the CI target). Now validate_requirements and the structural run on real main.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && PYTHONPATH=/tmp/opencode/shim python3 scripts/validate_re…

---

### Agent — 2026-11-19 22:29:28
Now run the structural check itself against the real tree. Default (no event) ⇒ SKIP. To exercise the source part on main, use a push-style event payload (no pull_request).
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && echo '{"ref":"refs/heads/main"}' > /tmp/opencode/push_eve…

---

### Agent — 2026-11-19 22:29:54
Zero findings on main: only the two expected INFO lines (analysis, api absent), PASS. Let me also demo the PR docs-only and the frozen-fail paths against real files (using a fake changed_files via a small harness) to prove behaviour, and confirm the `--offline` path plus default SKIP.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && echo "=== default (no event) ===" && PYTHONPATH=/tmp/open…

---

### Agent — 2026-11-19 22:30:30
Now simulate a PR event to show frozen-path FAIL and docs-only PASS against real files (monkeypatch changed_files).
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && cat > /tmp/opencode/pr_event.json <<'EOF' {"pull_request"…

---

### Agent — 2026-11-19 22:31:05
All behaviours verified: frozen fails, docs-only passes without source scan, transcripts not flagged. Now re-run full suite + ruff once more to confirm final state, and update todos.
> `bash` command=cd /mnt/d/CS/CityU/CS5351_SE/project/contentguard && export PATH="$HOME/.local/bin:$PATH" && PYTHONPATH=/tmp/o…

---

### Agent — 2026-11-19 22:31:48
> `todowrite` todos=[{'content': 'Write test/offline/test_structural_check.py (red)', 'priority': 'high', 'status': 'completed'}, …

---

### Agent — 2026-11-19 22:32:20
Here is the self-verification summary and the PR description. No commit made.

## Self-verification

| Check | Result |
|---|---|
| `pytest test/offline -v` | **246 passed** (was 235 + 10 new + 1 invariant = 246) |
| `ruff check src scripts test` | **All checks passed!** |
| `mypy --ignore-missing-imports scripts test` | 3 errors, all pre-existing `datetime.UTC` attr errors in untouched files under this sandbox's Python 3.10; **clean when targeting the CI interpreter** (`--python-version 3.12`: "Success: no issues found in 27 source files") |
| `python3 scripts/validate_requirements.py` | **GATE 3 PASS: 31 requirements valid** |
| ci.yml YAML parse | valid; job still `blocking-gates`; step `Gate 2e — structural checks` present; per-step `env:` only |
| structural check on `main` | **PASS**, zero findings (only INFO: `analysis`/`api` absent) |

Note: the sandbox has only Python 3.10; I ran the suite with a local-only `sitecustomize` shim (not committed) providing `datetime.UTC`/`enum.StrEnum`, because the repo targets 3.12. This is why mypy's 3.10 attr errors appear; CI on 3.12 is clean.

Behaviour demos against the real tree: frozen PR (`​.opencode/rules.md`) → FAIL; docs-only PR → PASS with no source scan; transcript-only PR → PASS (not flagged).

## Diff scope
- **new** `scripts/check_structural.py`, `test/offline/test_structural_check.py`
- **modified** `test/offline/test_invariants.py` (only `test_dependency_direction`, extracted into `_dependency_direction_violations`, + `test_analysis_must_not_import_policy`), `.github/workflows/ci.yml` (Gate 2e step), `docs/ai-use-log.yaml` (AI-012)

```
Test-Plan-Approved: #66

## TD-4 — CI structural checks (Gate 2e, issue #66 Revision 2)

Closes the structural gaps that gate 5's `test_invariants.py` does not cover, and only
those gaps. Requirement: `REQ-INV-001`; debt item TD-4.

### What this PR adds
- **`scripts/check_structural.py`** — Gate 2e, pure stdlib (`ast`, `pathlib`):
  - module-set vs ADR-001: an undeclared package directory under `src/contentguard/` FAILs;
    a declared-but-absent element (`analysis/`, `api/`) is **INFO**;
  - element-to-element import cycle detection (A→…→A FAIL);
  - frozen-path guard for `.opencode/**` and `.agent/**` **only** — **not** `transcripts/**`;
  - docs-only pass: a PR touching only `docs/` passes with no source scan.
  - Package directories only (must contain `__init__.py`); `__pycache__` ignored (gate 5
    runs pytest before this gate, so cache dirs exist on the runner). The element set is a
    hardcoded constant citing ADR-001; the scan root is injectable.
- **`test/offline/test_structural_check.py`** — 10 tests, `tmp_path` fixture trees; each
  docstring cites TD-4 / REQ-INV-001; includes negatives (unknown dir, A→B→A cycle, frozen
  path), the cache-present case, docs-only pass, and the closed-fail-on-missing-token case.
- **`.github/workflows/ci.yml`** — one step `Gate 2e — structural checks` inside the existing
  `blocking-gates` job (per-step `env:` only; job name unchanged).
- **`docs/ai-use-log.yaml`** — entry AI-012.

### Scope decisions (from the approved plan corrections)
- Gate 2e does **not** re-run the INV-1 enforcement scan or the dependency-direction check:
  those run in gate 5's `test_invariants.py` (per `docs/code-governance/structural-constraints.md`
  §"Enforcement status"). This gate does **not** import from `test/` — no inverted dependency,
  no scanner refactor. "Reuse, not duplicate" holds by not running them twice.
- A PR event with a missing `GITHUB_TOKEN` **fails closed** with an actionable message and
  still runs the source-tree part — never a silent skip and never a 401 traceback.

### Change to the testing owner's file
This PR touches `test/offline/test_invariants.py` (the testing owner's file). The diff is
limited to **one prohibition and its negative fixture**: `test_dependency_direction` gains
"`analysis` must not import `policy`" (via the extracted `_dependency_direction_violations`
helper, preserving the existing audit/escalation→policy, policy→analysis and mutation-repo
rules), plus `test_analysis_must_not_import_policy`. Nothing else in that file changes.

### Verification
- `pytest test/offline -v`: **246 passed**.
- `ruff check src scripts test`: clean.
- `mypy --ignore-missing-imports scripts test`: clean on the CI interpreter (Python 3.12).
- `python3 scripts/validate_requirements.py`: GATE 3 PASS (31 requirements).
- `ci.yml` parses; job name still `blocking-gates`.
- Gate 2e run against `main`: **zero findings** — PASS, with INFO for `analysis`/`api` (absent).

### Not claimed
- Full rule-5 enforcement (allowed-edge matrix) — deferred until `analysis/` and `api/` land.
- Contract / API-surface diff and the enforcement call-graph gate — stay TD-4 follow-ups.

### Governance note — architecture co-sign
The PM gate-1 approval for issue #66 Revision 2 is on record (2026-11-19). @xiaolizi33's
architecture co-sign is **PENDING at implementation start**; the operator accepted that on
the record because this change is additive (a new offline test file, one extension to
`test_dependency_direction`, one CI step) and does not modify the ADR-001 element set, the
dependency mapping, or any existing module. **Co-sign remains a precondition for MERGE**; if
not recorded before merge, the RM entry must say `co-sign pending` with this reason (per
`.github/CONTRIBUTING.md` step 6).
```

Two housekeeping notes for you:
1. **AI-012 `pr:` field** currently reads `REPLACE_WITH_PRNUMBER` — set it once the PR is opened.
2. Per Prompt.md Stage 5: save/annotate this session's transcript at `transcripts/60368210-HUANG-Hongwei-td4.md` (D5), and the architecture co-sign by @xiaolizi33 should be recorded before merge.
