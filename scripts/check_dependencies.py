"""CI gate 2 (Tier 0) — dependency manifest and resolution check (TD-8).

The workflow installs the toolchain **from** ``requirements.txt`` (single source of
truth), so this check guards two failure modes:

1. the manifest is missing or has stopped declaring a tool CI relies on, and
2. the installed environment has an inconsistent dependency set (``pip check``).

Run styles:
  - default: manifest checks + ``pip check`` (needs a real environment);
  - ``--offline``: manifest checks only, never shells out — used by the offline tests.

Exit 0 = pass, 1 = fail (blocking). Failures print ``GATE 2 FAIL:`` with a diagnosis,
matching the house style of the other gate scripts (actionable message, no traceback).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "requirements.txt"

# The toolchain the workflow needs; keep in lockstep with requirements.txt. pyyaml is the
# distribution name for the ``yaml`` import (jsonschema likewise imports as ``jsonschema``).
REQUIRED_DISTS = ("pytest", "ruff", "mypy", "pyyaml", "jsonschema")

_REQUIREMENT_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*(\[[^\]]*\])?\s*([<>=!~].*)?$")


def declared_distributions(text: str) -> set[str]:
    """Normalized distribution names declared in a requirements file (``-r`` lines skipped)."""
    names: set[str] = set()
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = _REQUIREMENT_RE.match(line)
        if match is not None:
            names.add(match.group(1).lower().replace("_", "-"))
    return names


def check_manifest(path: Path = MANIFEST) -> list[str]:
    """Return actionable error strings for the manifest; empty means healthy."""
    if not path.exists():
        return [
            (
                f"{path.name} is missing. Declare the CI toolchain "
                f"({', '.join(REQUIRED_DISTS)}) in {path.name} (TD-8)."
            )
        ]
    declared = declared_distributions(path.read_text(encoding="utf-8"))
    missing = [dist for dist in REQUIRED_DISTS if dist.lower() not in declared]
    if missing:
        return [
            (
                f"{path.name} does not declare required tool(s): {', '.join(missing)}. "
                "CI installs from this manifest, so a missing entry silently drops the tool."
            )
        ]
    return []


def run_pip_check(python: str = sys.executable) -> list[str]:
    """Run ``pip check`` and return error strings (empty = consistent).

    Kept separate from ``check_manifest`` so the offline tests never invoke pip.
    """
    try:
        proc = subprocess.run(
            [python, "-m", "pip", "check"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return [f"could not run 'pip check': {exc}"]
    if proc.returncode != 0:
        detail = (proc.stdout + proc.stderr).strip() or "no output"
        return [f"pip check reported inconsistent dependencies:\n{detail}"]
    return []


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    offline = "--offline" in args

    errors = check_manifest(MANIFEST)
    if not errors and not offline:
        errors = run_pip_check()

    if errors:
        for error in errors:
            print(f"GATE 2 FAIL: {error}")
        return 1
    scope = "manifest only (offline)" if offline else "manifest + pip check"
    print(f"GATE 2 PASS: dependency check ({scope})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
