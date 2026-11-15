# MCP Tool Manifest (D3)

> The tools the coding agent may call, and which roles may call them.
> **Status: DRAFT** — aligned with `.opencode/permissions.jsonc`; the course baseline
> agent is **OpenCode** (all assessments are based on it).

| Tool / capability | plan-agent | code-agent | verify-agent | Notes |
|---|---|---|---|---|
| Read files (whitelisted paths) | ✅ | ✅ | ✅ | Whitelist per permission model; default deny |
| Write files (whitelisted paths) | ❌ | ✅ `src/**`, `test/**`, `prompts/**` | ✅ report paths only | See rights matrix |
| Shell: run pytest / ruff / mypy | ❌ | ✅ | ✅ | Verification commands only |
| Shell: network access | ❌ | ❌ (except configured LLM API client in live tests) | ❌ | Deterministic tests must be offline |
| Web search / fetch | ❌ | ❌ | ❌ | Not needed for the build pipeline |
| Git commit / push | ❌ | ❌ | ❌ | Humans perform all git operations; agent output lands via PR |
| MCP servers | TBD | TBD | TBD | Registered here as they are enabled; each entry names its permitted roles |

> Rule: any tool not listed here is not available to any agent role. Adding a tool
> requires a human edit to this manifest **and** `.opencode/permissions.jsonc` in the
> same change.
