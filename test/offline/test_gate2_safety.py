"""Gate-2 safety-path tier tests (deterministic, offline).

Verifies the path-conditional safety tier added in issue #42 (partial TD-4): when a PR
touches ``src/contentguard/policy/**`` or another declared safety path, the PR body must
reference an ADR or invariant ID. This is the only check of the safety tier that genuinely
exists today; contract diffing, API-surface diffing and the structural call-graph check are
explicit TODO(TD-4) placeholders in ``scripts/check_safety_paths.py``, not silent PASSes.

Also drives the drift test: the ``SAFETY_PATHS`` constant must stay in sync with the paths
``docs/architecture/invariants.md`` names, or every path is explicitly excluded with a
reason. The gate itself stays deterministic — it never parses invariants.md at runtime.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SAFETY_SCRIPT = ROOT / "scripts" / "check_safety_paths.py"
INVARIANTS = ROOT / "docs" / "architecture" / "invariants.md"


def _load_safety() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_safety_paths_under_test", SAFETY_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _event(files: list[str], body: str) -> dict:
    return {
        "pull_request": {
            "number": 1,
            "body": body,
            "base": {"repo": {"full_name": "o/r"}},
        },
        "_files": files,
    }


def _run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    files: list[str],
    body: str,
) -> tuple[int, str]:
    safety = _load_safety()
    event = _event(files, body)
    monkeypatch.setattr(safety, "event_payload", lambda: event)
    if not hasattr(safety, "changed_files"):
        return safety.main(), capsys.readouterr().out
    monkeypatch.setattr(safety, "changed_files", lambda *a, **k: files)
    exit_code = safety.main()
    return exit_code, capsys.readouterr().out


def test_safety_paths_constant_shape() -> None:
    """Verifies: TD-4 (partial) — SAFETY_PATHS is an explicit, reviewed constant."""
    safety = _load_safety()
    assert safety.SAFETY_PATHS == ("src/contentguard/policy/", "test/eval/")
    assert isinstance(safety.EXCLUDED, dict)


def test_policy_path_tier_requires_adr_reference(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: TD-4 (partial) / REQ-GOV-005 — negative: policy PR without an ADR/invariant ref fails."""
    exit_code, output = _run(
        monkeypatch,
        capsys,
        files=["src/contentguard/policy/rules.py"],
        body="Refactors the policy kernel. No architecture reference here.",
    )
    assert exit_code != 0
    assert "SAFETY" in output.upper()


def test_policy_path_tier_passes_with_adr_reference(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: TD-4 (partial) / REQ-GOV-005 — a policy PR citing ADR-001 / REQ-INV-001 passes."""
    exit_code, output = _run(
        monkeypatch,
        capsys,
        files=["src/contentguard/policy/rules.py"],
        body="Implements authority per ADR-001 and REQ-INV-001.",
    )
    assert exit_code == 0
    assert "PASS" in output.upper()


def test_safety_tier_skips_non_policy_pr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: TD-4 (partial) — a PR far from safety paths is not gated by the safety tier."""
    exit_code, output = _run(
        monkeypatch,
        capsys,
        files=["docs/team/roster.md", "README.md"],
        body="Docs only.",
    )
    assert exit_code == 0
    assert "SAFETY" not in output.upper() or "PASS" in output.upper()


def test_safety_tier_no_pr_context_skips(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: TD-4 (partial) — local run (no event) is a skip, matching gates 1/4/6."""
    safety = _load_safety()
    monkeypatch.setattr(safety, "event_payload", lambda: None)
    assert safety.main() == 0
    assert "SKIP" in capsys.readouterr().out.upper()


_BACKTICKED_PATH = re.compile(r"`([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)`")
_KNOWN_EXTENSIONS = (".md", ".py", ".yaml", ".yml", ".json", ".jsonl", ".toml", ".txt")


def _invariants_paths() -> list[str]:
    """Backticked repo paths with a known extension named in invariants.md."""
    found: set[str] = set()
    for match in _BACKTICKED_PATH.finditer(INVARIANTS.read_text(encoding="utf-8")):
        path = match.group(1)
        if path.endswith(_KNOWN_EXTENSIONS):
            found.add(path)
    return sorted(found)


def test_safety_paths_constant_matches_invariant_register() -> None:
    """Verifies: TD-4 (partial) — drift guard between SAFETY_PATHS and invariants.md.

    Every path the invariant register names must be either covered by SAFETY_PATHS or
    explicitly listed in EXCLUDED with a reason. If invariants.md later names a new file,
    this test fails and a human adds it to the constant — the gate stays deterministic.
    """
    safety = _load_safety()
    uncovered: list[str] = []
    for path in _invariants_paths():
        covered = any(path.startswith(prefix) for prefix in safety.SAFETY_PATHS)
        excluded = path in safety.EXCLUDED
        if not covered and not excluded:
            uncovered.append(path)
    assert not uncovered, (
        "invariants.md names paths neither in SAFETY_PATHS nor EXCLUDED: "
        f"{uncovered}. Add them to SAFETY_PATHS (the fix belongs in the constant)."
    )
    for path, reason in safety.EXCLUDED.items():
        assert isinstance(reason, str) and reason.strip(), f"EXCLUDED[{path!r}] needs a reason"
