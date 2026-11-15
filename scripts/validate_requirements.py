"""CI gate 3: the requirements registry must validate against its JSON schema.

Validates docs/req/requirements.yaml against docs/req/req-schema.json (D1).
Exit 0 = pass, 1 = fail (blocking).
"""

import json
import sys
from pathlib import Path

import jsonschema  # type: ignore[import-untyped]
import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docs" / "req" / "requirements.yaml"
SCHEMA = ROOT / "docs" / "req" / "req-schema.json"


def main() -> int:
    if not REGISTRY.exists() or not SCHEMA.exists():
        print("GATE 3 FAIL: registry or schema file is missing")
        return 1
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        where = "/".join(str(part) for part in exc.absolute_path) or "<root>"
        print(f"GATE 3 FAIL: registry invalid at '{where}': {exc.message}")
        return 1
    print(f"GATE 3 PASS: {len(data['requirements'])} requirements valid against schema")
    return 0


if __name__ == "__main__":
    sys.exit(main())
