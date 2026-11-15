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
| `test/**` | read | read/write | read/write (reports only) | read/write |
| `prompts/**` | read | read/write (triggers gate 4) | read | read/write |
| `scripts/**` | read | read/write (via agent session — red line) | read | read/write |
| `.github/workflows/**` | read | read/write (via agent session — red line) | read | read/write |
| `.opencode/**`, `.agent/**` | none | none | none | read/write (human-only) |
| `transcripts/**` | none | none | none | read/write (human-only; sanitized before commit) |
| `.env*`, `token*` (secrets) | none | none | none | read locally only; never committed |

## Guard rules & enforcement

1. Default deny: any path not listed above is unreadable and unwritable for agents.
2. Human-only files are additionally guarded by CI (structural check rejects agent
   commits touching them without a human co-author).
3. Safety-critical paths (`src/contentguard/policy/**`, anything named in the invariant
   register) require human review **with an architecture decision** per branch
   protection (project sheet §6).
4. Violations: the CI structural gate blocks the merge; the incident is logged in
   `docs/bug-diary.md` with the invariant gap it exposed.
