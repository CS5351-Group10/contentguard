"""CI gate 2e — structural checks (TD-4, REQ-INV-001).

Closes the structural gaps that gate 5's ``test_invariants.py`` does not cover, and only
those gaps:

- **module-set vs ADR-001** — every package directory under ``src/contentguard/`` must be an
  element declared by ADR-001. An undeclared directory is an architecture change, so it is a
  **FAIL**. A declared-but-absent element (today ``analysis/`` and ``api/``) is **INFO**,
  never a failure.
- **element-to-element import cycles** — structural rule 5 forbids cycles; an A→…→A chain of
  ``contentguard`` element imports is a **FAIL** naming the cycle.
- **frozen-path guard** — a PR touching ``.opencode/**`` or ``.agent/**`` is a **FAIL**
  (human-only paths). ``transcripts/**`` is deliberately **not** frozen: human-authored
  transcripts are committed legitimately (PR #62).
- **docs-only pass** — a PR touching only ``docs/`` passes with no source scan.

Why this gate does **not** re-run the INV-1 enforcement scan or the dependency-direction
check: those already run in gate 5 via ``test/offline/test_invariants.py`` (see
``docs/code-governance/structural-constraints.md`` §"Enforcement status"). Re-implementing
them here would duplicate a scanner, and importing them from a ``test/`` module would invert
the dependency (a production gate depending on a test). "Reuse, not duplicate" is satisfied
by not running them a second time; issue #66 Revision 2 records this scope.

The element set is a hardcoded constant citing ADR-001, and the scan root is injectable so
fixture trees never touch the real ``src/``. Pure stdlib (``ast``, ``pathlib``); no new
dependency.

Exit 0 = pass, 1 = fail (blocking). ``--offline`` / no event context = skip, matching the
other gates. In a PR event the ``GITHUB_TOKEN`` is always present; its absence is an anomaly,
so this gate **fails closed** with an actionable message rather than silently skipping.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pr_files import changed_files, event_payload, pull_request

# The ADR-001 element set. Source: docs/architecture/adr/001-grounded-advisory-
# transactional-policy.md and architecture-blueprint.md §Components and dependencies,
# mirrored by AGENTS.md §5. Adding, renaming or splitting an element requires a new
# architecture decision — not a quiet directory under src/contentguard/.
ADR001_ELEMENTS: frozenset[str] = frozenset(
    {"analysis", "policy", "escalation", "audit", "api"}
)

# Agent-frozen prefixes (AGENTS.md §4). Narrowed on purpose to these two trees: a code
# scan cannot see authorship, but an agent PR touching these is always a violation.
# ``transcripts/**`` is intentionally excluded — human transcripts are committed there.
FROZEN_PREFIXES: tuple[str, ...] = (".opencode/", ".agent/")

DEFAULT_SRC = Path(__file__).resolve().parents[1] / "src"


def declared_elements() -> frozenset[str]:
    """Return the ADR-001 element set (the only allowed module names)."""
    return ADR001_ELEMENTS


def element_package_dirs(contentguard_dir: Path) -> dict[str, Path]:
    """Map element name → directory for immediate package children of ``contentguard/``.

    A directory qualifies only if it is a real package (contains ``__init__.py``).
    ``__pycache__`` (and any non-package directory) is ignored — gate 5 runs pytest before
    this gate, so cache directories exist on the runner.
    """
    packages: dict[str, Path] = {}
    for child in sorted(contentguard_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name == "__pycache__":
            continue
        if not (child / "__init__.py").is_file():
            continue
        packages[child.name] = child
    return packages


def unknown_element_findings(contentguard_dir: Path, elements: frozenset[str] = ADR001_ELEMENTS) -> list[str]:
    """FAIL lines for package directories that are not ADR-001 elements."""
    findings: list[str] = []
    for name in element_package_dirs(contentguard_dir):
        if name not in elements:
            findings.append(
                f"src/contentguard/{name}/ is not an ADR-001 element. Add the element "
                "through an architecture decision (ADR-001) or rename/remove the directory; "
                "undeclared modules are not allowed (structural rule 1)."
            )
    return findings


def missing_element_info(contentguard_dir: Path, elements: frozenset[str] = ADR001_ELEMENTS) -> list[str]:
    """INFO lines for declared elements that have not landed yet (never failures)."""
    present = set(element_package_dirs(contentguard_dir))
    return [
        f"INFO: declared element '{name}' is absent under src/contentguard/ (not landed yet)"
        for name in sorted(elements - present)
    ]


def _module_imports_contentguard(file_rel: Path, tree: ast.AST) -> set[str]:
    """Fully-qualified ``contentguard`` modules imported by a parsed file."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("contentguard"):
                    found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            if module and module.startswith("contentguard"):
                found.add(module)
    return found


def element_import_graph(contentguard_dir: Path) -> dict[str, set[str]]:
    """Build element → set(imported elements) from imports across ``contentguard/``.

    Only edges between distinct declared elements are kept; imports of a module within the
    same element are ignored. Used by :func:`cycle_findings`.
    """
    elements = set(element_package_dirs(contentguard_dir))
    graph: dict[str, set[str]] = {name: set() for name in elements}
    for name, pkg in element_package_dirs(contentguard_dir).items():
        for path in sorted(pkg.rglob("*.py")):
            rel = path.relative_to(pkg.parent.parent)  # e.g. contentguard/policy/x.py
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for imported in _module_imports_contentguard(rel, tree):
                parts = imported.split(".")
                if len(parts) >= 2 and parts[0] == "contentguard":
                    target = parts[1]
                    if target in elements and target != name:
                        graph[name].add(target)
    return graph


def _reachable(start: str, graph: dict[str, set[str]]) -> list[list[str]]:
    """All simple cycles from ``start`` back to itself (path lists, start included)."""
    cycles: list[list[str]] = []

    def walk(node: str, path: list[str]) -> None:
        for nxt in sorted(graph.get(node, set())):
            if nxt == start and len(path) >= 2:
                cycles.append(path + [start])
            elif nxt not in path:
                walk(nxt, path + [nxt])

    walk(start, [start])
    return cycles


def cycle_findings(graph: dict[str, set[str]]) -> list[str]:
    """FAIL lines for element-to-element import cycles (structural rule 5)."""
    findings: list[str] = []
    seen: set[frozenset[str]] = set()
    for start in sorted(graph):
        for cycle in _reachable(start, graph):
            key = frozenset(cycle)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                "import cycle between elements: "
                + " -> ".join(cycle)
                + " (structural rule 5 forbids element cycles)"
            )
    return findings


def frozen_hits(files: list[str], prefixes: tuple[str, ...] = FROZEN_PREFIXES) -> list[str]:
    """Changed files that fall under an agent-frozen prefix."""
    return [f for f in files if f.startswith(prefixes)]


def check_source(src_dir: Path) -> tuple[list[str], list[str]]:
    """Run the source-tree structural checks against ``src_dir/contentguard``.

    ``src_dir`` is the directory that contains ``contentguard/`` (the repository ``src/``
    or an equivalent fixture directory). Returns ``(failures, infos)``: failures are
    blocking, infos are informational.
    """
    contentguard_dir = src_dir / "contentguard"
    if not contentguard_dir.is_dir():
        return [f"source tree not found: {contentguard_dir}"], []
    failures = unknown_element_findings(contentguard_dir)
    failures += cycle_findings(element_import_graph(contentguard_dir))
    infos = missing_element_info(contentguard_dir)
    return failures, infos


def _docs_only(files: list[str]) -> bool:
    """True when every changed path is under ``docs/``."""
    return bool(files) and all(f.startswith("docs/") for f in files)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--offline" in args:
        print("GATE 2E SKIP: offline run")
        return 0
    event = event_payload()
    if event is None:
        print("GATE 2E SKIP: no event context (local run)")
        return 0

    pr = pull_request(event)
    if pr is None:
        failures, infos = check_source(DEFAULT_SRC)
        for info in infos:
            print(f"GATE 2E {info}")
        if failures:
            for finding in failures:
                print(f"GATE 2E FAIL: {finding}")
            return 1
        print("GATE 2E PASS: push event — structural checks clean")
        return 0

    # PR event: a token is always present. Its absence is an anomaly (the #61 blind
    # spot), so fail closed with an actionable message — never silently skip.
    token = (os.environ.get("GITHUB_TOKEN") or "").strip()
    if not token:
        # Still run the source-tree part so every finding surfaces at once.
        failures, _infos = check_source(DEFAULT_SRC)
        for finding in failures:
            print(f"GATE 2E FAIL: {finding}")
        print(
            "GATE 2E FAIL: cannot list changed files: the step is missing GITHUB_TOKEN. "
            "Pass it via `env: GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` on the Gate 2e "
            "step in .github/workflows/ci.yml."
        )
        return 1

    repo = str(pr["base"]["repo"]["full_name"])
    number = int(pr["number"])
    try:
        files = changed_files(repo, number, token)
    except RuntimeError as exc:
        print(f"GATE 2E FAIL: could not list PR files — {exc}")
        return 1

    if _docs_only(files):
        print("GATE 2E PASS: docs-only PR (no source scan)")
        return 0

    failures, infos = check_source(DEFAULT_SRC)
    failures += [
        f"agent-frozen path changed: {f} (.opencode/** and .agent/** are human-only)"
        for f in frozen_hits(files)
    ]
    for info in infos:
        print(f"GATE 2E {info}")
    if failures:
        for finding in failures:
            print(f"GATE 2E FAIL: {finding}")
        return 1
    print(f"GATE 2E PASS: {len(files)} changed file(s); structural checks clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
