# Technical Debt Register (D4) — AI-era categories

> Tracked categories (project sheet D4): prompt rot, hallucinated dependencies,
> untouchable code, hidden dependencies, agent-induced bloat, evaluation debt,
> guardrail debt, human/cognitive debt.

| # | Category | Description | Impact | Pay-down plan | Added by | Status |
|---|---|---|---|---|---|---|
| TD-1 | evaluation debt | Semantic evaluation harness + fixed eval set not yet implemented; CI gate 4 currently warns instead of blocking | prompt/model changes reach merge without behavioral evidence | W12/W13: build eval set + runner; flip gate 4 to blocking | scaffold, 2026-11-15 | open |
| TD-2 | guardrail debt | Gate 1 (test approval) checks only the PR-body marker; issue-existence and before-implementation timestamp checks not yet enforced | weak enforcement of tests-before-code | W12: tighten `scripts/check_test_approval.py` to resolve the cited issue and compare timestamps | scaffold, 2026-11-15 | open |
| TD-3 | guardrail debt | Scaffold seed files (`ci.yml`, `scripts/**`, `test/offline/test_smoke.py`, `prompts/prompt_v1.0.yaml`) were human-drafted pre-arrangement references — per the agentic red line (proposal §1.3) they must be regenerated through OpenCode sessions before counting as agent-generated baseline | red-line compliance; D5 transcript coverage for the governance/CI line | governance-CI owner regenerates in session 4 (11-17 → 11-20) | PM, 2026-11-15 | open |
| TD-4 | guardrail debt | CI structural check not implemented (module boundaries, permission conformance, INV-1 call-graph fitness function) — permission-model/GR-1/structural-constraints referenced it before it exists | ghost enforcement claims (D7 consistency); INV-1 structural verification missing | build in the governance-CI session (11-17 → 11-20) alongside gate hardening | audit, 2026-11-15 | open |
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
