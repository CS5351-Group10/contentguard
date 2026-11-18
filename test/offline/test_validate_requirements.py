"""Gate 3 requirements-validator tests (deterministic, offline).

Every case drives scripts/validate_requirements.py through temporary fixtures and
cites the governance requirement it verifies (REQ-GOV-003 and/or REQ-GOV-004).
"""

from __future__ import annotations

import copy
import importlib.util
import shutil
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "scripts" / "validate_requirements.py"
SCHEMA_PATH = ROOT / "docs" / "req" / "req-schema.json"
REGISTRY_PATH = ROOT / "docs" / "req" / "requirements.yaml"


def _load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "validate_requirements_under_test", VALIDATOR_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _valid_registry_data() -> dict[str, Any]:
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    requirements = data.get("requirements")
    assert isinstance(requirements, list) and len(requirements) == 31
    return data


def _fixture(
    tmp_path: Path, data: dict[str, Any], name: str
) -> tuple[Path, Path]:
    registry = tmp_path / f"{name}-requirements.yaml"
    schema = tmp_path / f"{name}-req-schema.json"
    registry.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    schema.write_text(SCHEMA_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return registry, schema


def _copy_fixture(tmp_path: Path, name: str) -> tuple[Path, Path]:
    registry = tmp_path / f"{name}-requirements.yaml"
    schema = tmp_path / f"{name}-req-schema.json"
    shutil.copyfile(REGISTRY_PATH, registry)
    shutil.copyfile(SCHEMA_PATH, schema)
    return registry, schema


def _run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    registry: Path,
    schema: Path,
) -> tuple[int, str]:
    monkeypatch.setattr(validator, "REGISTRY", registry)
    monkeypatch.setattr(validator, "SCHEMA", schema)
    exit_code = validator.main()
    return exit_code, capsys.readouterr().out


def test_duplicate_id_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-GOV-003/REQ-GOV-004: duplicate requirement IDs must be rejected."""
    data = _valid_registry_data()
    data["requirements"].append(copy.deepcopy(data["requirements"][0]))
    registry, schema = _fixture(tmp_path, data, "duplicate-id")
    exit_code, output = _run(monkeypatch, capsys, registry, schema)
    assert exit_code != 0
    assert "duplicate requirement id 'REQ-INV-001'" in output


def test_id_type_agreement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-GOV-003/REQ-GOV-004: an ID prefix must agree with the declared type."""
    data = _valid_registry_data()
    data["requirements"][0]["type"] = "functional"
    registry, schema = _fixture(tmp_path, data, "id-type")
    exit_code, output = _run(monkeypatch, capsys, registry, schema)
    assert exit_code != 0
    assert "implies type 'invariant'" in output
    assert "declared type is 'functional'" in output


@pytest.mark.parametrize(
    "missing_field",
    ["enforcing_component", "fallback", "zero_tolerance"],
)
def test_invariant_required_fields(
    missing_field: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-GOV-003: every invariant must declare all mandatory safety fields."""
    data = _valid_registry_data()
    data["requirements"][0].pop(missing_field)
    registry, schema = _fixture(tmp_path, data, f"invariant-fields-{missing_field}")
    exit_code, output = _run(monkeypatch, capsys, registry, schema)
    assert exit_code != 0
    assert missing_field in output
    assert "REQ-INV-001" in output


def test_lifecycle_status_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-GOV-003: an invalid lifecycle status must be rejected."""
    data = _valid_registry_data()
    data["requirements"][0]["status"] = "approved"
    registry, schema = _fixture(tmp_path, data, "lifecycle-status")
    exit_code, output = _run(monkeypatch, capsys, registry, schema)
    assert exit_code != 0
    assert "'approved' is not one of" in output
    assert "status" in output


def test_valid_registry_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-GOV-003/REQ-GOV-004: the actual 31-requirement registry must pass gate 3."""
    registry, schema = _copy_fixture(tmp_path, "valid")
    exit_code, output = _run(monkeypatch, capsys, registry, schema)
    assert exit_code == 0
    assert "GATE 3 PASS: 31 requirements valid against schema" in output


def test_missing_fallback_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-GOV-003: an invariant without a concrete fallback must be rejected."""
    data = _valid_registry_data()
    data["requirements"][1].pop("fallback")
    registry, schema = _fixture(tmp_path, data, "missing-fallback")
    exit_code, output = _run(monkeypatch, capsys, registry, schema)
    assert exit_code != 0
    assert "'fallback' is a required property" in output
    assert "non-empty 'fallback'" in output


def test_unknown_type_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-GOV-003: a requirement type outside the schema enum must be rejected."""
    data = _valid_registry_data()
    data["requirements"][0]["type"] = "unknown"
    registry, schema = _fixture(tmp_path, data, "unknown-type")
    exit_code, output = _run(monkeypatch, capsys, registry, schema)
    assert exit_code != 0
    assert "'unknown' is not one of" in output
    assert "type" in output


def test_moscow_tradeoff_note_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-GOV-003: the MoSCoW note must exist and meet its minimum length."""
    missing = _valid_registry_data()
    missing.pop("moscow_tradeoff_note")
    registry, schema = _fixture(tmp_path, missing, "note-missing")
    exit_code, output = _run(monkeypatch, capsys, registry, schema)
    assert exit_code != 0
    assert "moscow_tradeoff_note" in output
    assert "is a required property" in output

    short = _valid_registry_data()
    short["moscow_tradeoff_note"] = "too short"
    registry, schema = _fixture(tmp_path, short, "note-short")
    exit_code, output = _run(monkeypatch, capsys, registry, schema)
    assert exit_code != 0
    assert "moscow_tradeoff_note" in output
    assert "is too short" in output


def test_source_origin_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-GOV-003/REQ-GOV-004: each requirement must declare a source origin."""
    data = _valid_registry_data()
    data["requirements"][0]["source"].pop("origin")
    registry, schema = _fixture(tmp_path, data, "source-origin")
    exit_code, output = _run(monkeypatch, capsys, registry, schema)
    assert exit_code != 0
    assert "'origin' is a required property" in output
    assert "source" in output


def test_invariant_zero_tolerance_must_be_true(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-GOV-003: an invariant with zero_tolerance false must be rejected."""
    data = _valid_registry_data()
    data["requirements"][1]["zero_tolerance"] = False
    registry, schema = _fixture(tmp_path, data, "zero-tolerance")
    exit_code, output = _run(monkeypatch, capsys, registry, schema)
    assert exit_code != 0
    assert "zero_tolerance" in output
    assert "True was expected" in output
    assert "must set 'zero_tolerance: true'" in output
