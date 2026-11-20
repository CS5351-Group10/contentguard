"""Structural CI checks for gate 2e (TD-4, REQ-INV-001) — deterministic, offline.

Gate 2e closes the structural gaps that gate 5's ``test_invariants.py`` does not cover:

- **module-set vs ADR-001** — every package directory under ``src/contentguard/`` is an
  element declared by ADR-001 (unknown directory = FAIL; a declared-but-absent element is
  **INFO**, because ``analysis/`` and ``api/`` are declared and not yet landed);
- **element-to-element import cycles** (A↔B ⇒ FAIL);
- **frozen-path guard** for ``.opencode/**`` and ``.agent/**`` **only** — never
  ``transcripts/**`` (human transcripts are committed legitimately, PR #62);
- **docs-only pass** — a PR touching only ``docs/`` passes with no source scan.

Gate 2e deliberately does **not** re-run the INV-1 enforcement scan or the dependency
direction check: those run in gate 5 via ``test_invariants.py`` and this gate must not
import a test module (inverted dependency). See issue #66 Revision 2 and
``docs/code-governance/structural-constraints.md`` §"Enforcement status".

Every test docstring cites ``TD-4`` / ``REQ-INV-001``. Fixture trees live under
``tmp_path`` so the real ``src/`` is never touched. Offline only: no network; the
checker is exercised through its pure functions and a monkeypatched PR-file fetch.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
print_check = SCRIPTS / "check_structural.py"


def _load_check() -> ModuleType:
    """Load ``scripts/check_structural.py`` by file path (no package import needed)."""
    spec = importlib.util.spec_from_file_location("check_structural_under_test", print_check)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _pkg(parent: Path, name: str | None = None, *, init: bool = True) -> Path:
    """Create a package directory (``parent/name``, or ``parent`` itself if no name).

    A ``__init__.py`` is written by default so the directory is a real package.
    """
    d = parent / name if name else parent
    d.mkdir(parents=True, exist_ok=True)
    if init:
        (d / "__init__.py").write_text("", encoding="utf-8")
    return d


def _module_file(directory: Path, filename: str, source: str) -> Path:
    """Write a Python file inside an existing package directory."""
    path = directory / filename
    path.write_text(source, encoding="utf-8")
    return path


# --------------------------------------------------------------------------------------
# Module-set vs ADR-001 element set
# --------------------------------------------------------------------------------------


def test_unknown_element_directory_fails(tmp_path: Path) -> None:
    """Verifies TD-4 / REQ-INV-001 (negative): an undeclared package directory FAILS.

    A new directory under ``src/contentguard/`` that is not an ADR-001 element is an
    architecture change, not a quiet module, so the check must name it.
    """
    check = _load_check()
    cg = _pkg(tmp_path / "contentguard")
    _pkg(cg, "policy")
    _pkg(cg, "rogue")

    findings = check.unknown_element_findings(tmp_path / "contentguard")
    assert findings, "an undeclared package directory must be reported"
    assert any("rogue" in f for f in findings), findings


def test_declared_elements_pass_module_set(tmp_path: Path) -> None:
    """Verifies TD-4 / REQ-INV-001: only ADR-001 element directories exist ⇒ no failures.

    Mirrors current ``main`` (policy/audit/escalation present).
    """
    check = _load_check()
    cg = _pkg(tmp_path / "contentguard")
    for element in ("policy", "audit", "escalation"):
        _pkg(cg, element)

    assert check.unknown_element_findings(tmp_path / "contentguard") == []


def test_declared_absent_element_is_info_not_failure(tmp_path: Path) -> None:
    """Verifies TD-4 / REQ-INV-001: a declared-but-absent element is INFO, never FAIL.

    ``analysis/`` and ``api/`` are declared by ADR-001 and not yet landed; their absence
    must not fail the gate, but it is surfaced as an informational line.
    """
    check = _load_check()
    cg = _pkg(tmp_path / "contentguard")
    for element in ("policy", "audit", "escalation"):
        _pkg(cg, element)

    infos = check.missing_element_info(tmp_path / "contentguard")
    joined = "\n".join(infos)
    assert "analysis" in joined, infos
    assert "api" in joined, infos
    # And it is reported as INFO, not folded into the failure set.
    failures, reported_infos = check.check_source(tmp_path)
    assert failures == [], failures
    assert any("analysis" in line for line in reported_infos), reported_infos


def test_pycache_is_ignored(tmp_path: Path) -> None:
    """Verifies TD-4 / REQ-INV-001: a ``__pycache__`` directory does not count as an element.

    Gate 5 runs pytest before any structural gate, so cache directories exist on the
    runner; they must not be mistaken for an undeclared module.
    """
    check = _load_check()
    cg = _pkg(tmp_path / "contentguard")
    _pkg(cg, "policy")
    cache = cg / "__pycache__"
    cache.mkdir()
    (cache / "policy.cpython-312.pyc").write_bytes(b"\x00\x00")

    assert check.unknown_element_findings(tmp_path / "contentguard") == []
    # The element set still sees policy, and no cache-derived element.
    assert set(check.element_package_dirs(tmp_path / "contentguard")) == {"policy"}


# --------------------------------------------------------------------------------------
# Element-to-element import cycles
# --------------------------------------------------------------------------------------


def _write_importing(pkg: Path, target: str) -> None:
    """Give a package a module that imports another ``contentguard`` element."""
    _module_file(pkg, "mod.py", f"import contentguard.{target}\n")


def test_cycle_detected(tmp_path: Path) -> None:
    """Verifies TD-4 / REQ-INV-001 (negative): an element cycle A→B→A FAILS.

    Element-to-element import cycles are forbidden by structural rule 5 ("no cycles").
    """
    check = _load_check()
    cg = _pkg(tmp_path / "contentguard")
    a = _pkg(cg, "audit")
    b = _pkg(cg, "escalation")
    _write_importing(a, "escalation")
    _write_importing(b, "audit")

    graph = check.element_import_graph(tmp_path / "contentguard")
    findings = check.cycle_findings(graph)
    assert findings, f"an A→B→A cycle must be reported; graph={graph}"
    joined = "\n".join(findings)
    assert "audit" in joined and "escalation" in joined, findings


def test_acyclic_graph_passes(tmp_path: Path) -> None:
    """Verifies TD-4 / REQ-INV-001: a legal acyclic edge set produces no cycle finding.

    ``api → policy`` and ``policy → audit`` are the allowed direction, not a cycle.
    """
    check = _load_check()
    cg = _pkg(tmp_path / "contentguard")
    api = _pkg(cg, "api")
    policy = _pkg(cg, "policy")
    _pkg(cg, "audit")
    _write_importing(api, "policy")
    _write_importing(policy, "audit")

    graph = check.element_import_graph(tmp_path / "contentguard")
    assert check.cycle_findings(graph) == [], graph


# --------------------------------------------------------------------------------------
# Frozen-path guard (.opencode/** and .agent/** only)
# --------------------------------------------------------------------------------------


def test_frozen_path_flagged() -> None:
    """Verifies TD-4 / REQ-INV-001 (negative): agent-frozen paths in a PR are flagged.

    ``.opencode/**`` and ``.agent/**`` are human-only; an agent PR touching them fails.
    """
    check = _load_check()
    files = [".opencode/rules.md", ".agent/rules.md", "src/contentguard/policy/engine.py"]
    hits = check.frozen_hits(files)
    assert ".opencode/rules.md" in hits, hits
    assert ".agent/rules.md" in hits, hits
    assert "src/contentguard/policy/engine.py" not in hits, hits


def test_transcripts_not_frozen() -> None:
    """Verifies TD-4 / REQ-INV-001: ``transcripts/**`` is NOT frozen by this guard.

    Human-authored transcripts are committed legitimately (PR #62); the guard must not
    flag them.
    """
    check = _load_check()
    files = ["transcripts/60914643-HAN-Mei-AI-002.md", "docs/ai-use-log.yaml"]
    assert check.frozen_hits(files) == []


# --------------------------------------------------------------------------------------
# docs-only pass and closed-fail on a missing token (CI main() behaviour)
# --------------------------------------------------------------------------------------


def _pr_event(tmp_path: Path) -> Path:
    """Write a minimal pull_request event payload and return its path."""
    import json

    payload = {
        "pull_request": {
            "number": 123,
            "base": {"repo": {"full_name": "CS5351-Group10/contentguard"}},
        }
    }
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_docs_only_passes_without_source_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies TD-4 / REQ-INV-001: a PR touching only ``docs/`` passes, no source scan.

    A docs-only PR must not be blocked by structural checks, and the source-tree scan is
    skipped entirely (nothing under ``src/`` changed).
    """
    check = _load_check()
    event_path = _pr_event(tmp_path)
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setattr(
        check, "changed_files", lambda *_a, **_k: ["docs/architecture/readme.md"]
    )
    # Prove the source scan did not run for a docs-only PR.
    monkeypatch.setattr(
        check, "check_source", lambda *_a, **_k: pytest.fail("source scan must not run")
    )

    assert check.main([]) == 0
    assert "docs-only" in capsys.readouterr().out.lower()


def test_missing_token_on_pr_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies TD-4 / REQ-INV-001 (negative): a PR event with no GITHUB_TOKEN FAILS CLOSED.

    A blank credential must not silently disable the frozen-path check (the #61 blind
    spot). The failure is actionable, and the source-tree part still runs so all findings
    surface at once — never a 401 traceback.
    """
    check = _load_check()
    event_path = _pr_event(tmp_path)
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    ran_source = {"called": False}

    def fake_check_source(_root: Path) -> tuple[list[str], list[str]]:
        ran_source["called"] = True
        return [], []

    monkeypatch.setattr(check, "check_source", fake_check_source)

    exit_code = check.main([])
    out = capsys.readouterr().out
    assert exit_code != 0, "missing token on a PR event must fail closed"
    assert "GITHUB_TOKEN" in out, out
    assert "cannot list changed files" in out.lower(), out
    assert ran_source["called"], "the source-tree part must still run"
