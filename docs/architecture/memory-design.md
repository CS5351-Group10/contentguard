# Memory / State Design (D2.5)

> **Status: DRAFT skeleton** — filled at the W12 architecture session.

## What state survives across sessions, interruptions, and versions

TBD — decision audit records (append-only), requirements registry, prompt versions,
evaluation set + results, agent session transcripts.

## Write and retrieval policy

TBD — who writes each state type (component vs human vs agent), when, and how it is
retrieved (e.g., audit lookups by content hash; prompt rollback by version pin).

## Ownership

TBD — owning component per state type (audit subsystem owns audit records; humans own
the registry; CI owns gate reports).

## Retention

TBD — retention periods per state type, aligned with course evidence requirements
(transcripts and audit records are submission evidence: retain to project end).

## Privacy

TBD — no personal data in audit records beyond hashed content; no API keys/secrets in
any persisted state (see `.gitignore`); transcripts sanitized before commit.
