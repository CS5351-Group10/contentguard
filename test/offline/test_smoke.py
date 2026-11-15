"""Structural smoke tests (deterministic, offline).

Verifies repository structure integrity and registry/trace-matrix consistency.
IDs referenced: repo governance (AGENTS.md §6 rule 3); co-evolution per trace-matrix.md.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs" / "req" / "requirements.yaml"
TRACE = ROOT / "docs" / "architecture" / "trace-matrix.md"

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
]


def test_required_repository_files_exist() -> None:
    """Governance skeleton: every deliverable file required by the spec exists."""
    missing = [rel for rel in REQUIRED_FILES if not (ROOT / rel).exists()]
    assert not missing, f"missing deliverable files: {missing}"


def test_trace_matrix_covers_every_registry_requirement() -> None:
    """Co-evolution: every requirement ID in the registry appears in the trace matrix."""
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    registry_ids = {req["id"] for req in registry["requirements"]}
    trace_text = TRACE.read_text(encoding="utf-8")
    trace_ids = set(re.findall(r"REQ-[A-Z]{3}-\d{3}", trace_text))
    uncovered = registry_ids - trace_ids
    assert not uncovered, f"registry requirements missing from trace matrix: {sorted(uncovered)}"


def test_every_registered_invariant_has_zero_tolerance_true() -> None:
    """Invariant register integrity: REQ-INV-* entries are zero-tolerance with a fallback."""
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    invariants = [req for req in registry["requirements"] if req["type"] == "invariant"]
    assert invariants, "registry must contain at least one invariant"
    for req in invariants:
        assert req.get("zero_tolerance") is True, f"{req['id']} must be zero-tolerance"
        assert req.get("fallback"), f"{req['id']} must declare a concrete fallback"
        assert req.get("enforcing_component"), f"{req['id']} must name an enforcing component"
