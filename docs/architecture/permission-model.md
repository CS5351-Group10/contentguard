# Permission Model (D2.6)

> File-level read/write rights per AI coding agent role. **Default: no read, no write —
> every path is explicitly whitelisted.** Machine-readable form: `.opencode/permissions.jsonc`
> (this document is the human-readable authority; keep the two in lockstep).

## Roles

| Role | Purpose |
|---|---|
| `plan-agent` | Produces execution plans per `Prompt.md`; read-only |
| `code-agent` | Implements approved plans (src/test) |
| `verify-agent` | Runs verification suites and reports results; writes only reports |

## Rights matrix

| Path | plan-agent | code-agent | verify-agent | Human |
|---|---|---|---|---|
| `AGENTS.md`, `Prompt.md`, `architecture-blueprint.md` | read | read | read | read/write |
| `docs/req/**` | read | read | read | read/write (only humans may change) |
| `docs/architecture/**` | read | read | read | read/write (only humans may change) |
| `docs/code-governance/**` | read | read | read | read/write (only humans may change) |
| `docs/review-memo.md` | read | read | read | read/write |
| `docs/ai-use-log.yaml` | read | read | read | read/write |
| `docs/debt-register.md`, `docs/bug-diary.md` | read | propose in PR | read | read/write |
| `src/**` | read | read/write (post-ADR-001) | read | read/write |
| `test/**` | read | read/write | read/write (`test/reports/**` only) | read/write |
| `prompts/**` | read | read/write (triggers gate 4) | read | read/write |
| `scripts/**` | read | read/write (via agent session — red line) | read | read/write |
| `.github/workflows/**` | read | read/write (via agent session — red line) | read | read/write |
| `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/**` | read | read (propose in PR) | read | read/write (human-only governance config) |
| `.opencode/**`, `.agent/**` | none | none | none | read/write (human-only) |
| `transcripts/**` | none | none | none | read/write (human-only; sanitized before commit) |
| `.env*`, `token*` (secrets) | none | none | none | read locally only; never committed |

## Guard rules & enforcement

1. Default deny: any path not listed above is unreadable and unwritable for agents.
2. Human-only files are additionally guarded by a planned CI structural check —
   **not yet implemented (TD-4)**; until then humans enforce via review memos.
3. Safety-critical paths (`src/contentguard/policy/**`, anything named in the invariant
   register) require human review **with an architecture decision** per branch
   protection (project sheet §6).
4. Violations: once the planned structural check lands (TD-4), CI blocks the merge;
   until then the review memo rejects the PR. Either way the incident is logged in
   `docs/bug-diary.md` with the invariant gap it exposed.
