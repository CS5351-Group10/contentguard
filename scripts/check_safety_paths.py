"""CI gate 2 (Tier 0) — safety-path tier for PRs (partial TD-4).

When a PR touches a safety-relevant path, this gate requires the PR body to reference an
architecture decision (``ADR-<n>``) or an invariant ID (``REQ-INV-<nnn>`` / ``INV-<n>``).
That mirrors ``docs/code-governance/structural-constraints.md`` rule 7 and
``.agent/rules.md`` C4: a safety-critical change needs an architecture decision recorded.

What this gate genuinely checks today: the ADR/invariant reference requirement above.
The remaining "second tier" checks the constraints document names — contract diffing
against interface-contracts.md, API-surface diffing, and the INV-1 structural call-graph
fitness function — DO NOT EXIST YET and are written below solely as TODO(TD-4) markers.
They must never be step placeholders that print PASS without inspecting anything.

``SAFETY_PATHS`` is an explicit reviewed constant, not a runtime parse of invariants.md
(a gate whose behaviour depends on prose regexes drifts silently). The drift guard lives
in test/offline/test_gate2_safety.py: if invariants.md names a new path, that test fails
and a human extends the constant or records it in EXCLUDED with a reason.

Exit 0 = pass/skip, 1 = fail (blocking). ``--offline`` / no event context = skip, matching
gates 1/4/6.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pr_files import changed_files, event_payload, pull_request

# Safety-relevant path prefixes. Grew from repo knowledge, not from parsing prose:
#   - src/contentguard/policy/ is the enforcement surface (INV-1 / REQ-INV-001): the only
#     module allowed to decide and execute enforcement.
#   - test/eval/ holds the labelled evaluation corpus: silently editing it changes what
#     "gate 4 passes" means — the evaluation-debt blind spot (TD-1).
SAFETY_PATHS = ("src/contentguard/policy/", "test/eval/")

# invariants.md-named paths that are intentionally NOT safety-gated, with the reason.
# The invariant-register drift test requires every path named there to appear here or in
# SAFETY_PATHS.
EXCLUDED = {
    "docs/req/requirements.yaml": "human-owned registry; gate 3 validates it",
    "docs/bug-diary.md": "incident log, not an enforcement surface",
    "docs/debt-register.md": "debt tracker, propose-in-PR",
    ".agent/rules.md": "human-owned covenant; changes go through human review",
    "scripts/check_semantic_eval.py": "gate 4 script itself; behaviour gated by its tests",
    "prompts/prompt_vN.yaml": "prompt changes are already gated by gate 4 (INV-5)",
}

ADR_OR_INVARIANT = re.compile(r"\b(ADR-\d+|REQ-INV-\d{3}|INV-\d)\b")

# TODO(TD-4): contract diff — compare changed call sites against
#   docs/architecture/interface-contracts.md once the contracts have executable form.
# TODO(TD-4): API-surface diff — flag changed public signatures under src/contentguard/api/.
# TODO(TD-4): structural call-graph — assert enforcement entry points are reachable only
#   from src/contentguard/policy/ (INV-1). Needs src/ to land first (PR #41).


def safety_hits(files: list[str], paths: tuple[str, ...] = SAFETY_PATHS) -> list[str]:
    """Changed files that fall under a safety path prefix."""
    return [f for f in files if f.startswith(paths)]


def has_decision_reference(body: str) -> bool:
    """True if the PR body cites an ADR or an invariant ID."""
    return ADR_OR_INVARIANT.search(body) is not None


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--offline" in args:
        print("GATE 2 SAFETY SKIP: offline run")
        return 0
    event = event_payload()
    if event is None:
        print("GATE 2 SAFETY SKIP: no event context (local run)")
        return 0
    pr = pull_request(event)
    if pr is None:
        print("GATE 2 SAFETY PASS: push event — safety tier applies to pull requests")
        return 0

    repo = str(pr["base"]["repo"]["full_name"])
    number = int(pr["number"])
    try:
        files = changed_files(repo, number, os.environ.get("GITHUB_TOKEN", ""))
    except RuntimeError as exc:
        print(f"GATE 2 SAFETY FAIL: could not list PR files — {exc}")
        return 1

    hits = safety_hits(files)
    if not hits:
        print("GATE 2 SAFETY PASS: no safety-relevant path in this PR")
        return 0

    body = pr.get("body") or ""
    if not has_decision_reference(body):
        print(
            "GATE 2 SAFETY FAIL: this PR touches safety-relevant path(s) "
            f"({', '.join(hits)}) but the description cites no architecture decision. "
            "Reference the governing ADR (e.g. ADR-001) or invariant ID (e.g. REQ-INV-001)."
        )
        # TODO(TD-4): add contract diff / API-surface diff / call-graph checks here.
        return 1

    print(f"GATE 2 SAFETY PASS: safety path(s) {', '.join(hits)} reference an ADR/invariant")
    return 0


if __name__ == "__main__":
    sys.exit(main())
