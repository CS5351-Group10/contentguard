# MCP Tool Manifest (D3)

> The tools the coding agent may call, and which roles may call them.
> Status: Phase ② baseline (2026-11-16) — aligned with `.opencode/permissions.jsonc`;
> the course baseline agent is **OpenCode** (all assessments are based on it).

| Tool / capability | plan-agent | code-agent | verify-agent | Notes |
|---|---|---|---|---|
| Read files (whitelisted paths) | ✅ | ✅ | ✅ | Whitelist per permission model; default deny |
| Write files (whitelisted paths) | ❌ | ✅ `src/**`, `test/**`, `prompts/**`, `scripts/**`, `.github/workflows/**`† | ✅ report paths only | † `.github/workflows/**` only: governance/CI owner's agent session, with PM + governance-owner human review (see the note below) |
| Shell: run pytest / ruff / mypy | ❌ | ✅ | ✅ | Verification commands only |
| Shell: network access | ❌ | ❌ (live tests are human/CI-authorized — see note) | ❌ (live tests are human/CI-authorized — see note) | Deterministic tests must be offline |
| Web search / fetch | ❌ | ❌ | ❌ | Not needed for the build pipeline |
| Git commit / push | ❌ | ❌ | ❌ | Humans perform all git operations; agent output lands via PR |
| MCP servers | ❌ | ❌ | ❌ | **None enabled in the MVP.** Adding one requires a human edit to this manifest and `.opencode/permissions.jsonc` in the same change, naming the permitted roles |

> Rule: any tool not listed here is not available to any agent role. Adding a tool
> requires a human edit to this manifest **and** `.opencode/permissions.jsonc` in the
> same change. The manifest is cross-checked against the `guard_rules` in
> `.opencode/permissions.jsonc` at every governance review.
>
> **† CI configuration (`workflows/**`) writes:** `.github/workflows/**` is not an ordinary
> feature-work path — the agentic red line puts CI configuration in agent-session-only
> territory. It is writable only by the governance/CI owner's OpenCode session, with PM +
> governance-owner human review in the PR.
>
> **`scripts/**` is ordinary agent-writable code.** Any code-agent session may write it,
> exactly as `AGENTS.md` §4 and `docs/architecture/permission-model.md` say ("modifiable,
> with verification requirements") — the gate scripts are not a special class. Gate 2a/2b
> (lint, type), gate 5 (regression) and gate 6 (AI-use log) apply as they do to `src/**`.
> An earlier revision of this file narrowed `scripts/**` to the governance/CI session only;
> that was wrong, it contradicted the permission model, and it is corrected here (it would
> also have made the testing line's `scripts/build_evaluation_dataset.py` a violation).
> `prompts/**` changes still trigger gate 4.
>
> **Live tests:** `test/live` is not an agent capability in the offline pipeline. An
> explicitly authorized human-run or CI job may execute live tests with provider
> credentials; the verify-agent's regression path stays network-free and uses recorded
> fixtures. No agent role receives provider credentials.
