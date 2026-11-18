# ContentGuard — Community Content Policy v1.0

**Document ID:** CG-POL-001  
**Version:** 1.0  
**Status:** Draft  
**Project:** ContentGuard  
**Document Type:** Community Moderation Policy  
**Owner:** Requirements Engineering Team  
**Created:** 2026-11-17  
**Related Requirements:** REQ-INV-001–005, REQ-FUN-001–007, REQ-SEC-001–005, REQ-QUA-001–003

---

# 1. Purpose and Scope

## 1.1 Purpose

This document defines the community content standards and moderation rules used by ContentGuard.

Its purpose is to establish a consistent, transparent, and testable policy framework for evaluating user-generated content.

ContentGuard uses AI-assisted content analysis together with a deterministic policy engine and human moderation workflow.

The policy provides the reference criteria for:

- Identifying potentially harmful or inappropriate content.
- Categorizing policy violations.
- Assessing violation severity.
- Recommending appropriate moderation actions.
- Routing uncertain and high-risk cases to human moderators.
- Recording moderation decisions for audit and accountability.
- Supporting consistent evaluation of moderation accuracy.

The policy is designed to balance community safety, freedom of expression, contextual interpretation, and procedural fairness.

## 1.2 Scope

This policy applies to user-generated content submitted to the ContentGuard platform, including:

- Text posts and comments.
- Replies and discussion messages.
- User-submitted descriptions and other textual material.
- Content edited or resubmitted after an earlier moderation decision.

The initial MVP focuses on text-based content moderation.

Image, audio, video, and other multimodal content are outside the initial policy implementation scope unless explicitly supported by a future extension.

## 1.3 Policy Principles

ContentGuard adopts the following principles:

1. **Safety first:** Content presenting credible threats or serious harm must receive appropriate protective handling.
2. **Consistent enforcement:** Similar violations should receive comparable treatment under the same policy conditions.
3. **Context matters:** Decisions should consider context, intent, target, and surrounding discussion rather than relying exclusively on individual keywords.
4. **Proportionate response:** Moderation actions should be proportionate to the severity and certainty of the violation.
5. **Human oversight:** AI analysis is advisory and must not independently execute consequential enforcement actions.
6. **Fail-safe handling:** AI failures, invalid responses, and uncertain high-risk cases must not result in automatic approval or rejection.
7. **Traceability:** Every consequential moderation decision must have attributable evidence and an audit record.
8. **Fair treatment:** Users should not be penalized solely because of language, identity, viewpoint, or an isolated ambiguous expression.

---

# 2. Content Classification Framework

ContentGuard classifies potentially problematic content into seven primary policy categories.

## 2.1 Harassment and Personal Attacks

**Policy ID: POL-001**

Definition:

Content that targets an individual or group through abusive, humiliating, intimidating, or persistently hostile communication.

Examples:

- Direct personal insults intended to degrade another user.
- Repeated targeted harassment.
- Encouraging others to intimidate or attack a particular user.
- Publishing humiliating personal information to facilitate harassment.

Severity guidance:

- Low: Isolated rude or disrespectful language without sustained targeting.
- Medium: Direct personal attacks or repeated hostile remarks.
- High: Sustained targeted harassment, coordinated abuse, or credible intimidation.

Enforcement guidance:

- Low: Allow or issue a warning depending on context.
- Medium: Hide or remove the offending content and consider a warning.
- High: Escalate to human review and consider account restrictions.

Context exceptions:

- Criticism of an idea, public decision, or argument is not automatically harassment.
- Quoting abusive language to report or discuss an incident is not automatically a violation.
- Satire and consensual banter require contextual assessment.

## 2.2 Hate Speech and Discriminatory Abuse

**Policy ID: POL-002**

Definition:

Content that attacks, dehumanizes, or promotes discrimination or hostility against individuals or groups based on protected characteristics.

Examples:

- Dehumanizing statements directed at a protected group.
- Calls for exclusion or discrimination based on identity.
- Slurs used to attack or intimidate a protected group.
- Advocacy of violence against people because of protected characteristics.

Severity guidance:

- Low: Ambiguous or potentially discriminatory language requiring contextual assessment.
- Medium: Explicit discriminatory insults or degrading statements.
- High: Dehumanization, direct threats, or encouragement of violence against protected groups.

Enforcement guidance:

- Low: Contextual assessment or human review.
- Medium: Remove or restrict the content.
- High: Immediate escalation to human review and protective action where necessary.

Context exceptions:

- Educational discussions of discrimination.
- News reporting and historical analysis.
- Counterspeech opposing hateful statements.
- Quotation for documentation or criticism.

Such exceptions do not automatically make content acceptable; context and purpose must be considered.

## 2.3 Threats and Incitement to Violence

**Policy ID: POL-003**

Definition:

Content expressing an intention to cause physical harm or encouraging others to commit violence.

Examples:

- Direct threats against an identifiable person.
- Encouragement of physical attacks.
- Instructions or encouragement intended to facilitate imminent violence.
- Threats involving identifiable targets, locations, or planned actions.

Severity guidance:

- Low: Ambiguous violent language without an identifiable threat.
- Medium: Explicit violent statements with unclear intent or credibility.
- High: Credible threats, specific targets, or apparent intent to carry out physical harm.

Enforcement guidance:

- Low: Contextual assessment.
- Medium: Escalate for human review.
- High: Prioritize immediate human review and restrict harmful content where authorized.

Important distinction:

Fictional violence, metaphorical language, gaming discussions, and news reporting should not automatically be treated as real-world threats.

## 2.4 Spam and Manipulative Content

**Policy ID: POL-004**

Definition:

Content intended to disrupt community discussion, manipulate engagement, or distribute repetitive and unwanted material.

Examples:

- Repeated identical posts.
- Unsolicited commercial promotions.
- Automated promotional messages.
- Deceptive links intended to manipulate users.
- Coordinated repetitive posting.

Severity guidance:

- Low: Occasional irrelevant promotional material.
- Medium: Repeated spam or disruptive advertising.
- High: Large-scale coordinated spam, deceptive campaigns, or malicious distribution.

Enforcement guidance:

- Low: Warning or removal.
- Medium: Content restriction and possible temporary posting limits.
- High: Human review and account-level restrictions where justified.

Context exceptions:

- Approved announcements.
- Relevant commercial discussions.
- Authorized community promotions.
- Legitimate links shared as part of a discussion.

## 2.5 Sexual and Explicit Content

**Policy ID: POL-005**

Definition:

Content containing sexually explicit descriptions, sexually exploitative material, or inappropriate sexual solicitation.

Examples:

- Explicit sexual descriptions posted outside permitted contexts.
- Unsolicited sexual solicitation.
- Sexually abusive or coercive communication.
- Sexual exploitation or abuse-related material.

Severity guidance:

- Low: Mildly inappropriate sexual language.
- Medium: Explicit sexual content violating the community's permitted-content rules.
- High: Sexual exploitation, coercion, or content involving the sexual abuse of minors.

Enforcement guidance:

- Low: Warning or restriction depending on context.
- Medium: Remove or restrict the content.
- High: Immediate escalation through the designated safety procedure.

Content involving sexual exploitation or abuse of minors must never be treated as ordinary adult-content moderation.

## 2.6 Privacy Violations and Personal Information Exposure

**Policy ID: POL-006**

Definition:

Content that exposes, distributes, or threatens to expose private or sensitive personal information without appropriate authorization.

Examples:

- Publishing another user's private contact details.
- Sharing private addresses or identifiable personal information to facilitate harassment.
- Threatening to expose private information.
- Distributing confidential personal records without authorization.

Severity guidance:

- Low: Accidental exposure of limited personal information.
- Medium: Unauthorized publication of identifiable personal information.
- High: Deliberate exposure intended to facilitate stalking, harassment, or physical harm.

Enforcement guidance:

- Low: Remove or redact the exposed information.
- Medium: Restrict the content and escalate when necessary.
- High: Immediate human review and protective handling.

The system should minimize the retention and display of exposed personal information in moderation records.

## 2.7 Misinformation and Deceptive Claims

**Policy ID: POL-007**

Definition:

Content that presents demonstrably false information as fact with a meaningful risk of misleading or harming community members.

Examples:

- Fabricated claims presented as verified facts.
- Deliberately misleading impersonation of authoritative sources.
- False emergency information that could cause harm.
- Fraudulent claims intended to deceive users.

Severity guidance:

- Low: Unverified or inaccurate claims with limited impact.
- Medium: Misleading factual claims with potential community impact.
- High: Deceptive claims presenting significant and immediate risks to users.

Enforcement guidance:

- Low: Request clarification or supporting evidence.
- Medium: Human review and contextual correction where appropriate.
- High: Escalate for urgent review and restrict demonstrably harmful content where authorized.

Important distinction:

Disagreement, opinion, satire, prediction, and unverified statements are not automatically misinformation.

The system must not treat an AI model's unsupported assessment as proof that a factual statement is false.

---

# 3. Severity Classification

ContentGuard uses three severity levels.

| Level | Name | Description | Default handling |
|---|---|---|---|
| S1 | Low | Minor or ambiguous policy concern | Allow, warn, or review |
| S2 | Medium | Clear violation with moderate community impact | Restrict or remove; review where needed |
| S3 | High | Serious harm, credible threats, exploitation, or significant safety risk | Human escalation and protective handling |

## 3.1 Severity Assessment Factors

The severity level should be determined using the following factors:

1. **Intent:** Is the content accidental, informational, provocative, or deliberately harmful?
2. **Target:** Does the content target an identifiable person or protected group?
3. **Impact:** What potential harm could result?
4. **Specificity:** Does it identify a target, location, or intended action?
5. **Repetition:** Is the behavior isolated or repeated?
6. **Reach:** Is the content likely to affect a large number of users?
7. **Context:** Is it quotation, criticism, education, satire, or genuine abuse?

No single keyword should independently determine the final severity.

## 3.2 Severity Escalation

The system should escalate a case when:

- A credible threat is detected.
- The content involves possible exploitation of minors.
- Multiple violations occur together.
- The context is insufficient to distinguish harmful intent from legitimate discussion.
- AI confidence is insufficient for a safe automated recommendation.
- A high-severity violation is suspected regardless of the model's ordinary classification.

---

# 4. Moderation Decision Framework

## 4.1 Available Outcomes

ContentGuard defines four primary moderation outcomes.

| Outcome | Meaning |
|---|---|
| ALLOW | Content is permitted under the applicable policy |
| FLAG | Content is identified for further assessment |
| HOLD | Content is retained pending human review or safe recovery |
| REJECT | Content is not permitted under the applicable policy |

The system must distinguish an AI recommendation from an authorized moderation decision.

## 4.2 Decision Responsibilities

**AI Analysis Component**

The AI component may:

- Identify possible policy violations.
- Assign provisional categories.
- Recommend a severity level.
- Provide supporting evidence.
- Explain uncertainty and conflicting signals.

The AI component must not directly approve, reject, remove, ban, or otherwise execute enforcement actions.

**Deterministic Policy Engine**

The policy engine is responsible for:

- Applying mandatory safety rules.
- Evaluating the AI analysis against policy constraints.
- Determining whether a decision is permitted.
- Enforcing severity-based routing.
- Authorizing consequential moderation actions.

**Human Moderator**

Human moderators are responsible for:

- Reviewing escalated cases.
- Resolving ambiguous or conflicting evidence.
- Confirming high-risk moderation decisions.
- Recording attributable review outcomes.
- Handling cases requiring contextual judgment.

## 4.3 Decision Flow

1. User submits content.
2. Intake component validates the submission.
3. AI analysis evaluates the content against this policy.
4. The policy engine checks the AI output and mandatory safety rules.
5. The system assigns an authorized outcome.
6. High-risk or uncertain content is routed to human review.
7. The decision and supporting evidence are recorded in the audit subsystem.

If AI analysis fails, times out, or returns an invalid response, the system must place the affected content into the appropriate safe review or recovery state.

It must not automatically approve or reject content because of an AI failure.

---

# 5. Enforcement Actions

ContentGuard supports the following enforcement actions.

| Action | Description | Appropriate circumstances |
|---|---|---|
| Allow | Permit content to remain visible | No actionable violation |
| Warning | Notify the user of a policy concern | Minor or first-time violations |
| Flag | Mark content for additional assessment | Uncertain or potentially harmful content |
| Hold | Retain content pending review | AI failure or unresolved safety concern |
| Hide | Temporarily restrict public visibility | Suspected violations requiring review |
| Remove | Remove content from public access | Confirmed policy violations |
| Temporary restriction | Temporarily limit account capabilities | Repeated or serious violations |
| Account suspension | Temporarily suspend account access | Serious or repeated violations, subject to authorization |

The system must not automatically apply account-level sanctions solely on the basis of an unverified AI prediction.

Every consequential action must have:

- A policy identifier.
- A decision identifier.
- A responsible actor.
- A decision timestamp.
- A recorded rationale.
- A reference to supporting evidence.

---

# 6. Contextual Exceptions

ContentGuard must consider legitimate uses of language that may superficially resemble policy violations.

The following contexts require special consideration:

## 6.1 Educational and Academic Discussion

Content discussing hate speech, violence, harassment, or discrimination for educational or research purposes should not automatically be classified as a violation.

## 6.2 News and Public Interest Reporting

Reporting harmful incidents, quoting public statements, or discussing current events may contain offensive or threatening expressions without endorsing them.

## 6.3 Satire and Fiction

Fictional characters, jokes, parody, and role-play should be assessed according to their context and likely real-world impact.

## 6.4 Counterspeech

Users criticizing, documenting, or opposing abusive content should not be penalized merely for quoting it.

## 6.5 Ambiguous Language

When intent cannot be reliably established, the system should prefer contextual assessment and human review over an unsupported definitive judgment.

These exceptions do not override mandatory safety invariants.

---

# 7. Appeals and Human Review

## 7.1 Human Review

Users and moderators should be able to identify the policy basis for a moderation action.

Human review should consider:

- The original content.
- The relevant policy category.
- The severity assessment.
- The AI recommendation.
- The deterministic policy decision.
- Relevant conversation context.
- Available supporting evidence.

The moderator must be able to record a reason for confirming or changing a decision.

## 7.2 Appeal Extension

A formal user-facing appeal workflow is outside the initial MVP scope and is associated with the deferred appeal requirement REQ-FUN-006.

The system architecture should preserve an extension point for future appeal submission, review, and resolution.

## 7.3 Decision Reversal

When a review determines that a previous decision was incorrect:

- The correction must be recorded.
- The original decision must remain traceable.
- The system must not silently overwrite historical audit records.
- Any authorized content restoration or restriction reversal must produce a new attributable event.

---

# 8. Audit and Evidence Requirements

Every consequential moderation decision must be auditable.

The audit record should contain:

| Field | Description |
|---|---|
| decision_id | Unique decision identifier |
| content_id | Associated content identifier |
| policy_id | Applicable policy rule |
| violation_category | Identified violation category |
| severity | S1, S2, or S3 |
| ai_recommendation | AI-generated recommendation |
| policy_decision | Final authorized outcome |
| decision_actor | AI analysis, policy engine, or human moderator |
| decision_reason | Explanation of the decision |
| evidence_reference | Reference to supporting evidence |
| timestamp | Decision time |
| review_status | Pending, reviewed, confirmed, or reversed |

The audit subsystem must preserve the relationship between the original recommendation, the authorized decision, and subsequent human review.

Sensitive personal information should not be unnecessarily duplicated in audit records.

---

# 9. Policy-to-Requirements Traceability

The following table connects policy categories to the ContentGuard requirements registry.

| Policy | Category | Related requirements |
|---|---|---|
| POL-001 | Harassment | REQ-FUN-002, REQ-FUN-003, REQ-INV-003 |
| POL-002 | Hate speech | REQ-FUN-002, REQ-INV-003, REQ-SEC-001 |
| POL-003 | Threats and violence | REQ-INV-002, REQ-INV-003, REQ-FUN-003 |
| POL-004 | Spam | REQ-FUN-001, REQ-FUN-002 |
| POL-005 | Sexual content | REQ-FUN-002, REQ-SEC-001 |
| POL-006 | Privacy violations | REQ-SEC-001, REQ-SEC-004 |
| POL-007 | Misinformation | REQ-FUN-002, REQ-FUN-005, REQ-QUA-003 |

Cross-cutting requirements:

- REQ-INV-001: AI cannot directly execute enforcement.
- REQ-INV-002: AI failure must trigger safe handling.
- REQ-INV-003: High-severity content requires human review.
- REQ-INV-004: Moderation decisions must be auditable.
- REQ-INV-005: Prompt and model changes must pass semantic evaluation.
- REQ-GOV-003: Requirements registry validation.
- REQ-GOV-004: Requirements traceability.

---

# 10. Policy Evaluation and Acceptance Criteria

The policy must be testable rather than relying on subjective descriptions alone.

The following acceptance criteria are proposed for the initial implementation.

| ID | Acceptance criterion | Verification method |
|---|---|---|
| PC-001 | Each supported content category has a unique policy identifier | Policy schema validation |
| PC-002 | Each policy category defines its scope, examples, severity, and enforcement guidance | Policy completeness test |
| PC-003 | Equivalent fixed test cases produce consistent category and severity outputs | Deterministic regression test |
| PC-004 | Contextual exceptions are not automatically treated as violations | Negative test fixtures |
| PC-005 | AI output cannot directly invoke enforcement actions | Structural boundary test |
| PC-006 | High-severity cases are routed to human review | Severity-routing test |
| PC-007 | AI timeout or invalid output cannot cause automatic approval or rejection | Fault-injection test |
| PC-008 | Every consequential decision has an attributable audit record | Audit completeness test |
| PC-009 | A human moderator can review and record a decision correction | Review workflow integration test |
| PC-010 | Policy and prompt revisions are evaluated against a fixed test corpus | Semantic evaluation gate |

These criteria define the initial policy verification scope. Quantitative model-accuracy and latency thresholds must be taken from the approved requirements registry and evaluation plan rather than invented by this policy document.

---

# 11. Policy Limitations

Version 1.0 has the following limitations:

1. The policy is primarily designed for text-based moderation.
2. It does not provide a complete legal determination of whether content is unlawful.
3. It does not guarantee that AI can accurately infer user intent.
4. It does not cover every possible cultural or linguistic context.
5. It does not implement a complete appeal workflow.
6. It does not define a universal penalty schedule for every account violation.
7. It does not replace human judgment in high-risk or ambiguous cases.

These limitations must be considered when interpreting evaluation results.

---

# 12. Policy Revision and Governance

This document follows a version-controlled revision process.

| Version | Date | Changes | Status |
|---|---|---|---|
| 1.0 | 2026-11-17 | Initial policy categories, severity levels, decision framework, enforcement guidance, and audit requirements | Draft |
| 1.1 | TBD | Incorporate initial user interview findings | Planned |
| 2.0 | TBD | Revise policy based on user feedback, moderation evaluation, and team review | Planned |

Policy changes must be reviewed against:

- The requirements registry.
- The traceability matrix.
- Existing test cases.
- The evaluation corpus.
- Relevant architectural constraints.

Changes affecting safety invariants require appropriate testing and human approval.

# 13. References and Research Sources

The initial ContentGuard Community Content Policy was independently drafted using publicly available community moderation guidelines, moderation research, and evaluation resources.

The following materials are used as research references. ContentGuard does not claim ownership of the referenced policies and does not reproduce their full text.

### 13.1 Platform Community Guidelines

1. Discord. *Community Guidelines.*
   https://discord.com/guidelines

2. Reddit. *Reddit Rules.*
   https://redditinc.com/policies/reddit-rules

3. YouTube. *YouTube Community Guidelines.*
   https://support.google.com/youtube/answer/9288567

**End of Document — ContentGuard Community Content Policy v1.0**
