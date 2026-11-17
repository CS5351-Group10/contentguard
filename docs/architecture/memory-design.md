# Memory / State Design (D2.5)

> Status: Phase ② baseline (2026-11-16). Source: ADR-001 and `architecture-blueprint.md`
> (PR #15) plus the module interface contracts. Items marked **pending ratification**
> are design proposals tracked in the risk/debt registers — they are not claimed as
> accepted retention/access SLOs.
>
> **Source status (2026-11-17):** ADR-001 (PR #15) is merged; PR #11's registry is still a
> candidate, not merged. This design does not claim PR #11 acceptance and must be
> re-baselined if the registry changes. Full performance/cost benchmarks are deferred
> under decision #23.

## What state survives across sessions, interruptions, and versions

| State | What it is | Survives | Durable store |
|---|---|---|---|
| Case state | submission hash/id, case revision, status, pinned policy snapshot, effective flags | process restart, retries | SQLite `cases` (transactional) |
| Review queue | held/escalated items, queue status, assignment | restart | SQLite `review_queue` (transactional) |
| Decision audit | append-only record per committed decision: content hash, AI verdict (if any), policy rule/fallback id, final action, timestamps, actor ids | restart, versions | SQLite `audit` (append-only; written in the same transaction as case/queue) |
| Policy snapshots | immutable approved policy corpus: snapshot id, version, corpus digest, activation state | restart, versions | SQLite `policy_snapshot` + the approved policy corpus; owned by `policy` |
| Requirements registry | baselined requirements, lifecycle status, provenance | sessions, versions | git `docs/req/requirements.yaml` |
| Prompt versions | versioned runtime prompts (`prompt_vN.yaml`) | versions | git `prompts/` + prompt version pinned per case |
| Evaluation set/results | fixed labeled set and replay results | versions | git `test/eval/` + CI artifacts |
| AI-use log | session/operator/scope/interventions per change | versions | git `docs/ai-use-log.yaml` |
| Agent transcripts | annotated OpenCode sessions | submission | git `transcripts/` |
| Man-hours/contribution | per-phase hours | submission | git `docs/contribution-log.md` |

Resumable model summaries are **not** authoritative state: they live only inside a
bounded context envelope and never replace case/revision/decision records
(ADR-001 "Layered context, assembly, budgets and reinjection").

### Durable intake and recovery state

Intake bookkeeping is **not** a policy decision. It lets the system recover an accepted
request without inventing a disposition; only the policy commit writes consequential
case/queue/audit state.

| State | What it is | Durable store / owner | Write authority and recovery |
|---|---|---|---|
| Intake intent | intent id, authenticated actor, idempotency key, payload hash, received_at, status (`accepted`/`analyzing`/`terminal`/`failed`) | SQLite `intake_intent`; owned by `api` | `api` persists the intent before analysis; on restart, reconcile by intent id + payload hash; an abandoned intent never implies a decision |
| Worker reservation | intent id, worker id, lease expiry, attempt metadata | SQLite `intake_reservation`; owned by `api`/intake worker | one worker per intent; an expired lease is recovered explicitly; a recovered reservation never implies a finished decision |
| Replay record | actor + idempotency key, payload hash, case revision, last known status | SQLite `intake_replay` (or the intent row); owned by `api` | on lost acknowledgment, read durable state before retry; repeated delivery polls/reconciles and never invokes a second worker or commits twice |
| Policy snapshot activation | snapshot id/version/digest and activation state | SQLite `policy_snapshot`; owned by `policy` | activation only through a reviewed human change; cases pin the snapshot id/digest; no in-place rewrite; retention follows the audit/submission policy |

Recovery rule: on restart, `api` enumerates intents in `accepted`/`analyzing` with expired
reservations and resumes or reconciles them. A committed decision is authoritative; an
uncommitted intent is retried or reported failed/unconfirmed. It never manufactures a
hold, decision, or audit row. The intake `terminal` status means "no further recovery
needed"; it is **not** the case disposition — that lives in the policy-owned case/audit
records.

## Write and retrieval policy

- Writes to case, queue, and audit happen only through the policy commit operation:
  one SQLite transaction that first checks the expected case revision and the unique
  decision id. If any write fails, the whole transaction rolls back and the API reports
  failure/unconfirmed — never success (INV-4, REQ-QUA-002).
- `analysis` has no DB write credentials and returns advisory DTOs only; `api` and
  `escalation` do not mutate protected state outside the policy boundary (INV-1;
  `structural-constraints.md` rule 4).
- Retrieval: case/audit lookups by an authorized actor and case/audit id; review queue
  by moderator scope; prompt rollback by version pin; policy snapshot by immutable
  snapshot id/digest.
- Idempotency: replay identity = authenticated actor + `Idempotency-Key`, bound to the
  payload hash. A lost acknowledgment is reconciled by reading durable state before any
  retry (interface contracts, "State, retries and transactions").

## Ownership

| State | Owner |
|---|---|
| Case, queue, audit | policy boundary for the transaction; audit and escalation own their repositories behind transaction-enlisted ports |
| Requirements registry | human requirements owner; PM ratifies each baseline |
| Prompt versions / model configuration | human architecture owner + PM; any change passes gate 4 |
| Evaluation set/results | testing owner + CI |
| AI-use log | the operator of each agent session; PM audits |
| Transcripts | each member for their own session; PM checks sanitization and coverage |
| Contribution log | each member reports PR-natively; PM aggregates at phase close |

## Retention

- Course evidence — transcripts, audit records, evaluation results, registry, prompt
  versions — is retained to project submission (2026-11-25) and the 11/30 demo; no
  deletion before grading.
- Runtime case/audit retention values are a **planned** policy for REQ-SEC-004; the final
  access/retention matrix must be ratified by the PM and testing owner before claiming
  SEC-004 acceptance.
- The audit table is append-only: records are never updated; a correction is a new record
  linked to the original decision.

## Privacy

- Audit records store a content hash plus the decision evidence needed for traceability;
  raw submitted text is stored separately with restricted access and is not written to
  logs.
- No personal data beyond what moderation requires. Demo content is team-authored
  synthetic English/Chinese.
- The evaluation corpus is planned from Jigsaw 2018 (dataset CC0; underlying Wikipedia
  text CC BY-SA 3.0) plus team-authored synthetic cases, with COLD (Apache-2.0) only if
  PR #37 keeps it. Raw third-party text must stay out of `main` until the
  license/NOTICE and PII review lands (PR #37); `test/eval/README.md` records provenance
  and limitations.
- No API keys, tokens, or secrets in any persisted state: `.gitignore` blocks `.env*` and
  `token*`; transcripts are sanitized before commit (SEC-005, RSK-4).
- Provider usage records store token counts and model identity only, never credentials.
