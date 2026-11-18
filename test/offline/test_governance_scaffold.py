"""Gate-2 dependency manifest and scaffold-regeneration tests (deterministic, offline).

Covers the two jobs of issue #42:

- TD-8: the CI toolchain is declared in ``requirements.txt`` and gate 2 fails when the
  manifest is absent or declares an uninstallable requirement.
- TD-3: the regenerated scaffold seed (``pytest.ini``, ``prompts/*.yaml``) keeps the
  guarantees the human draft had, without weakening them.

Every test docstring cites the debt / requirement ID it verifies; these are governance
infrastructure, so there is no direct REQ ID for most of them. ``test_smoke.py`` keeps
the registry trace-matrix coverage assertion (REQ-GOV-004).

Offline only: ``check_dependencies.run_pip_check`` is never called here — the manifest
logic is exercised through ``--offline``/monkeypatched fixtures so no network or pip
subprocess is needed (``.agent/rules.md`` C2/C3).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEPS_SCRIPT = ROOT / "scripts" / "check_dependencies.py"
MANIFEST = ROOT / "requirements.txt"
PROMPTS_DIR = ROOT / "prompts"
PYTEST_INI = ROOT / "pytest.ini"

CI_TOOLCHAIN = ("pytest", "ruff", "mypy", "pyyaml", "jsonschema")


def _load_deps() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_dependencies_under_test", DEPS_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_manifest(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_manifest_declares_ci_toolchain() -> None:
    """Verifies: TD-8 / REQ-GOV-006 — a manifest exists and declares every tool CI installs.

    This is the single source of truth: ``ci.yml`` installs from ``requirements.txt``,
    so a missing tool here means CI silently stops installing it.
    """
    assert MANIFEST.exists(), "requirements.txt must exist (TD-8: declared dependency manifest)"
    declared = MANIFEST.read_text(encoding="utf-8").lower()
    missing = [tool for tool in CI_TOOLCHAIN if tool.lower() not in declared]
    assert not missing, f"requirements.txt does not declare CI tools: {missing}"


def test_missing_manifest_fails_gate2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verifies: TD-8 — negative: no manifest ⇒ gate 2 dependency check exits nonzero.

    The failure must be actionable (names ``requirements.txt``), not a bare traceback.
    """
    deps = _load_deps()
    monkeypatch.setattr(deps, "MANIFEST", tmp_path / "requirements.txt")
    exit_code = deps.main(["--offline"])
    output = capsys.readouterr().out
    assert exit_code != 0
    assert "GATE 2 FAIL" in output
    assert "requirements.txt" in output


def test_broken_dependency_fails_gate2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verifies: TD-8 — negative: a manifest that omits a required tool ⇒ gate 2 fails.

    A broken/partial manifest (an agent edited it and dropped a tool CI relies on) must
    fail closed rather than let the workflow install an incomplete toolchain.
    """
    deps = _load_deps()
    manifest = tmp_path / "requirements.txt"
    _write_manifest(manifest, ["pytest>=8,<9", "ruff>=0.6,<1"])  # mypy/pyyaml/jsonschema missing
    monkeypatch.setattr(deps, "MANIFEST", manifest)
    exit_code = deps.main(["--offline"])
    output = capsys.readouterr().out
    assert exit_code != 0
    assert "GATE 2 FAIL" in output
    assert "mypy" in output


def test_manifest_parses_and_passes_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies: TD-8 — a complete manifest passes the offline check without shelling to pip."""
    deps = _load_deps()
    manifest = tmp_path / "requirements.txt"
    _write_manifest(manifest, [f"{tool}==1.0" for tool in CI_TOOLCHAIN])
    monkeypatch.setattr(deps, "MANIFEST", manifest)
    assert deps.main(["--offline"]) == 0


def test_pytest_ini_scopes_offline_suite() -> None:
    """Verifies: TD-3 — pytest collects test/offline by default, never test/live.

    Gate 5 runs ``pytest test/offline`` explicitly, but a default ``pytest`` at repo root
    must not drag the live tier (network, provider keys) into the deterministic suite.
    """
    text = PYTEST_INI.read_text(encoding="utf-8")
    assert "testpaths" in text, "pytest.ini must pin testpaths"
    section = text.split("testpaths", 1)[1].splitlines()[0]
    assert "test/offline" in section, f"testpaths must include test/offline, got: {section!r}"
    assert "test/live" not in section, "testpaths must not include the live tier"
    # The live tier must be opt-in only; no `testpaths = test` that sweeps both tiers.
    assert "testpaths = test\n" not in text and "testpaths = test\r\n" not in text


def test_prompts_yaml_parse_and_versioned() -> None:
    """Verifies: TD-3 — every prompts/*.yaml parses, carries a version, no unknown keys."""
    allowed = {
        "version",
        "component",
        "role",
        "response_schema",
        "system_prompt",
        "status",
        "notes",
    }
    prompt_files = sorted(PROMPTS_DIR.glob("*.yaml"))
    assert prompt_files, "at least one prompt must exist"
    for path in prompt_files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{path.name} must parse to a mapping"
        assert data.get("version"), f"{path.name} must declare a version"
        unknown = set(data) - allowed
        assert not unknown, f"{path.name} has unknown keys: {sorted(unknown)}"
