# Verification Constraints (D4)

> The rules the verification agent (and human reviewers) apply. Four tiers of verification:
> **static analysis & dependency (Tier 0)**, **structural (Tier 1)**, **regression
> (Tier 2)**, **behavioral (Tier 3)**.

## Universal rules

1. Every fit criterion in `docs/req/requirements.yaml` has **at least one test**.
2. Every invariant has at least one test that **fails when the invariant is violated**
   (negative test — required per feature by `.agent/rules.md`).
3. Every test references the requirement or invariant ID it verifies (docstring).
4. Every new round of work runs **all** previous rounds' test suites with **zero
   regressions** (CI gate 5; `pytest test/offline` = the full deterministic suite).
5. The test plan exists **and was approved before implementation started** (CI gate 1):
   an issue opened from `.github/ISSUE_TEMPLATE/test-plan.md`, cited in the PR body as
   `Test-Plan-Approved: #<n>`. Gate 1 today only matches that marker; resolving the issue
   and comparing its approval time with the first implementation commit is **TD-2**.
6. A PR that changes code, tests, scripts or prompts updates `docs/ai-use-log.yaml` in the
   same PR (CI gate 6 — its path set is `src/`, `test/`, `prompts/`, `scripts/`). The entry
   names the session, the model, the scope, and the human interventions — the transcript is
   the evidence behind it (D5).

## Tier 0 — Static analysis and dependency (every commit / PR)

- Lint (`ruff`) and type-check (`mypy`) on every commit (CI gate 2, first tier).
- **Dependency check** (CI gate 2, second tier): a declared manifest must exist and
  resolve — `requirements.txt` (or `pyproject.toml`) plus `pip check` / `pip-audit`.
  The failure this catches is an agent importing a package nobody declared
  (**TD-8**); nothing else notices it until runtime.
- On a PR touching a **safety-relevant path** (`src/contentguard/policy/**`, files named in
  `docs/architecture/invariants.md`): contract checks against
  `docs/architecture/interface-contracts.md`, security scan, API-surface diff, and
  permission conformance — the project sheet §6 "second tier" of gate 2 that the
  workflow does not yet run path-conditionally.

## Tier 1 — Structural (every commit / PR)

- Imports, module boundaries, one-to-one element↔module mapping
  (`docs/code-governance/structural-constraints.md`).
- Permissions conformance: agent PRs touch only whitelisted paths
  (`docs/architecture/permission-model.md`).
- Architectural fitness functions: call-graph check that enforcement API is reachable
  only from `src/contentguard/policy/` (INV-1) — **planned, TD-4**.

## Tier 2 — Regression (every PR)

- Full prior suites: `pytest test/offline -v` (deterministic; no network).
- Deterministic tests live in `test/offline/`; **live** tests (needing API access) in
  `test/live/` and never run in the offline regression tier.

## Tier 3 — Behavioral (quality thresholds)

- Semantic evaluation for the AI component: a fixed evaluation set
  (`test/eval/moderation_eval.jsonl`) replayed by CI gate 4 on any prompt or model change.
- **Harness decision (2026-11-16, TD-1):** run it with our own `scripts/eval_runner.py`
  (stdlib + JSONL) rather than a third-party eval CLI. Reasons: the repo's other gates are
  already hand-rolled stdlib scripts with one error style, `promptfoo` would add a Node
  toolchain to a Python CI, and the paired `deepeval`/`ragas`-style frameworks pull model
  SDKs into the offline tier. What we need is small: load rows, compare verdicts, compute
  per-slice rates, exit nonzero. The runner is `scripts/**` code, so it gets written in an
  OpenCode session like every other gate script — a docs PR does not get to slip it in.
- **Replay, not live, in CI:** the runner replays **recorded** model outputs, so the gate is
  deterministic and needs no provider secret (a fork PR cannot even see one). `--live` is
  opt-in for local/nightly use and must not gate a merge until the live suite is stable.
- Metrics and thresholds (provisional until the eval set lands; owned with Buna):
  - verdict agreement with the labeled set ≥ **0.80**
  - **zero safety escapes** — any high-severity item the pipeline auto-approves fails the
    gate outright; this is a hard 0, never averaged
  - false-block (误杀) rate ≤ **0.10**, reported **per slice** so a good average cannot hide
    a bad identity-bias slice
  - rationale faithfulness/relevance ≥ agreed threshold (LLM-judge rubric, optional in v1)
- `--strict` flips gate 4 from warn to block. It turns on when (a) the eval set has ≥100
  labeled rows **and** (b) the recorded-replay path is green twice in a row — target S4
  (11/19–20), tracked as TD-1.
- Fault-injection: AI-unavailable paths behave per runtime policy catalog R-1/R-2.

## Evidence discipline

- Gate failures are never waived silently; a waiver requires a review-memo entry with
  verdict CHANGES REQUIRED→APPROVE chain and a debt-register line.
- `docs/review-memo.md`: one memo per PR — spec alignment, architecture alignment,
  code & test quality, operational metadata, security & efficiency throughout, ending
  in APPROVE / CHANGES REQUIRED / REJECT.
