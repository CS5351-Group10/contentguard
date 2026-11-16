# ADR-001 — Grounded advisory analysis with transactional policy authority

> Status: PROPOSED — Shiyi authorized submitting this draft on 2026-11-16.
> ADR acceptance, non-author/PM review and numeric-limit ratification remain pending.
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



Title: Modular monolith with grounded advisory analysis and transactional policy authority.
Status: PROPOSED. Date: 2026-11-16. Owner: Shiyi LI. Human approval: pending.

### Architectural design process (ADD)

This records the proposal/review sequence on 2026-11-16, not an approved or measured
architecture. Inputs are REQ-INV-001..005/FUN-001..003 on inspected main, the 31-ID
candidate registry at PR #11 `b0dd79c`, PM scope ratification (grounding Must,
appeal Won't), governance constraints and the course build window.

1. Identify architecturally significant requirements: policy authority, fail-safe
   handoff, mandatory human review, atomic audit/state, grounded advisory analysis,
   offline testability and bounded provider cost/time.
2. Generate candidates: modular monolith, split services, rules-only with optional
   LLM. The alternatives and driver weights are documented in the table below.
3. Evaluate by weighted design judgment (35/25/25/15); C1=5.00, C2=3.25, C3=4.00.
   These scores are rationale, not experiment results or independently approved values.
4. Propose C1 and document components/contracts/context assembly in the blueprint,
   this ADR and interface contracts. PR #15 initial commit `49681d8` preserves the
   submitted proposal. OpenCode planning/review session
   `ses_e1dd9f5fbffe6pe5Vn1eXoEQSK` is referenced in that PR; this is planning,
   not completed implementation or human annotations.
5. Revise against the [PM's 2026-11-16 review](https://github.com/CS5351-Group10/contentguard/pull/15#pullrequestreview-5916924512)
   and latest PR #11 criteria. Record provisional numeric ratification below,
   retain pending co-signs, and submit for fresh review. No accepted decision or
   architecture-approval date is asserted before the actual human verdict.

PR #16 separately supplies D2.5 memory design and D2.8 evaluation table, plus
runtime policy, risks and option/evaluation logs. Both support artifacts must merge
before Phase ② exit; they are not claimed as part of #15. Later benchmark/fault
results may reopen this decision, with dated evidence and a reviewed revision.

### Ratification and outstanding dependencies

PM provisionally ratified the 8,192 context envelope, 6,144 input cap, 4,608
compaction trigger and 20-second hard single-call cap in the review linked above.
Requirements-owner and Testing Lead co-signs remain pending (Buna onboarding).
Twenty seconds is not REQ-PER-001's <=10-second end-to-end p95. The blueprint's
proposed 8-second analysis cutoff is a separate, unratified coordination setting;
its late-result fencing and durable-hold semantics must be co-signed and measured.
REQ-COS-001's <=4,000 combined-token target is provisional/not-claimed until
measured; the context envelope is not a logical-request aggregate cap. See the
[blueprint alignment section](../../../architecture-blueprint.md#provisional-latency-usage-and-evaluation-alignment).

PM owns the separate human docs change reconciling governance dependency arrows
(in particular structural-constraints.md rule 5 and AGENTS.md references) after
#15 merges. This PR does not alter those governance files. Keep this ADR PROPOSED
until required fixes, CI and human ratifications/review actually complete; only then
record APPROVED with the actual reviewer/date. No implementation is authorized now.

### Decision and alternatives

Propose the [architecture blueprint](../../../architecture-blueprint.md) and
[interface contracts](../interface-contracts.md). The deterministic policy module owns
all consequential transitions; RAG is required; LLM output remains advisory.

Scores are design judgments from 1 (weak) to 5 (strong), not benchmark evidence.

| Driver / weight | Modular monolith | Split services | Rules-only + optional LLM |
|---|---:|---:|---:|
| Safety and atomic persistence / 35% | 5 | 3 | 5 |
| Grounded AI scope fit / 25% | 5 | 5 | 1 |
| Build-window feasibility / 25% | 5 | 2 | 5 |
| Offline verification / 15% | 5 | 3 | 5 |
| Weighted score | 5.00 | 3.25 | 4.00 |

Rules-only is rejected despite its low complexity because required live advisory
analysis and RAG would be missing. Split services offer scaling/isolation but add
distributed audit/queue consistency work. Reconsider split services if multi-process
throughput or independent deployment becomes a measured requirement; reconsider
retrieval ranking only if the frozen evaluation set demonstrates insufficient recall.

### Feature flags and demo comparison

`analysis.reconsideration_enabled` defaults false; enabling permits an extra advisory
step only on a queued case. Pin and audit effective flags when starting each request.
The closed flag allowlist contains only `analysis.reconsideration_enabled` in MVP;
adding a flag requires architecture review. Flag updates are authenticated operator
configuration, never accepted from submitted content. Fail unknown/invalid flags closed. No flag disables policy mediation,
high-severity review, audit persistence, schema validation or required grounding.
Mandatory RAG and semantic CI gate 4 are non-toggleable and non-bypassable in any
environment claiming MVP compliance. Runtime flags and configuration cannot waive
REQ-INV-005; prompt/model/behavior-affecting configuration must pass the semantic
release gate with evidence bound to the effective configuration and revision.

Demo baseline/enhanced comparison uses the same fixed input, policy/model versions
and recorded flag configuration. Baseline runs required initial RAG review;
enhanced additionally enables reconsideration. Compare advice/citations/token usage
and final policy outcome. Both preserve invariants. An ungrounded/unsafe educational
comparison is a separate read-only simulation with no protected state writes, never
a runtime bypass. Effective configuration changes affecting model behavior require
semantic evaluation; flag settings must be part of replay identity.

### Consequences, failure paths and verification

Benefits: clear ownership, local atomic commit and deterministic offline fault tests.
Costs: SQLite single-writer limitations and conservative holds when grounding is
unavailable. No production scaling or measured quality/latency/token compliance is claimed. An explicit
revision is required before adding external effects, appeals or an LLM summarizer.

Fallback contract: retrieval/provenance/context overflow/schema/provider failure →
hold with durable queue and fallback identifier; high severity → escalate; policy
error → no final disposition; audit/queue commit failure → roll back, report failure
or unconfirmed accurately; lost response → reconcile by key before retry; semantic
gate failure → block merge. Existing R-1..R-7 remain applicable; retrieval and token
rows are proposed separately in PR #16; they require review and remain planned
until implementation/evidence lands.

Acceptance tests to plan with Buna (not implemented or executed evidence): all five
invariants including negative bypasses; injection + forged/stale citations; exact
token boundary/overflow/reinjection; retrieval no-match/error; provider timeout;
duplicate request/lost acknowledgment; audit/queue rollback; competing stale review
requests; flag comparison preserving all invariants. A real provider test is separate
from deterministic offline tests and records the actual model/config version.

Approval conditions: PR #11 baseline reconciled; requirements/testing owners ratify
limits and fallback contract; PM/non-author approval; CI green; governance owner
aligns module contract references. No implementation before accepted ADR, test-plan
approval and human-approved OpenCode execution plan. This document does not itself
grant any of those approvals.

Reopen ADR if retrieval cannot satisfy the build window, numeric limits fail measured
workload, appeal is adopted, external enforcement is added, database contention is
measured, or the model context limit changes.


### Layered context, assembly, budgets and reinjection


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
