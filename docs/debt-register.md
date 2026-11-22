# Technical Debt Register (D4) — AI-era categories

> Tracked categories (project sheet D4): prompt rot, hallucinated dependencies,
> untouchable code, hidden dependencies, agent-induced bloat, evaluation debt,
> guardrail debt, human/cognitive debt.

| # | Category | Description | Impact | Pay-down plan | Added by | Status |
|---|---|---|---|---|---|---|
| TD-1 | evaluation debt | Semantic evaluation harness + fixed eval set not yet implemented; CI gate 4 currently warns instead of blocking | prompt/model changes reach merge without behavioral evidence | S4/S5 (11/19–20): eval set (Buna) + self-built `scripts/eval_runner.py` (stdlib + JSONL — **harness selected 2026-11-16**; rationale, replay-vs-live split and thresholds in `docs/code-governance/verification-constraints.md` §Tier 3); flip gate 4 to `--strict` once ≥100 labeled rows and the recorded-replay path is green twice in a row | scaffold, 2026-11-15 | closed via PR #57 (merged 2026-11-19) |
| TD-2 | guardrail debt | Gate 1 (test approval) checks only the PR-body marker; issue-existence and before-implementation timestamp checks not yet enforced | weak enforcement of tests-before-code | S4 (11/19): tighten `scripts/check_test_approval.py` to resolve the cited issue and compare timestamps | scaffold, 2026-11-15 | closed via PR #61 (merged 2026-11-19) |
| TD-3 | guardrail debt | Scaffold seed files (`ci.yml`, `scripts/**`, `test/offline/test_smoke.py`, `prompts/prompt_v1.0.yaml`, `pytest.ini`, `src/README.md`) were human-drafted pre-arrangement references — per the agentic red line (proposal §1.3) they must be regenerated through OpenCode sessions before counting as agent-generated baseline | red-line compliance; D5 transcript coverage for the governance/CI line | S4 (11/19): regenerate the remaining scaffold seed through an OpenCode session (AI-001 already covered `ci.yml` + `scripts/**`) | PM, 2026-11-15 | partial |
| TD-4 | guardrail debt | CI structural check was missing (module boundaries, permission conformance, INV-1 call-graph fitness function) — permission-model/GR-1/structural-constraints referenced it before it existed; implemented as gate 2e in PR #69 | ghost enforcement claims (D7 consistency); INV-1 structural verification missing | S4 (11/19): implement the structural check and wire it into `blocking-gates` | audit, 2026-11-15 | closed via PR #69 (merged 2026-11-20) |
| TD-5 | prompt rot | `prompt_v1.1.yaml` is reserved; the first prompt change must be versioned and pass gate 4 before merge | stale/untested prompt wording reaches the app | S3/S4: version the prompt, run the eval set, record the result in `evaluation-logbook.md` | Phase ② review, 2026-11-16 | open |
| TD-6 | human/cognitive debt | Five transcripts + a growing memo backlog are due in a short window; the PM is the default reviewer | missed D5/D4 evidence; review bottleneck | Daily checkpoints from 11/17; delegate domain reviews/memos; transcript lock 11/21 | Phase ② review, 2026-11-16 | open |
| TD-7 | agent-induced bloat | Build sessions may add unnecessary abstractions, flags, or dependencies | review/maintenance cost; scope creep | ADR-001 abstraction limits; small PRs; PM/test-owner review | Phase ② review, 2026-11-16 | open |
| TD-8 | hallucinated dependencies | Agent may import undeclared packages in build sessions | CI/type failures; supply-chain risk | Declare runtime/test dependencies in a manifest; add a dependency check to gate 2 (S4) | Phase ② review, 2026-11-16 | open |
| TD-9 | guardrail debt | Proposed gate 7 (review-memo presence gate) not implemented; PM decision 2026-11-16 to defer during the build window (issue #4) | memos remain process-enforced, not machine-enforced | Revisit after the 11/21 lock / submission; use issue #4's implementation spec | PM, 2026-11-16 | deferred |
| TD-10 | guardrail debt | Gate 1/6 PR-file scope (`scripts/pr_files.py` CODE_PREFIXES) covers `src/ test/ prompts/ scripts/` but not `.github/workflows/`, `pytest.ini`, `requirements.txt` — a workflows-only PR would bypass both gates | latent bypass of gates 1/6; no occurrence to date (every CI-touching PR also touched `scripts/`) | OpenCode session PR: add the three paths to CODE_PREFIXES (post-submission window) | PM, 2026-11-20 | open |
| TD-11 | guardrail debt | AGENTS.md §4's agent-session definition assumes code changes run through (OpenCode) agent sessions; multiple disclosed zcode sessions (AI-017/AI-018 in PR #83, AI-019 in PR #75 — RM-042 path B) already operated outside that definition — rule text and practice have silently diverged (RM-036 class: docs say A, machine runs B) | governance wording vs. actual practice mismatch; future sessions have no written license for the actual tooling in use | Post-submission window: amend AGENTS.md §4 to define "agent session" agent-neutrally (or record the disclosed zcode exception explicitly) | review RM-047 (Huang, Li), 2026-11-22 | open |
| — | — | — | — | — | — | — |

> Discipline: every review memo or bug-diary entry that spots debt adds a row; rows
> leave the register only via a PR that removes the debt (verdict APPROVE).

## Progress notes

- **2026-11-15 (RM-001, AI-001):** gate 1/4/6 PR-file fetch 401 fixed
  (`scripts/pr_files.py` no longer sends an empty `Authorization` header;
  `changed_files()` raises an actionable error; gates 1/4 got a per-step
  `GITHUB_TOKEN`; workflow declares least-privilege `permissions`).
  - TD-1: gate 4 is now reachable in CI; still **warn-only** → remains **open**.
  - TD-2: gate 1 helper hardened for API failures; marker-only enforcement
    unchanged → remains **open**.
  - TD-3: `ci.yml` + `scripts/check_*.py` + `scripts/pr_files.py` regenerated/refined
    through the OpenCode session (AI-001); remaining scaffold seed still to regenerate
    → **partial**.
  - TD-4: script hardening only; structural check **not** implemented → remains
    **open**.
- **2026-11-16 (Phase ② close):** D2 support artifacts drafted (memory design,
  evaluation table, runtime policy catalog, option ledger, evaluation logbook, risk
  list); trace-matrix rows prepared for PR #11. Local checks green: gate 3, pytest
  offline, ruff, mypy. TD-1..TD-4 remain open with S4 pay-down dates; TD-5..TD-9 added
  for build-phase tracking (TD-9 records the gate-7 deferral per issue #4).
- **2026-11-18 (issue #42, AI-008):** TD-3 scaffold seed regenerated through an OpenCode
  session — `test/offline/test_smoke.py` (31-ID trace coverage preserved, added a negative
  vacuity test), `prompts/prompt_v1.0.yaml` (ADR-001 advisory contract; `prompt_v1.1.yaml`
  still reserved), `pytest.ini` (`testpaths = test/offline`) and `src/README.md` (module
  layout + authority boundary). TD-8: `requirements.txt` is now the single toolchain source
  (`ci.yml` installs from it) with a gate-2 `pip check` + manifest step
  (`scripts/check_dependencies.py`). TD-4 (partial): path-conditional safety tier
  (`scripts/check_safety_paths.py`) requires an ADR/invariant reference on policy/eval PRs;
  contract diff, API-surface diff and the structural call-graph check remain TODO(TD-4).
  Statuses leave the register only on the follow-up merge-and-verify PR, so TD-3/TD-8
  stay **partial/open** here; TD-4 is closed by #69 (2026-11-20).
- **2026-11-20 (docs consistency pass):** TD-1 closed — gate 4 is `--strict` blocking on
  the fixed eval set + replay converter (squash `8e7e2af`, PR #57), and the release
  acceptance tests assert strict blocking (PR #62). TD-2 closed — gate 1 resolves the
  cited test-plan issue and verifies the approval predates implementation (squash
  `6264e89`, PR #61). TD-10 added for the gate-1/6 path-scope gap. TD-4 closed — the
  structural checks are active as gate 2e (`scripts/check_structural.py`, PR #69, merged
  `6b91946`); the INV-1 scan and dependency-direction checks stay in gate 5, and the
  semantic authority boundary plus rule-6 authorship remain review duties.
