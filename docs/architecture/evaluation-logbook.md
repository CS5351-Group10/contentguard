# Evaluation Logbook (D2.9, optional)

> Accumulated evidence behind the architecture choices. Status: Phase ② baseline
> (2026-11-16). Append entries as experiments/measurements happen; never rewrite history.
> **Planned rows are not evidence** — they become entries only when the run exists.

| Date | Question | Experiment / evidence | Result | Influenced |
|---|---|---|---|---|
| 2026-11-16 | Which architecture candidate? | ADD scoring session: criteria/weights (35/25/25/15), candidates C1/C2/C3, design-judgment scores | C1 5.00; C3 4.00; C2 3.25; C1 selected | ADR-001; `evaluation-table.md` |
| 2026-11-16 | What context envelope fits the provider and the cost target? | Derivation from the provider context limit + 1,024 output + 1,024 reserve; compaction at 75% of the input cap (4,608 / 6,144) | 8,192 envelope; 6,144 input cap; 4,608 compaction trigger; 20 s per-call deadline (provisional design values) | ADR-001 "Layered context"; `runtime-policy-catalog.md` R-9 |
| Planned (S4) | Does gate 4 replay the fixed set and block a bad prompt? | `test/eval/` harness + `check_semantic_eval.py --strict`; deliberately bad-prompt fixture | Pending — do not record as evidence until the run exists | INV-5; gate 4 |
| Planned (S5) | What are measured latency, token usage, and agreement by slice? | Fixed eval set + benchmark of ≥100 requests; per-slice agreement/FP/FN; p50/p95 latency; token usage | Pending — fills REQ-QUA-003 / PER-001 / COS-001 evidence | Report §4; requirements status |
| Planned (S5) | Does test evidence trigger an architecture revision? | Buna's fault-injection/eval session finds a defect; ADR/blueprint revision recorded | Pending — this is the D5 stage-5 evidence | ADR-001 revision; Report §5 |

> Any number in the evaluation table or ADR rationale not backed by a completed logbook
> entry is an assumption and is flagged in `risk-list.md`.
