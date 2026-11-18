"""Structural smoke tests (deterministic, offline).

Verifies repository-structure integrity and registry/trace-matrix consistency. This file
was regenerated through an OpenCode session (issue #42, TD-3) from the current ADR-001
state and the 31-ID registry; it keeps — and only strengthens — the coverage assertion of
the human-drafted seed.

IDs referenced: REQ-GOV-004 (trace matrix keeps the registry in lockstep) and the
REQ-INV-* zero-tolerance fields; repo governance per AGENTS.md §6 rule 3.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs" / "req" / "requirements.yaml"
TRACE = ROOT / "docs" / "architecture" / "trace-matrix.md"
ID_PATTERN = re.compile(r"REQ-[A-Z]{3}-\d{3}")

REQUIRED_FILES = [
    "README.md",
    "AGENTS.md",
    "Prompt.md",
    "Report.md",
    "architecture-blueprint.md",
    "docs/req/requirements.yaml",
    "docs/req/req-schema.json",
    "docs/architecture/invariants.md",
    "docs/architecture/trace-matrix.md",
    "docs/code-governance/structural-constraints.md",
    "docs/code-governance/verification-constraints.md",
    "docs/ai-use-log.yaml",
    "docs/review-memo.md",
    ".opencode/permissions.jsonc",
    ".opencode/rules.md",
    ".agent/rules.md",
    ".github/workflows/ci.yml",
    "scripts/validate_requirements.py",
    "requirements.txt",
]


def _registry_ids(registry_path: Path = REGISTRY) -> set[str]:
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    return {req["id"] for req in registry["requirements"]}


def _uncovered(registry_path: Path, trace_text: str) -> set[str]:
    return _registry_ids(registry_path) - set(ID_PATTERN.findall(trace_text))


def test_required_repository_files_exist() -> None:
    """REQ-GOV-004: every deliverable file required for the governance skeleton exists."""
    missing = [rel for rel in REQUIRED_FILES if not (ROOT / rel).exists()]
    assert not missing, f"missing deliverable files: {missing}"


def test_trace_matrix_covers_every_registry_requirement() -> None:
    """REQ-GOV-004: every requirement ID in the registry appears in the trace matrix."""
    uncovered = _uncovered(REGISTRY, TRACE.read_text(encoding="utf-8"))
    assert not uncovered, f"registry requirements missing from trace matrix: {sorted(uncovered)}"


def test_trace_coverage_assertion_is_not_vacuous(tmp_path: Path) -> None:
    """REQ-GOV-004: negative — an ID absent from the trace matrix is reported as uncovered.

    Guards against a regeneration that silently weakens the coverage check: inject a
    registry entry with an ID that is not in the real trace matrix and assert the same
    set-difference logic the gate uses reports it.
    """
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    registry["requirements"].append({"id": "REQ-GOV-999"})
    fake_registry = tmp_path / "requirements.yaml"
    fake_registry.write_text(
        yaml.safe_dump(registry, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    uncovered = _uncovered(fake_registry, TRACE.read_text(encoding="utf-8"))
    assert uncovered == {"REQ-GOV-999"}


def test_every_registered_invariant_has_zero_tolerance_true() -> None:
    """REQ-INV-001..005: invariant entries are zero-tolerance with a fallback and enforcer."""
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    invariants = [req for req in registry["requirements"] if req["type"] == "invariant"]
    assert invariants, "registry must contain at least one invariant"
    for req in invariants:
        assert req.get("zero_tolerance") is True, f"{req['id']} must be zero-tolerance"
        assert req.get("fallback"), f"{req['id']} must declare a concrete fallback"
        assert req.get("enforcing_component"), f"{req['id']} must name an enforcing component"


@pytest.mark.parametrize("inv_id", [f"REQ-INV-00{i}" for i in range(1, 6)])
def test_all_five_invariants_present(inv_id: str) -> None:
    """REQ-INV-001..005: the registry declares all five invariant IDs named in invariants.md."""
    assert inv_id in _registry_ids(), f"{inv_id} must be registered"
