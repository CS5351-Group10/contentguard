# OpenCode Project Rules — always-on behavioral rules (D3)

> **HUMAN-ONLY FILE.** The coding agent must never edit this file. Loaded on every
> OpenCode session in this repository.

1. Read `AGENTS.md` first, then its reading order, before any action.
2. Follow `Prompt.md` stage gates exactly; stop for human approval where it says stop.
3. Never read, write, or traverse secret files: `.env*`, `token*`, anything ignored by
   `.gitignore` under the secrets section.
4. Never write to frozen/human-only paths: `.opencode/**`, `.agent/**`, `.github/**`,
   `transcripts/**`, `docs/req/**`, `docs/architecture/**` (propose via PR instead).
5. Never generate code before the execution plan is human-approved (gate 1: tests
   approved before implementation began — write tests first, per the approved plan).
6. Every feature ships with at least one negative test (`.agent/rules.md` covenant).
7. Every test docstring cites the REQ-*/INV-* ID it verifies.
8. If a requirement or architecture statement is ambiguous — stop and ask a human;
   never guess and never silently reinterpret the registry.
9. Report honestly: if a verification command fails, show the failure; never claim
   success without showing command output.
10. Announce in the PR description whenever the change touches `prompts/**` or model
    configuration (semantic evaluation gate applies).
11. Do not run `git commit`/`git push`; deliver work as PRs (humans operate git).
12. Keep PRs small: one feature or one invariant slice per PR.
