# Gate 3 Evidence Report — Requirements Validator v2

## 1. Task Information

- **Student:** HAN Mei (60914643)
- **Main line:** Requirements Engineering (D1 requirements registry, JSON Schema, Gate 3 validator, requirements traceability)
- **Task:** Enhance `scripts/validate_requirements.py` to support the updated ContentGuard requirements registry, including duplicate ID detection, ID/type consistency, required-field validation, invariant safety checks, and clear error reporting with appropriate exit codes.
- **Agent:** OpenCode
- **Model displayed:** Big Pickle
- **Test plan reference:** Issue #24 (approved test plan supplied by the Testing Lead)
- **Requirements:** REQ-GOV-003, REQ-GOV-004
- **Working directory:** `/mnt/c/Users/Mei HAN/Desktop/contentguard`

## 2. Implementation Scope

The validator under test is:

`scripts/validate_requirements.py`

The permanent test suite is:

`test/offline/test_validate_requirements.py`

The implementation covers:

1. Duplicate requirement ID detection.
2. Requirement ID prefix and type consistency.
3. Required-field validation for invariant requirements.
4. Lifecycle status validation against the JSON Schema enum.
5. Requirement type validation.
6. MoSCoW trade-off note validation.
7. Source origin validation.
8. Invariant zero-tolerance enforcement.
9. Clear schema and semantic validation error reporting.
10. Appropriate process exit codes for CI integration.

The implementation preserves the existing requirements registry and validates it against the repository's JSON Schema.

## 3. Approved Test Cases

Ten approved test functions were implemented and executed.

| # | Test function | Requirement | Case covered |
|---|---|---|---|
| 1 | `test_duplicate_id_rejected` | REQ-GOV-003, 004 | Reject duplicate requirement IDs with a non-zero exit code and diagnostic. |
| 2 | `test_id_type_agreement` | REQ-GOV-003, 004 | Reject ID prefix and requirement type mismatches. |
| 3 | `test_invariant_required_fields` | REQ-GOV-003 | Reject missing `enforcing_component`, `fallback`, and `zero_tolerance`. |
| 4 | `test_lifecycle_status_values` | REQ-GOV-003 | Reject invalid lifecycle status `approved`. |
| 5 | `test_valid_registry_passes` | REQ-GOV-003, 004 | Accept the exact current 31-requirement registry. |
| 6 | `test_missing_fallback_rejected` | REQ-GOV-003 | Reject an invariant without a fallback. |
| 7 | `test_unknown_type_rejected` | REQ-GOV-003 | Reject requirement types outside the schema enum. |
| 8 | `test_moscow_tradeoff_note_required` | REQ-GOV-003 | Reject a missing or shorter-than-40-character MoSCoW note. |
| 9 | `test_source_origin_required` | REQ-GOV-003, 004 | Reject a missing `source.origin`. |
| 10 | `test_invariant_zero_tolerance_must_be_true` | REQ-GOV-003 | Reject `zero_tolerance: false` for an invariant. |

**Test parameterization:** `test_invariant_required_fields` covers three independent missing-field scenarios. Therefore, the ten named test functions produce 12 collected pytest items.

## 4. Test Environment

| Component | Version |
|---|---|
| Python | 3.14.4 |
| pytest | 9.1.1 |
| PyYAML | 6.0.3 |
| jsonschema | 4.19.2 |

## 5. Execution Commands and Results

### 5.1 Targeted Gate 3 Test Suite

Command:

```bash
python3 -m pytest test/offline/test_validate_requirements.py -v
```

Recorded result:

- Collected: 12
- Passed: 12
- Failed: 0
- Exit code: 0
- Warnings/failures: None

### 5.2 Complete Offline Regression Suite

Command:

```bash
python3 -m pytest test/offline -v
```

Recorded result:

- Collected: 20
- Passed: 20
- Failed: 0
- Exit code: 0
- Warnings/failures: None

Breakdown:

- 12 new validator test cases.
- 5 existing tests in `test_pr_files_headers.py`.
- 3 existing tests in `test_smoke.py`.

No existing offline test regression was reported.

### 5.3 Actual Requirements Validator

Command:

```bash
python3 scripts/validate_requirements.py
```

Recorded result:

```text
GATE 3 PASS: 31 requirements valid against schema
```

- Requirements validated: 31
- Exit code: 0
- Warnings/failures: None

## 6. Permanent Test Suite Integrity

The permanent test file was recorded as:

- File: `test/offline/test_validate_requirements.py`
- Lines: 235
- Size: 8,267 bytes
- Test functions: 10
- Collected test items: 12

The test suite uses temporary fixtures to validate invalid and valid registry scenarios without modifying the actual requirements registry.

## 7. OpenCode Session Provenance

The implementation and verification work was recorded in the following OpenCode session:

- **Session ID:** `ses_e170e175cffeErOe3BcXI8zqed`
- **Slug:** `hidden-lagoon`
- **Session title:** ContentGuard Requirements Validator v2 test plan
- **Agent:** `build`
- **Model:** Big Pickle (`big-pickle`)
- **Provider:** OpenCode
- **Created (UTC):** 2026-11-17 09:58:50
- **Last updated (UTC):** 2026-11-17 10:15:16
- **Messages exported:** 44
- **Parts exported:** 195

The session included project inspection, implementation planning, test development, execution and verification.

Human supervision included approval of the implementation plan, separate authorization of the verification stage, and clarification that the traceability-matrix issue should be treated as an architecture dependency rather than a validator defect.

## 8. Final Results

The Gate 3 validator v2 implementation and its recorded test results demonstrate the following:

1. The validator accepts the current 31-requirement registry.
2. Invalid requirement data is rejected through schema and semantic checks.
3. Duplicate IDs and ID/type inconsistencies are detected.
4. Invariant safety requirements are enforced.
5. The targeted validator suite records 12/12 passing cases.
6. The complete offline regression suite records 20/20 passing cases.
7. The validator returns exit code 0 for the valid registry.

**Overall recorded result: Gate 3 PASS.**

The implementation addresses REQ-GOV-003 and contributes test and validation evidence towards REQ-GOV-004.

---

**Evidence qualification:** The results in this report reflect the recorded execution outputs and OpenCode session information. This report consolidates the evidence into one document; it does not claim that deleted standalone output files remain available or that tests were independently re-executed during report preparation.