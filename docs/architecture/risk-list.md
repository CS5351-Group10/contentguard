# Risk List (D2.10, optional)

> Assumptions that could become defects, with review triggers. Status: Phase ② baseline
> (2026-11-16).

| # | Assumption / risk | Could become | Review trigger | Owner |
|---|---|---|---|---|
| RSK-1 | LLM verdicts drift after provider-side model updates | silent quality regression; INV-5 evidence becomes stale | any unexplained shift in evaluation-set metrics | Architecture owner (Shiyi) |
| RSK-2 | Evaluation set too small or biased | gate 4 passes bad prompts (guardrail debt) | safety escapes found in the review queue | Testing owner (Buna) |
| RSK-3 | Team member unavailable near the deadline | review bottleneck (PM is the default reviewer) | any PR waiting > 24 h for review | PM |
| RSK-4 | Secrets leaked into transcripts (raw session logs) | credential exposure (course red line) | every transcript commit (sanitization check) | All members; PM checks |
| RSK-5 | Requirements churn late in the build | trace matrix / tests out of co-evolution | any registry change after baseline | PM |
| RSK-6 | Runtime LLM provider access/quota unavailable in CI or the demo | live analysis test or gate 4 cannot run; demo fails | first live-test attempt; CI secret check | Architecture owner + PM |
| RSK-7 | Scope overrun (24 Must requirements in a four-day build) | partial implementation; weak verification | any session plan exceeding its slice; daily stand-up | PM |
| RSK-8 | Transcript evidence incomplete or not "full raw" at the 11/21 lock | D5 score loss; audit-chain gap | transcript checkpoint 11/18 and 11/21 | PM + each member |

> Each risk is reviewed at sprint end; materialized risks move to `docs/bug-diary.md`
> with the invariant gap they exposed.
