# Architecture Blueprint (D2.1 / D2.2)

> Status: PROPOSED — Shiyi authorized submitting this draft on 2026-11-16.
> ADR acceptance, non-author/PM review and numeric-limit ratification remain pending.
> AI-assisted documentation; no implementation or test-execution evidence is claimed.

## Baseline and scope


Main inspected: `7fb4a924f085a32b3f6ce15b561a26acb9642cf4`.
Main has REQ-INV-001..005 and REQ-FUN-001..003. PR #11 inspected at
`6e45418ee146a04de9d164fc7ef5c8265abd9463` proposes 31 requirements and remains
unmerged. References to its additional IDs below are provisional mappings, not
claims that the registry is baselined.

PM's latest PR #11 addendum supersedes the proposed registry's old wording:
retrieval (REQ-FUN-005) is must; appeal (REQ-FUN-006) is wont for MVP; numeric NFR
thresholds must be ratified. This proposal reserves appeal support but implements
no appeal endpoint. Bulk import, analytics and multilingual support stay deferred.



### Scope and drivers

MVP accepts text, retrieves approved policy clauses, obtains advisory LLM analysis,
applies deterministic rules, durably queues held/escalated cases and persists an
audit record before reporting a committed result. Human decisions traverse the
same policy boundary. The five invariants dominate convenience, latency and cost.
All implementation follows approved ADR-001, approved test-plan issues and recorded
OpenCode sessions. This proposal defines design responsibilities, not implemented
capabilities.

### Components and dependencies

Use a modular monolith with a REST boundary and one transactional SQLite database
for the course demo. One deployment and local transactions reduce failure modes in
the short build window. Provider calls run outside database transactions. No
external content platform is mutated in MVP; dispositions affect local case state.
Adding external effects requires an outbox/reconciliation ADR before enabling them.

| Existing architectural element | Responsibility | Must not do |
|---|---|---|
| `api` | Validate/authenticate, deduplicate requests, coordinate analysis then policy, map responses | Decide a moderation outcome or write protected case state |
| `analysis` | Retrieve approved clauses, assemble bounded context, call/validate advisory LLM | Hold DB write credentials, call enforcement APIs, approve policy revisions |
| `policy` | Evaluate mandatory rules, authorize transitions, coordinate atomic commit | Delegate authority to model output or accept client-supplied reviewer identity |
| `escalation` | Durable queue repository and authorized review reads; mutations enlisted by policy | Dispose content or let queue status bypass the policy gate |
| `audit` | Append-only records and transaction-bound persistence | Assert committed outcome for an incomplete transaction |

Logical dependency: API → analysis for advisory data; API → policy for every
transition; policy → escalation/audit transaction interfaces. Analysis never
imports policy internals. Retrieval/context/provider adapters are subcomponents
of `analysis`, not new top-level modules. A shared contract belongs to its owning
element; adapters depend on read-only DTOs, not protected mutation internals.
The package owner and governance owner reconcile AGENTS.md's placeholder dependency
arrow with the proposed arrangement before implementation; this proposal does not
silently change that governance file.

### Authority and processing

1. API validates authenticated actor, text and idempotency key. Invalid submissions
   produce controlled errors and zero model calls. A durable intake intent identifies
   the logical request before provider work begins, without claiming a decision.
2. Pin approved policy snapshot, prompt version, model configuration and feature
   flags for the case. Run a deterministic high-severity pre-filter.
3. Analysis retrieves only from that snapshot, builds context and attempts initial
   LLM analysis. The caller treats missing/invalid results as typed failures.
4. Policy selects outcome/reason. AI failure or invalid grounding produces hold;
   any high-severity signal produces escalate. Neither can become an automatic
   final disposition. A missing durable queue is failure/unconfirmed, never success.
5. One DB transaction checks expected case revision, writes state and any queue entry,
   appends exactly one committed decision audit row, and commits all or none.
6. API reports success only after commit. A lost acknowledgment is reconciled by
   idempotency lookup. Conflicting requests on one revision cannot both commit.

Human review requests are authenticated evidence, not enforcement authority.
Require reviewer ID from server authentication, current case revision, nonempty
review rationale and reference to the current policy snapshot. Any change to text,
policy snapshot or severity assessment invalidates prior review evidence. An
authorized, current review permits policy to reconsider a high-severity case;
mandatory rules remain binding even after human review.

### Three LLM roles

| Role | MVP activation | Contract |
|---|---|---|
| Initial review | Required live analysis path | Verdict/severity/rationale/citations; advisory only |
| Reconsideration | Optional flag, moderator-requested on queued case | Same schema plus original decision reference; disagreement stays queued |
| Appeal review | Extension seam only; disabled | Future request references immutable original decision and follows policy + human review |

Do not call three models for every item. Initial review is the default single call.
Reconsideration cannot auto-release a case or substitute for substantive human
review. Appeal adoption requires a recorded scope change, tests and review.

### Retrieval and context

Approved policy snapshot is immutable and contains unique clause IDs, revision,
category, text, severity guidance, provenance and content digest. A case pins its
snapshot. Baseline retrieval uses a deterministic lexical ranking over the small
local corpus, with stable ID tie-breaks; a vector service is deferred. This keeps
the retrieval contract independent of a future ranking implementation.

Only approved, matching snapshot clauses enter policy context. Submitted text and
retrieved prose are untrusted data, never instructions or executable rules. Validate
citations against the exact clause IDs supplied to the model and the pinned digest.
Unknown ID, stale snapshot, conflicting authoritative metadata, missing corpus,
retriever error or no usable match produces `GroundingUnavailable`; policy holds
for human review. Retrieval must be attempted on the normal MVP path. The demo
control for an isolated baseline cannot switch production retrieval off and proceed
as if grounding succeeded.

### Layered context and assembly

Layers, in priority order: (1) identity and output schema; (2) standing safety and
authority constraints; (3) retrieved approved policy clauses with provenance;
(4) current submitted content/history as delimited data; (5) resumable state with
case revision, original decision and prior summaries; (6) current role/task.
Persistent authoritative state always comes from storage, never a model summary.

Pipeline: load pinned revisions → retrieve → validate provenance → deduplicate
by clause ID/digest → rank → allocate budgets → compact lower-priority material →
reinject immutable safety capsule → assemble explicit data delimiters → recount
complete input → dispatch → validate schema/citations → return advisory result.
Prompt composition does not grant authority; deterministic validation still applies
to schema-valid malicious recommendations.

Proposed numeric design settings, subject to requirements/testing owner and PM
ratification (not approved SLOs):

| Setting | Proposed value | Meaning |
|---|---:|---|
| Total invocation context envelope | 8,192 tokens | 6,144 input + 1,024 maximum output + 1,024 reserve |
| Input compaction trigger | >4,608 tokens | 75% of input hard cap; recount after reinjection |
| Input hard cap | 6,144 tokens | Overflow after compaction means no provider call; hold |
| Safety/schema allocation | 1,024 tokens | Immutable and never truncated; includes task envelope |
| Approved policy allocation | 2,048 tokens | At most 5 complete clauses, no mid-clause truncation |
| Content/history allocation | 2,048 tokens | Preserve original evidence separately; no silent content loss |
| Resumable state allocation | 512 tokens | Structured IDs/revisions + bounded summary |
| Delimiter/assembly allowance | 512 tokens | Included in total input count |
| Per-invocation deadline | 20 seconds | No automatic model retries in MVP |
| Default invocation count | 1 | At most one extra explicit reconsideration invocation |

Use the selected model's tokenizer and count the actual serialized request. Provider
context limits must accommodate this envelope or the adapter fails configuration
validation. Record measured provider usage separately from local estimates, including
unknown usage for failed calls. Limits are ceilings, not per-layer padding targets.

Compaction first removes duplicate/lowest-ranked clauses (whole clauses), then
nonessential historical turns. Use deterministic structured summaries of prior
state in MVP; a new LLM summarizer would need its own token/cost/evaluation contract.
Never summarize away high-severity evidence, current case revision or the current
content needed for a reliable verdict. If those cannot fit, hold rather than issue
a partial-content verdict. After compaction reconstruct the safety capsule from
trusted versioned constants: advisory-only authority, untrusted-data boundary,
mandatory human review, failure fallback, required schema and citation rules.
Reinsert it as instructions, not inside the untrusted summary, then recount and
validate all required constraints before dispatch.

### API and observability

REST/JSON over a single process: submit text, read case/audit, list review queue and
submit review requests. No appeal endpoint in MVP. Responses distinguish committed,
pending/unconfirmed and rejected intake; only committed triage has a resolvable
decision audit ID. See [interface contracts](docs/architecture/interface-contracts.md).

Record correlation/case/decision IDs, outcome and reason, case revision, policy and
prompt/model versions, selected clause IDs/digests, effective flags, fallback code,
latency and per-attempt token usage. Never log credentials. Hash content in audit;
store necessary raw review content separately with restricted access. Retain course
evidence to project submission; production retention/access values need human
ratification before claiming REQ-SEC-004 acceptance. Track queue depth, unconfirmed
handoffs, audit failures, grounding failures, schema failures and cap/deadline events.


### State, ownership and change policy

The policy boundary owns transition authorization; audit and escalation own their
transaction-enlisted repositories. See [interface contracts](docs/architecture/interface-contracts.md)
for retry identity, revision checks and atomic commit rules. Policy snapshots, prompt
versions and prior decisions remain immutable references across requests; resumable
model summaries cannot replace authoritative case state.

Architecture and scope changes require a reviewed ADR revision. Requirements remain
owned by the registry and must be reconciled after PR #11; update the authoritative
trace matrix with the requirements owner once the baseline lands. No component may
be implemented until ADR-001 is accepted and governance dependency references are
aligned. Each implementation slice needs approved tests, human plan approval and
OpenCode evidence. See [ADR-001](docs/architecture/adr/001-placeholder.md).
