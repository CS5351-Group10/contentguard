# ContentGuard

Community content moderation guard: an AI-enabled web service that triages user-generated
content. An LLM performs moderation **analysis** (verdict, severity, rationale) as an
**advisory** component; every **enforcement** decision (approve / hold / reject / escalate)
is made exclusively by a deterministic policy engine constrained by auditable invariants.
This advisory-vs-authoritative split is the safety-relevant boundary required by the
CS5351 Agentic Software Engineering Project specification (D1–D9, §6 blocking gates).

> **Status:** Phase ② closing (2026-11-16): blocking-gates green (11-16 CI fix, PR #7);
> man-hours protocol under review (PR #8); requirements registry v1.0 under review
> (PR #11); evaluation set due today. Working log: `docs/contribution-log.md`.

## Repository organization

| Path | Purpose | Spec item |
|---|---|---|
| `AGENTS.md` | Single entry point for the AI coding agent (build target, reading order, permissions baseline, verification requirements) | D3 |
| `Prompt.md` | The one static startup prompt the agent reads after `AGENTS.md` | D9 |
| `architecture-blueprint.md` | Master constraint document read by the Plan agent | D2.1 |
| `Report.md` | Process report + per-member reflections + relative contributions | D6 |
| `docs/req/requirements.yaml` | Machine-readable PRD / consolidated requirements registry | D1 |
| `docs/req/req-schema.json` | JSON Schema validating the registry (CI gate 3) | D1 |
| `docs/architecture/` | ADR, invariants, trace matrix, permission model, runtime policy catalog, etc. | D2 |
| `docs/code-governance/` | Structural constraints, verification constraints, MCP tool manifest | D3/D4 |
| `docs/ai-use-log.yaml` | Mandatory AI-use log (updated with every code/prompt change) | D1, gate 6 |
| `docs/review-memo.md` | One review memo per pull request, ending in a verdict | D4 |
| `docs/team/` | Team roster cards (one per member) + first-PR exercise guide (feeds `Report.md` §1) | D6 |
| `docs/debt-register.md` | AI-era technical debt tracker | D4 |
| `docs/bug-diary.md` | Diary entry per significant bug | D4 |
| `docs/contribution-log.md` | Working log of man-hours / story points (feeds the D6 contribution table) | D6 |
| `.opencode/` | Project-level OpenCode permission model + always-on behavioral rules | D3 |
| `.agent/rules.md` | Project covenant (abstraction limits, negative tests, safety-critical change policy) | D3 |
| `.github/workflows/ci.yml` | CI/CD pipeline implementing the six blocking gates | D4/D7 |
| `scripts/` | CI gate helper scripts (schema validation, AI-use-log check, etc.) | §6 |
| `prompts/` | Versioned runtime prompts for the AI component | — |
| `src/` | Application source; module names match architectural elements | D8 |
| `test/offline/` | Deterministic offline tests (no API access) | D4/D8 |
| `test/live/` | Live tests requiring API access | D4/D8 |
| `transcripts/` | Annotated AI-agent session transcripts (human-authorship evidence) | D5 |

## How to run the tests

```bash
# Deterministic offline suite (default, no API access needed)
pytest test/offline -v

# Live tests (requires API key in the environment; cost-aware)
pytest test/live -v

# Full suite (offline + live)
pytest test -v

# Single-tier verification helpers used by CI
python scripts/validate_requirements.py   # gate 3: registry validates against its schema
ruff check src scripts test               # gate 2: lint
mypy scripts test                          # gate 2: type check
```

## GitHub repository

https://github.com/CS5351-Group10/contentguard (public; owned by the team org
CS5351-Group10 — transferred from the PM's personal account on 2026-11-15 so
members can hold repository-admin roles for CI governance). Branch protection on
`main`: the CI check `blocking-gates` must pass before merge, and safety-critical
paths additionally require human review with an accompanying architecture decision
(§6) — machine-enforced via CODEOWNERS once domain owners onboard; review-process
enforced until then.

## Blocking-gate design (§6)

| # | Gate | What it enforces | Where implemented | Status |
|---|---|---|---|---|
| 1 | Test approval | No code change merges unless its tests were approved before implementation began; PR must cite the approved test plan | `scripts/check_test_approval.py` (PR body marker) | Active (basic) — tightened W12 |
| 2 | Static analysis | Lint + type-check on every commit; extra checks on safety-relevant paths | `ruff` + `mypy` in `ci.yml` | Active |
| 3 | Schema | Requirements registry validates against `docs/req/req-schema.json` | `scripts/validate_requirements.py` | Active |
| 4 | Semantic evaluation | Prompt/model changes replay a fixed evaluation set against quality thresholds | `scripts/check_semantic_eval.py` | Skeleton (warns) — harness W12; tracked in debt register |
| 5 | Regression | Every change runs all prior test suites; any regression blocks merge | `pytest test/offline` in `ci.yml` | Active |
| 6 | AI-use log | PR changing code/prompts without updating `docs/ai-use-log.yaml` is blocked | `scripts/check_ai_use_log.py` | Active |

## Team

Live roster: `docs/team/` (members add themselves via PR; index in
`docs/team/README.md`). The final table with names, student IDs, and relative
contributions is transcribed into `Report.md` §1 at submission; man-hours evidence
lives in `docs/contribution-log.md`.
