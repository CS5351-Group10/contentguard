# Technical Debt Register (D4) — AI-era categories

> Tracked categories (project sheet D4): prompt rot, hallucinated dependencies,
> untouchable code, hidden dependencies, agent-induced bloat, evaluation debt,
> guardrail debt, human/cognitive debt.

| # | Category | Description | Impact | Pay-down plan | Added by | Status |
|---|---|---|---|---|---|---|
| TD-1 | evaluation debt | Semantic evaluation harness + fixed eval set not yet implemented; CI gate 4 currently warns instead of blocking | prompt/model changes reach merge without behavioral evidence | S4/S5 (11/19–20): build the eval set + runner; flip gate 4 to `--strict` | scaffold, 2026-11-15 | open |
| TD-2 | guardrail debt | Gate 1 (test approval) checks only the PR-body marker; issue-existence and before-implementation timestamp checks not yet enforced | weak enforcement of tests-before-code | S4 (11/19): tighten `scripts/check_test_approval.py` to resolve the cited issue and compare timestamps | scaffold, 2026-11-15 | open |
| TD-3 | guardrail debt | Scaffold seed files (`ci.yml`, `scripts/**`, `test/offline/test_smoke.py`, `prompts/prompt_v1.0.yaml`, `pytest.ini`, `src/README.md`) were human-drafted pre-arrangement references — per the agentic red line (proposal §1.3) they must be regenerated through OpenCode sessions before counting as agent-generated baseline | red-line compliance; D5 transcript coverage for the governance/CI line | S4 (11/19): regenerate the remaining scaffold seed through an OpenCode session (AI-001 already covered `ci.yml` + `scripts/**`) | PM, 2026-11-15 | partial |
| TD-4 | guardrail debt | CI structural check not implemented (module boundaries, permission conformance, INV-1 call-graph fitness function) — permission-model/GR-1/structural-constraints referenced it before it exists | ghost enforcement claims (D7 consistency); INV-1 structural verification missing | S4 (11/19): implement the structural check and wire it into `blocking-gates` | audit, 2026-11-15 | open |
| TD-5 | prompt rot | `prompt_v1.1.yaml` is reserved; the first prompt change must be versioned and pass gate 4 before merge | stale/untested prompt wording reaches the app | S3/S4: version the prompt, run the eval set, record the result in `evaluation-logbook.md` | Phase ② review, 2026-11-16 | open |
| TD-6 | human/cognitive debt | Five transcripts + a growing memo backlog are due in a short window; the PM is the default reviewer | missed D5/D4 evidence; review bottleneck | Daily checkpoints from 11/17; delegate domain reviews/memos; transcript lock 11/21 | Phase ② review, 2026-11-16 | open |
| TD-7 | agent-induced bloat | Build sessions may add unnecessary abstractions, flags, or dependencies | review/maintenance cost; scope creep | ADR-001 abstraction limits; small PRs; PM/test-owner review | Phase ② review, 2026-11-16 | open |
| TD-8 | hallucinated dependencies | Agent may import undeclared packages in build sessions | CI/type failures; supply-chain risk | Declare runtime/test dependencies in a manifest; add a dependency check to gate 2 (S4) | Phase ② review, 2026-11-16 | open |
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
  offline, ruff, mypy. TD-1..TD-4 remain open with S4 pay-down dates; TD-5..TD-8 added
  for build-phase tracking.
