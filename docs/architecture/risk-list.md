# Risk List (D2.10, optional)

> Assumptions that could become defects, with review triggers. **Status: DRAFT skeleton.**

| # | Assumption / risk | Could become | Review trigger | Owner |
|---|---|---|---|---|
| RSK-1 | LLM verdicts drift after provider-side model updates | silent quality regression; invariant INV-5 evidence becomes stale | any unexplained shift in evaluation-set metrics | TBD |
| RSK-2 | Evaluation set too small/biased | gate 4 passes bad prompts (guardrail debt) | safety escapes found in review queue | TBD |
| RSK-3 | Team member unavailable near W13 deadline | review bottleneck (PM sole reviewer) | any PR waiting > 24 h for review | PM |
| RSK-4 | Secrets leaked into transcripts (raw session logs) | credential exposure (course red line) | every transcript commit (sanitization check) | all |
| RSK-5 | Requirements churn late in W12/W13 | trace matrix / tests out of co-evolution | any registry change after baseline | PM |

> Each risk is reviewed at sprint end; materialized risks move to `docs/bug-diary.md`
> with the invariant gap they exposed.
