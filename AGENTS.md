# AGENTS.md — Coding-Agent Governance (D3)

This file is the **single entry point** for the AI coding agent (OpenCode). Read it fully
before doing anything. Then follow the reading order below and obey the authority
boundaries. This is a human-owned file; changes require human commit and review.

## 1. Build target

**ContentGuard** — a community content moderation guard with:
- an LLM-powered moderation **analysis** component (advisory only: verdict, severity, rationale), and
- a deterministic **policy engine** (authoritative: it, and only it, decides enforcement actions),
- a human review queue for escalated content,
- an audit log of every decision.

MVP scope is defined by `docs/req/requirements.yaml` (MoSCoW). **Must** requirements define
the MVP; anything else is out of scope unless a human explicitly changes the registry.

## 2. Reading order (mandatory)

1. `AGENTS.md` (this file)
2. `architecture-blueprint.md` — master constraints (scope, drivers, boundaries, authority)
3. `docs/architecture/adr/` — binding architecture decisions
4. `docs/architecture/invariants.md` — zero-tolerance rules you must never violate
5. `docs/req/requirements.yaml` — the requirements registry (IDs you must cite)
6. `docs/code-governance/structural-constraints.md` — module organization rules
7. `docs/code-governance/verification-constraints.md` — what "done" means
8. `.opencode/permissions.jsonc` — what you may read/write
9. `Prompt.md` — your startup instruction (execution plan → human approval → build)

## 3. Code baseline

- `src/contentguard/` implements the baseline modules: `policy/` (authoritative kernel),
  `audit/`, `escalation/`, and `analysis/` (merged via #52, `397e002`). The `api/`
  module lands via the S2 session (2026-11-20, in flight) — see ADR-001 and
  `docs/code-governance/structural-constraints.md`. Do not create modules outside the
  ADR-001 layout.
- **Scaffold seed compliance note:** the whole scaffold seed — CI workflow,
  `scripts/**`, `prompts/**`, `test/**` scaffolding (READMEs + `test_smoke.py`),
  `pytest.ini`, `src/README.md` — was **human-drafted pre-arrangement reference**.
  Per the agentic red line (proposal §1.3: CI configuration, scripts, tests and
  prompts are changed only through agent sessions), it must be
  **regenerated/refined through OpenCode sessions** (governance-CI owner's session)
  before counting as agent-generated baseline — tracked as TD-3 in
  `docs/debt-register.md`.
- Every new module must map to exactly one architectural element (see
  `docs/code-governance/structural-constraints.md`).
- New work **extends** the baseline; never replace or rewrite an existing module wholesale.

## 4. Readable / modifiable / frozen

| Scope | Status |
|---|---|
| `docs/**`, `src/**`, `test/**`, `prompts/**`, `scripts/**`, `.github/workflows/**`, `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/**` | readable |
| `src/**`, `test/**`, `scripts/**` | modifiable (with verification requirements below) |
| `prompts/**` | modifiable, but any change triggers the semantic evaluation gate (gate 4) |
| `.github/workflows/**` | modifiable via agent session (governance-CI owner + PM review) — agentic red line: CI configuration is changed only through agent sessions |
| `docs/req/**`, `docs/architecture/**`, `.github/CODEOWNERS`, `.github/CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/**` | **human-owned** — the agent may propose changes in a PR, only humans approve. (`.github` governance config is not "CI configuration": the agentic red line covers `workflows/**` only) |
| `.opencode/rules.md`, `.opencode/permissions.jsonc`, `.agent/rules.md`, `transcripts/**` | **frozen** (human-only) |
| `.env*`, `token*` | never read, never touch (secrets) |

Machine-readable rights: `.opencode/permissions.jsonc` (default: no read, no write;
every path explicitly whitelisted).

## 5. Module organization

ADR-001 (`docs/architecture/adr/001-grounded-advisory-transactional-policy.md`,
approved 2026-11-16) fixes the module layout. Names must match architectural elements
one-to-one:

```
src/
  contentguard/
    analysis/       # AI (LLM) advisory moderation analysis — advisory component
    policy/         # deterministic policy engine — authoritative component (SAFETY-CRITICAL)
    escalation/     # human review queue routing
    audit/          # decision audit log
    api/            # service interface
```

Integration contracts between modules: `docs/architecture/interface-contracts.md`.
Dependency direction: `api → {analysis, policy}; policy → {escalation, audit}`;
`analysis` must not import `policy`; `policy` may consume validated advisory data that
`api` passes as read-only input, but must not import analysis internals or delegate
enforcement authority to the model output. The API coordinates analysis then policy.

## 6. Verification requirements (generated code must satisfy all)

1. Every fit criterion in `docs/req/requirements.yaml` that your change touches has at
   least one test; every invariant has at least one test that **fails** when the invariant
   is violated (negative test).
2. Every test references the requirement/invariant ID it verifies (in its docstring).
3. Full offline suite passes with **zero regressions**: `pytest test/offline -v`.
4. `ruff check src scripts test` and `mypy scripts test` are clean.
5. If you changed `prompts/**` or any model configuration, the semantic evaluation gate
   must pass before merge (gate 4) — announce this in the PR description.
6. You must update `docs/ai-use-log.yaml` in the same PR (gate 6 blocks otherwise).
7. Deterministic tests live in `test/offline/`, live tests in `test/live/` — never mix.

## 7. Stop conditions (you must halt and ask a human)

- Before generating any code (per `Prompt.md` execution-plan approval gate).
- Before changing any file under `docs/req/**`, `docs/architecture/**` (human-owned).
- Before changing safety-critical code (anything enforcing an invariant, `src/**/policy/`)
  — requires an architecture decision record **and** explicit human approval.
- Whenever a requirement is ambiguous — stop and ask; never guess.
