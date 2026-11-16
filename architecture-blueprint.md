# Architecture Blueprint (D2.1 / D2.2)

> Status: APPROVED (2026-11-16) — PM LIU Jianwei approved this D2.1/D2.2 blueprint
> together with ADR-001; requirements/testing co-signs and the final PR #11 baseline
> remain pending.
> AI-assisted documentation; no implementation or test-execution evidence is claimed.

## Baseline and scope


Main inspected: `7fb4a924f085a32b3f6ce15b561a26acb9642cf4`.
Main has REQ-INV-001..005 and REQ-FUN-001..003. PR #11 inspected at
`b0dd79c1b5a3ec23c0967ff414e94584e14d4907` proposes 31 requirements and remains
unmerged. References to its additional IDs below are provisional mappings, not
claims that the registry is baselined.

PM's latest PR #11 addendum supersedes the proposed registry's old wording:
retrieval (REQ-FUN-005) is must; appeal (REQ-FUN-006) is wont for MVP; numeric NFR
thresholds must be ratified. This proposal reserves appeal support but implements
no appeal endpoint. Bulk import, analytics and multilingual support stay deferred.

The [PM working-scope decision #23](https://github.com/CS5351-Group10/contentguard/issues/23#issuecomment-6911253409)
on 2026-11-16 keeps all Must requirements; FUN-007 demo comparison is conditional
on S5 capacity, SEC-004 and QUA-002/003 are partial, and PER-001/COS-001 are log-only
for this build (no full benchmark commitment). Numerical criteria remain provisional
future acceptance targets, not implemented/verified claims or an implicit registry
edit. Record later scope/priority changes explicitly with the requirements owner.
Objections to that working scope remain open until 2026-11-17 09:00 HKT.



### Scope and drivers

MVP accepts text, retrieves approved policy clauses, obtains advisory LLM analysis,
applies deterministic rules, durably queues held/escalated cases and persists an
audit record before reporting a committed result. Human decisions traverse the
same policy boundary. The five invariants dominate convenience, latency and cost.
Implementation must not begin until ADR-001 is accepted and test-plan issues are
approved; subsequent implementation uses recorded OpenCode sessions. This proposal defines design responsibilities, not implemented
capabilities.

### System boundaries and architectural drivers

Actors are authenticated submitters, authorized moderators, and operators approving
policy snapshots/configuration. REST accepts text, replay identity and review requests;
responses expose confirmed triage or truthful incomplete states, plus authorized
case/audit lookups. CI is a separate development/verification boundary, not a runtime decision-maker.
The external hosted LLM receives bounded submitted text and
approved policy context and returns untrusted advisory data. The local policy corpus
and transactional SQLite store are inside the application boundary. No external
forum writes, bans or delete tools are enabled. Provider credentials stay outside
requests, persisted evidence and logs.

Primary drivers are the five invariants (REQ-INV-001..005), required grounding
(REQ-FUN-005 in PR #11), repeatable policy outcomes, atomic durable handoff/audit,
offline verification, and the course build window. Latency/cost/quality thresholds
are provisional benchmark targets; their status does not weaken safety boundaries.

### Agent workflow

OpenCode first reads [AGENTS.md](AGENTS.md) and its required documents, then follows
[Prompt.md](Prompt.md): confirm context and REQ/INV IDs → propose traceable file,
interface and test plan → STOP for explicit human execution-plan approval → build
in small approved steps → verify → hand off a PR for human review. Code work also
requires a pre-approved test-plan issue; runtime modules require an accepted ADR
and reconciled governance dependencies. A changed plan returns to human approval.
Tests precede the implementation they verify. Humans retain architecture/requirements
approval, PR review memos, real transcript annotations and actual-hours reporting.

The plan role is read-only; the code role works only in approved implementation
paths; the verification role writes only permitted reports. In this project,
`src/`, `test/`, `prompts/`, `scripts/` and CI workflows are generated/refined through
OpenCode sessions. Docs-only architecture proposals do not authorize implementation.
Each covered code/prompt/workflow PR includes its AI-use-log entry; session evidence
is sanitized and annotated by the human operator. Non-author review and required CI
checks precede merge. Existing governance restrictions remain binding until changed
through the separately reviewed human documentation process.

### Permissions

Use the authoritative [permission model](docs/architecture/permission-model.md)
for the complete role/path matrix: default deny, explicit readable/modifiable paths,
and no agent access to secrets or frozen files. `docs/req/**` and
`docs/architecture/**` are human-owned proposals requiring human approval.
Analysis has no enforcement API or protected-write authority; only policy authorizes
consequential state transitions. Safety-critical changes require an approved ADR
and explicit human approval. Tool access is bounded by the
[MCP tool manifest](docs/code-governance/mcp-tool-manifest.md).

### Verification strategy

Follow [verification constraints](docs/code-governance/verification-constraints.md):

- Structural tier: one-to-one module mapping, dependency/permission boundaries,
  lint and type checks. Enforcement call-graph fitness checks are planned TD-4,
  not claimed as implemented protection.
- Regression tier: every change runs all previous deterministic suites with zero
  regressions (`pytest test/offline -v`); live API tests remain separate. Every
  touched fit criterion needs a test and each invariant a violation-detecting
  negative test; test docstrings cite REQ/INV IDs.
- Behavioral tier: prompt/model/behavior-affecting configuration changes require
  revision-bound fixed-corpus semantic replay, slice metrics and zero safety
  escapes. Gate 4's current skeleton is not evidence of strict enforcement;
  the governance/testing owners must activate and prove blocking behavior.

The six gates cover test approval, static analysis, registry schema, semantic replay,
offline regression, and AI-use logging. Report failing/missing evidence honestly;
passing static checks cannot substitute for live analysis or semantic evidence.

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
references with the proposed arrangement before implementation; this proposal does not
silently change that governance file. The current conflicting arrow is explicit
in structural-constraints.md rule 5; PM review also flags AGENTS.md references.
PM owns a separate human docs PR aligning these after #15; implementation waits
for that reconciliation.

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
co-sign (not measured SLO compliance). PM provisionally ratified the envelope,
input cap, compaction trigger and 20-second hard per-call cap in the
[2026-11-16 review](https://github.com/CS5351-Group10/contentguard/pull/15#pullrequestreview-5916924512);
requirements-owner and Testing Lead co-signs remain pending:

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
| Per-invocation hard deadline | 20 seconds | Absolute ceiling, not the <=10-second end-to-end p95 target; no automatic model retries |
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

### Provisional latency, usage and evaluation alignment

PR #11 head `b0dd79c` proposes REQ-PER-001 p50 <=5,000 ms, p95 <=10,000 ms,
and >=95% confirmed triage/durable hold within 10,000 ms, with two independent
runs of >=100 accepted requests each at concurrency 1. Record timing from accepted
intake through the observable response, including persistence. Include every accepted
request and separate normal, held/fallback, timeout, failed and unconfirmed groups.
A fast 202 response is not confirmed successful triage. No measured pass is claimed.

The provisionally PM-ratified 20-second provider cap is an absolute single-call
ceiling, not this end-to-end percentile target. Proposed coordination setting:
cut off analysis 8 seconds after accepted intake, reserve 2 seconds for policy,
queue/audit and response, and limit a dispatched call to the lesser of 20 seconds
and the remaining analysis window. This earlier cutoff is NOT ratified by the
20-second-cap approval; requirements/testing owners and PM must co-sign and measure
it before implementation. On expiry, return a typed timeout for policy-owned hold;
if high severity is known, escalate. Cancel provider work best-effort and fence late
results using attempt identity/current case revision. Never report queue success
without atomic commit. A slow or uncertain write yields truthful unconfirmed/failure
with durable-intent reconciliation, even when that misses the latency target.

REQ-COS-001's provisional median <=2,500 and p95 <=4,000 combined input/output tokens
are measured logical-request usage targets including retries, not context capacities.
The 8,192 envelope includes 1,024 unused reserve, not billed usage; a valid invocation
can still exceed the 4,000 statistical target. COS-001 remains provisional/not-claimed
until measured and co-signed. Prefer compacting toward <=2,976 serialized input tokens
with at most 1,024 output, without removing safety constraints or necessary evidence.
Overflow beyond the hard input cap means no provider call and safe hold.

The aggregate hard token budget per logical request is still OPEN in PR #11.
Do not call 8,192 that budget. Default one attempt, no automatic retry, satisfies
the proposed ceiling of at most two attempts. Enabling retries needs an approved
aggregate budget, unknown-usage policy and remaining-time checks. Record provider
usage per attempt, including explicit unknown after timeout/cancellation; remote
billing may continue after local cancellation. A separate explicit moderator
reconsideration is linked to the case; account for its operation and case totals,
without bypassing any subsequently approved logical-request budget.

Proposed evidence follows PR #11: >=100 fully observed logical requests for token
percentiles; >=95% complete usage on the designated successful-request benchmark;
report failed/unknown attempts separately, never as zero or silently excluded.
For REQ-QUA-003 use >=100 pinned labeled cases, agreement >=85%, >=20 high-severity
positives with recall >=90%; per-category confusion matrices for >=10 examples,
otherwise insufficient sample size. Publish slice FP/FN numerators/denominators,
empty denominators N/A, and account for 100% of cases. Zero consequential boundary
bypasses is required independently of average quality. REQ-FUN-005 plans >=100
retrieval fixtures (>=20 matches, >=20 error/tampering cases), 100% valid accepted
citations and safe failure behavior. These sample sizes/thresholds still require
Testing Lead/PM ratification and are planned evidence, not test results.

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
OpenCode evidence. See [ADR-001](docs/architecture/adr/001-grounded-advisory-transactional-policy.md).
