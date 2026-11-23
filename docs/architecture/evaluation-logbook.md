# Evaluation Logbook (D2.9, optional)

> Accumulated evidence behind the architecture choices. Status: Phase ② baseline
> (2026-11-16). Append entries as experiments/measurements happen; never rewrite history.
> **Planned rows are not evidence** — they become entries only when the run exists.

| Date | Question | Experiment / evidence | Result | Influenced |
|---|---|---|---|---|
| 2026-11-16 | Which architecture candidate? | ADD scoring session: criteria/weights (35/25/25/15), candidates C1/C2/C3, design-judgment scores | C1 5.00; C3 4.00; C2 3.25; C1 selected | ADR-001; `evaluation-table.md` |
| 2026-11-16 | What context envelope is proposed for the provider and cost target? | Design allocation from the provider context limit + 1,024 output + 1,024 reserve; compaction at 75% of the input cap (4,608 / 6,144) | Proposed: 8,192 envelope; 6,144 input cap; 4,608 compaction trigger; 20 s per-call deadline. **Not provider-validated and not a measured cost/latency result**; validation is pending S5 | ADR-001 "Layered context"; `runtime-policy-catalog.md` R-9 |
| Planned (S4) | Does gate 4 replay the fixed set and block a bad prompt? | `test/eval/` harness + `check_semantic_eval.py --strict`; deliberately bad-prompt fixture | Pending — do not record as evidence until the run exists | INV-5; gate 4 |
| Planned (S5) | What are measured latency, token usage, and agreement by slice? | Fixed eval set + benchmark of ≥100 requests; per-slice agreement/FP/FN; p50/p95 latency; token usage. **Full benchmark deferred under #23**; record only actual findings | Pending — fills REQ-QUA-003 / PER-001 / COS-001 evidence only if the run exists | Report §4; requirements status |
| Planned (S5) | Does test evidence trigger an architecture revision? | Buna's fault-injection/eval session finds a defect; ADR/blueprint revision recorded | Pending — this is the D5 stage-5 evidence | ADR-001 revision; Report §5 |
| 2026-11-22 | Does the main baseline at `9e189e9ee7175349d7b20694108a991e0ec0254a` pass deterministic verification? | On 2026-11-22, fetched `main` in the pre-#84 state and ran `pytest test/offline -v`, `ruff check src scripts test`, `MYPYPATH=src mypy scripts test`, and `python scripts/validate_requirements.py` | **535 tests passed; Ruff passed; mypy passed for 47 source files; Gate 3 passed with 31 requirements**. This is deterministic offline baseline evidence only; it does not establish live-provider or semantic replay acceptance or an approved architecture revision. | S5 evidence baseline; Report §5 |

> **Evaluation provenance (planned, 2026-11-17):** the fixed set is planned from Jigsaw
> 2018 (dataset CC0; underlying Wikipedia text CC BY-SA 3.0) plus team-authored synthetic
> Chinese/English cases, with COLD (Apache-2.0) only if PR #37 keeps it. Raw third-party
> text must stay out of `main` until the license/NOTICE and PII review lands (PR #37). No
> measured agreement/latency/cost result is claimed. Full performance/cost benchmarks are deferred
> under decision #23; the S5 fault exercise records actual findings, including "no
> finding", rather than presupposing a defect.
>
> Any number in the evaluation table or ADR rationale not backed by a completed logbook
> entry is an assumption and is flagged in `risk-list.md`.
