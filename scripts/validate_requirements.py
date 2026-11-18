"""CI gate 3: the requirements registry must validate against its JSON schema.

Validates docs/req/requirements.yaml against docs/req/req-schema.json (D1) and
applies cross-field checks that JSON Schema cannot express: unique IDs,
ID-prefix/type agreement, and invariant safety fields.
Exit 0 = pass, 1 = fail (blocking).
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docs" / "req" / "requirements.yaml"
SCHEMA = ROOT / "docs" / "req" / "req-schema.json"

ID_PATTERN = re.compile(r"^REQ-(FUN|INV|QUA|PER|COS|GOV|SEC)-\d{3}$")
TYPE_BY_ID_PREFIX = {
    "FUN": "functional",
    "INV": "invariant",
    "QUA": "quality",
    "PER": "performance",
    "COS": "cost",
    "GOV": "governance",
    "SEC": "security",
}
INVARIANT_STRING_FIELDS = ("enforcing_component", "fallback")


def _format_path(parts: Any) -> str:
    return "/".join(str(part) for part in parts) or "<root>"


def _schema_errors(data: Any, schema: Any) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    return [
        f"registry invalid at '{_format_path(exc.absolute_path)}': {exc.message}"
        for exc in validator.iter_errors(data)
    ]


def _requirements(data: Any) -> list[Any]:
    if not isinstance(data, dict):
        return []
    requirements = data.get("requirements")
    return requirements if isinstance(requirements, list) else []


def _duplicate_id_errors(requirements: list[Any]) -> list[str]:
    errors: list[str] = []
    first_seen: dict[str, int] = {}
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            continue
        req_id = requirement.get("id")
        if not isinstance(req_id, str):
            continue
        if req_id in first_seen:
            errors.append(
                f"duplicate requirement id '{req_id}' at requirements[{index}] "
                f"(first declared at requirements[{first_seen[req_id]}])"
            )
        else:
            first_seen[req_id] = index
    return errors


def _id_type_errors(requirements: list[Any]) -> list[str]:
    errors: list[str] = []
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            continue
        req_id = requirement.get("id")
        req_type = requirement.get("type")
        if not isinstance(req_id, str) or not isinstance(req_type, str):
            continue
        match = ID_PATTERN.fullmatch(req_id)
        if match is None:
            continue
        expected_type = TYPE_BY_ID_PREFIX[match.group(1)]
        if req_type != expected_type:
            errors.append(
                f"requirement id '{req_id}' at requirements[{index}] implies type "
                f"'{expected_type}', but declared type is '{req_type}'"
            )
    return errors


def _invariant_errors(requirements: list[Any]) -> list[str]:
    errors: list[str] = []
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict) or requirement.get("type") != "invariant":
            continue
        req_id = requirement.get("id")
        label = req_id if isinstance(req_id, str) else f"<requirements[{index}]>"
        for field in INVARIANT_STRING_FIELDS:
            value = requirement.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"invariant '{label}' at requirements[{index}] must declare a "
                    f"non-empty '{field}'"
                )
        if requirement.get("zero_tolerance") is not True:
            errors.append(
                f"invariant '{label}' at requirements[{index}] must set "
                "'zero_tolerance: true'"
            )
    return errors


def _semantic_errors(requirements: list[Any]) -> list[str]:
    return [
        *_duplicate_id_errors(requirements),
        *_id_type_errors(requirements),
        *_invariant_errors(requirements),
    ]


def main() -> int:
    if not REGISTRY.exists() or not SCHEMA.exists():
        print("GATE 3 FAIL: registry or schema file is missing")
        return 1
    try:
        data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"GATE 3 FAIL: could not read or parse registry or schema: {exc}")
        return 1

    try:
        errors = _schema_errors(data, schema)
    except jsonschema.SchemaError as exc:
        print(f"GATE 3 FAIL: requirements schema is invalid: {exc.message}")
        return 1

    requirements = _requirements(data)
    errors.extend(_semantic_errors(requirements))
    if errors:
        for error in errors:
            print(f"GATE 3 FAIL: {error}")
        return 1
    print(f"GATE 3 PASS: {len(requirements)} requirements valid against schema")
    return 0


if __name__ == "__main__":
    sys.exit(main())
