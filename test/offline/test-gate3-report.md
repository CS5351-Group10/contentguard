# Gate 3 Evidence Report — Requirements Validator v2

- Test plan reference: Issue #24 (approved plan supplied by the Testing Lead; no GitHub access used)
- Requirements: REQ-GOV-003 (validate the registry), REQ-GOV-004 (trace acceptance evidence)
- Validator under test: `scripts/validate_requirements.py`
- Permanent test file: `test/offline/test_validate_requirements.py`
- Environment: Python 3.14.4, pytest 9.1.1, pyyaml 6.0.3, jsonschema 4.19.2

## Evidence files

| Artifact | Path |
|---|---|
| Initial targeted Gate 3 run | `test-results/gate3/pytest-initial-run.txt` |
| Full offline regression run | `test-results/gate3/pytest-offline-regression.txt` |
| Actual validator run | `test-results/gate3/validator-result.txt` |
| Verbatim OpenCode session export | `transcripts/gate3/gate3-validator-v2-session.md` |

## Ten approved test cases

| # | Test function | Requirement(s) | Case covered |
|---|---|---|---|
| 1 | `test_duplicate_id_rejected` | REQ-GOV-003, REQ-GOV-004 | Duplicate requirement ID rejected with a non-zero exit and duplicate-ID diagnostic. |
| 2 | `test_id_type_agreement` | REQ-GOV-003, REQ-GOV-004 | ID prefix/type disagreement rejected with a non-zero exit and mismatch diagnostic. |
| 3 | `test_invariant_required_fields` | REQ-GOV-003 | Parameterized over `enforcing_component`, `fallback`, and `zero_tolerance`; each missing field is rejected. |
| 4 | `test_lifecycle_status_values` | REQ-GOV-003 | Invalid lifecycle status `approved` rejected by the schema enum. |
| 5 | `test_valid_registry_passes` | REQ-GOV-003, REQ-GOV-004 | Exact current 31-requirement registry copied into `tmp_path` passes with exit code 0. |
| 6 | `test_missing_fallback_rejected` | REQ-GOV-003 | Missing invariant fallback rejected by both schema and validator semantic checks. |
| 7 | `test_unknown_type_rejected` | REQ-GOV-003 | Requirement type outside the schema enum rejected. |
| 8 | `test_moscow_tradeoff_note_required` | REQ-GOV-003 | Both a missing `moscow_tradeoff_note` and a value shorter than 40 characters are rejected. |
| 9 | `test_source_origin_required` | REQ-GOV-003, REQ-GOV-004 | Missing `source.origin` rejected. |
| 10 | `test_invariant_zero_tolerance_must_be_true` | REQ-GOV-003 | `zero_tolerance: false` on an invariant rejected by schema const and semantic check. |

All ten named tests were executed. `test_invariant_required_fields` expanded into three parametrized cases, so the targeted run collected 12 items.

## Commands and actual results

### 1. Targeted Gate 3 suite

Command:

```text
python3 -m pytest test/offline/test_validate_requirements.py -v
```

Result:

- Collected: 12
- Passed: 12
- Failed: 0
- Exit code: 0
- Warnings/failures: none

### 2. Complete offline regression suite

Command:

```text
python3 -m pytest test/offline -v
```

Result:

- Collected: 20
- Passed: 20
- Failed: 0
- Exit code: 0
- Warnings/failures: none

Breakdown: 12 new validator cases plus all 8 pre-existing offline tests (`test_pr_files_headers.py`: 5, `test_smoke.py`: 3). No existing offline test regressed.

### 3. Actual requirements validator

Command:

```text
python3 scripts/validate_requirements.py
```

Result:

- Exit code: 0
- Output: `GATE 3 PASS: 31 requirements valid against schema`
- Requirements validated: 31
- Warnings/failures: none

## Test file integrity

`test/offline/test_validate_requirements.py` is present and non-empty: 235 lines, 8267 bytes.

## Transcript export

The complete current OpenCode session was available in the local OpenCode database and was exported verbatim to `transcripts/gate3/gate3-validator-v2-session.md`. The export includes the actual stored user messages, assistant text, reasoning parts, tool calls, tool inputs/outputs, patch parts, and message metadata. No conversation messages were fabricated or reconstructed.
