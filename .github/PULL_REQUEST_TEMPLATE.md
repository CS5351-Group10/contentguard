<!--
ContentGuard PR conventions (docs/review-memo.md): one logical change per PR.
Title format: <type>(<scope>): <subject> — cite REQ/INV IDs in title or body.
-->

## Requirement / invariant IDs

<!-- Cite the registry IDs this PR serves, e.g. REQ-FUN-001, REQ-INV-002. -->

## Test plan approval (gate 1)

Test-Plan-Approved: #<issue-number>

<!-- Docs-only PRs: replace the line above with "n/a (docs-only)" — gate 1
     early-passes when no code/prompt files change. -->

## AI agent session (gate 6 / D5)

- ai-use-log entry: AI-<NNN>
- Transcript: transcripts/<student-id>-<student-name>.md

<!-- Docs-only PRs: "n/a (human-written docs)" — gate 6 does not apply. -->

## Checklist

- [ ] One logical change (small PR)
- [ ] Every touched fit criterion has ≥1 test; ≥1 negative test per feature (code PRs)
- [ ] Offline suite green locally: `pytest test/offline -v`
- [ ] `docs/ai-use-log.yaml` updated in this PR (code/prompt PRs)
- [ ] Trace matrix row added/updated if requirements touched
- [ ] Safety-critical path (`src/contentguard/policy/**` or invariant-named files)?
      → ADR linked **and** architecture owner co-sign requested
