# Module Interface Contracts — ADR-001 draft

> Status: PROPOSED — Shiyi authorized submitting this draft on 2026-11-16.
> ADR acceptance, non-author/PM review and numeric-limit ratification remain pending.
> AI-assisted documentation; no implementation or test-execution evidence is claimed.

Linked design: [ADR-001](adr/001-placeholder.md) and
[architecture blueprint](../../architecture-blueprint.md). Additional PR #11 IDs
are provisional until that baseline merges.


These are language-neutral design contracts, not source code or executable schemas.

### Common data

| Record | Required information / validation |
|---|---|
| Submission | Server actor ID, idempotency key, nonempty text; proposed max 16 KiB UTF-8; token fit checked separately |
| Case snapshot | Case ID, revision, content hash/reference, policy snapshot ID/digest, effective flags, current status |
| Retrieval result | Pinned snapshot, ordered unique clause IDs/text/digests, retrieval outcome; no action field |
| Advisory result | Role, verdict `allow/review/violate`, severity `low/medium/high`, rationale, validated citations, prompt/model versions, per-attempt usage |
| Analysis failure | `provider_unavailable/timeout/invalid_response/grounding_unavailable/context_overflow`; no invented verdict |
| Review request | Authenticated reviewer, case ID, expected revision, requested outcome, rationale, evidence tied to current snapshot |
| Policy decision | Decision ID, case revision, `approve/hold/reject/escalate`, deterministic rule/fallback ID, actor, pinned evidence |
| Commit result | `committed/pending_unconfirmed/failed/conflict`; committed result includes resolvable audit ID |

The 16 KiB intake ceiling is a proposed design value requiring ratification with
REQ-SEC-002, not an existing accepted requirement. Missing/unknown enum/type and
extra privileged action/tool fields invalidate an advisory response.
Across all inbound request DTOs, server-authenticated context is the sole source of
actor identity and privileges. Reject caller-supplied actor/role/privilege claims;
server-enriched internal records may contain these fields. Every state-changing
review and policy commit binds expected case revision and pinned policy snapshot;
mismatches yield conflict with no state change.

### Operations and owners

| Owner / operation | Input → output | Failure/side-effect boundary |
|---|---|---|
| API: submit | Submission → committed result or accurate incomplete state | Invalid input: no model call; key+payload mismatch: conflict |
| Analysis: retrieve | Content + pinned policy snapshot → retrieval result | No usable/provenance-valid match: typed failure; no writes |
| Analysis: analyze | Case + retrieved clauses + role → advisory result/failure | No DB mutation or enforcement; bounded context/deadline |
| Policy: evaluate | Immutable case + validated advisory/failure + optional review → proposed decision | Pure deterministic outcome/reason from full input/state tuple |
| Policy: commit | Proposed decision + expected revision + replay identity → commit result | Atomic state+queue+audit; rollback on any failure |
| Escalation: enqueue (internal) | Case + transaction → queue entry | Idempotent per logical case/revision; commit owned by policy |
| Audit: append (internal) | Decision + transaction → audit ID | Unique logical decision ID; no committed status before transaction commit |
| API: review | Authenticated review + expected revision → commit result | Unauthorized/stale review cannot change state |
| API: lookup | Authorized actor + case/audit ID → filtered record | Unauthorized denied; immutable historical policy references |

Provider adapter exposes only analysis invocation, never execution tools. Retrieval
adapter reads approved local snapshots only; model output cannot choose arbitrary
filesystem paths, URLs, policy revisions or SQL queries.

### REST outline

| Route | Purpose | Principal outcomes |
|---|---|---|
| POST `/v1/submissions` | Submit text with `Idempotency-Key` | 201 committed new triage; 200 reconciled result; 202 durably pending with no final outcome/audit claim; 409 payload conflict; 422 invalid input; 503 definitive persistence failure |
| GET `/v1/cases/{id}` | Authorized case/reconciliation lookup | 200 known state; 403 denied; 404 unknown |
| GET `/v1/review-queue` | Moderator queue view | 200 list; 403 denied |
| POST `/v1/cases/{id}/reviews` | Request human-reviewed transition with expected revision | 200 committed; 403 unauthorized; 409 stale/conflict; 422 mandatory-rule violation; 503 persistence failure |
| GET `/v1/audits/{id}` | Authorized immutable decision evidence | 200 record; 403 denied; 404 unknown |

Only return 202 when a durable intake intent exists and can be recovered. A queued
hold/escalate can be a committed triage result even though final disposition is not
complete. Never use a success status to imply confirmed queue placement when the
handoff is uncertain. Internal requests carry authenticated principals; client JSON
cannot self-assert moderator privileges.
Response categories are mutually exclusive: committed (200/201, resolvable audit
ID and outcome); durably pending/unconfirmed (202, intent ID and reconciliation
link, no final outcome or committed audit claim); rejected/failed (4xx/503, no
success claim). If reconciliation cannot prove a durable intent, report unavailable
with the replay key rather than manufacturing a 202 recovery guarantee.

### State, retries and transactions

States: accepted intent → analyzing → hold/escalate/approve/reject. Hold/escalate may
transition to a permitted final disposition only through current authorized human
review and policy evaluation. Final states remain historical; any future appeal
creates a linked successor, not a rewrite. State changes increment revision.

Key replay identity by authenticated actor + idempotency key; bind it to payload hash.
Persist intent uniquely before analysis; reserve one worker per intent, so duplicate
delivery polls/reconciles rather than invoking another worker or committing twice.
On restart an abandoned reservation is recovered explicitly; it cannot imply a
finished decision. A policy commit checks expected revision and unique decision ID,
then writes case, queue and audit in a single DB transaction. Repeated commit returns
the same result; opposing commits on one revision yield at most one winner.
Policy owns authorization and the commit operation; audit and escalation own their
respective repositories and expose transaction-enlisted ports. They neither commit
independently nor expose protected mutation routes to API/analysis. This is a
proposed port contract, pending governance-owner reconciliation with the existing
dependency rules before implementation.
No network side effects are allowed inside that transaction or in the MVP effect
model. If a response is lost, read durable state before taking further action.

### Session-3 handoff

After approval, Shiyi's OpenCode session 3 implements only the approved analysis
subcomponents: retrieval interface, policy corpus format, context assembly,
compaction/reinjection and bounded provider adapter. Coordinate with Mei's policy
kernel interfaces and Buna's approved negative tests. Do not create policy module
implementation or change CI in Shiyi's slice. Session transcript and ai-use-log must
link the approved plan, test issue and actual implementation PR.
