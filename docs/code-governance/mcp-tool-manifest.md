# MCP Tool Manifest (D3)

> The tools the coding agent may call, and which roles may call them.
> Status: Phase ② baseline (2026-11-16) — aligned with `.opencode/permissions.jsonc`;
> the course baseline agent is **OpenCode** (all assessments are based on it).

| Tool / capability | plan-agent | code-agent | verify-agent | Notes |
|---|---|---|---|---|
| Read files (whitelisted paths) | ✅ | ✅ | ✅ | Whitelist per permission model; default deny |
| Write files (whitelisted paths) | ❌ | ✅ `src/**`, `test/**`, `prompts/**`, `scripts/**`†, `.github/workflows/**`† | ✅ report paths only | † governance/CI owner's agent session only, with PM + governance-owner human review; see rights matrix |
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
> **† Governance/CI writes:** `scripts/**` and `.github/workflows/**` are not ordinary
> feature-work paths. They are writable only by the governance/CI owner's OpenCode
> session, with PM + governance-owner human review in the PR. `prompts/**` changes still
> trigger gate 4.
>
> **Live tests:** `test/live` is not an agent capability in the offline pipeline. An
> explicitly authorized human-run or CI job may execute live tests with provider
> credentials; the verify-agent's regression path stays network-free and uses recorded
> fixtures. No agent role receives provider credentials.
