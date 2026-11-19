"""Structural invariants & forgery tests (REQ-INV-001, REQ-INV-004) — deterministic.

Verifies REQ-INV-001: only ``contentguard.policy`` may import or reference the enforcement
authority (``policy.enforcement`` / ``EnforcementAuthority``); every other module reaches
enforcement only through the public ``PolicyEngine.evaluate*`` API. The checker is an AST
scan (never a text scan, so docstrings and comments cannot cause false positives), proven
in both directions: it passes on the real ``src/`` tree and fails on the deliberate
``fixtures/forbidden_enforcement/rogue_module.py.txt`` fixture.

Also verifies:
- REQ-INV-001 (dependency direction): ``audit``/``escalation`` do not import ``policy``;
  ``policy`` does not import ``analysis``; the audit/escalation mutation repositories are
  not imported outside ``policy`` (structural rule 5 in ``structural-constraints.md``).
- REQ-INV-001 (forgery): ``AdvisoryResult.from_payload`` rejects privileged action fields
  and accepts ``role`` only as the LLM role, never as actor authority.
- REQ-INV-004: audit's local value sets stay in lockstep with the policy enums (no drift
  across the no-import boundary).
- REQ-INV-001 (positive control): an engine-authorized decision commits successfully.

No network, no model access; only ``tmp_path`` SQLite for the positive control.
"""

from __future__ import annotations

import ast
import shutil
from pathlib import Path

import pytest
from conftest import make_case, make_snapshot

from contentguard.audit.contracts import (
    VALID_FAILURE_CODES,
    VALID_OUTCOMES,
    VALID_VERDICTS,
)
from contentguard.policy.contracts import (
    ADVISORY_ROLES,
    AdvisoryResult,
    CommitStatus,
    FailureCode,
    Outcome,
    ReplayKey,
    Severity,
    Verdict,
)
from contentguard.policy.engine import PolicyEngine
from contentguard.policy.store import SqliteStore

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "forbidden_enforcement"

_ENFORCEMENT_MODULE = "contentguard.policy.enforcement"
_POLICY_MODULE = "contentguard.policy"
_AUTHORITY_SYMBOL = "EnforcementAuthority"


def _in_policy_package(rel: Path) -> bool:
    """True when a path (relative to ``src/``) is under ``contentguard/policy/``."""
    parts = rel.parts
    return len(parts) >= 3 and parts[0] == "contentguard" and parts[1] == "policy"


def _resolve_relative(module: str | None, level: int, file_rel: Path) -> str | None:
    """Resolve an ``ImportFrom`` module against its file package for ``level > 0``."""
    if level == 0:
        return module
    pkg_parts = list(file_rel.parts[:-1])  # drop the file name → package
    # ``src/contentguard/x.py`` has package ["contentguard"]; level 1 stays in that pkg.
    drop = level - 1
    if drop:
        if drop > len(pkg_parts):
            return module  # unresolvable; fall back to the raw module name
        pkg_parts = pkg_parts[:-drop]
    base = ".".join(pkg_parts)
    if module:
        return f"{base}.{module}" if base else module
    return base or None


def _string_constants(node: ast.AST) -> list[str]:
    """Constant string values supplied to an ``__import__``/``import_module`` call."""
    out: list[str] = []
    for arg in getattr(node, "args", []):
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            out.append(arg.value)
    return out


def _references_enforcement(tree: ast.AST, file_rel: Path) -> list[str]:
    """Return the reasons a parsed module references the enforcement authority."""
    reasons: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == _ENFORCEMENT_MODULE or alias.name.startswith(
                    _ENFORCEMENT_MODULE + "."
                ):
                    reasons.append(f"import {alias.name}")
                if alias.asname == _AUTHORITY_SYMBOL:
                    reasons.append(f"import ... as {_AUTHORITY_SYMBOL}")
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_relative(node.module, node.level, file_rel)
            for alias in node.names:
                if alias.name == _AUTHORITY_SYMBOL:
                    reasons.append(f"from {resolved} import {_AUTHORITY_SYMBOL}")
                if resolved == _POLICY_MODULE and alias.name == "enforcement":
                    reasons.append(f"from {_POLICY_MODULE} import enforcement")
                if resolved == _ENFORCEMENT_MODULE:
                    reasons.append(f"from {_ENFORCEMENT_MODULE} import {alias.name}")
                if resolved == _POLICY_MODULE and alias.name == _AUTHORITY_SYMBOL:
                    reasons.append(
                        f"from {_POLICY_MODULE} import {_AUTHORITY_SYMBOL}"
                    )
        elif isinstance(node, ast.Attribute):
            if node.attr == _AUTHORITY_SYMBOL:
                reasons.append(f"attribute .{_AUTHORITY_SYMBOL}")
            # ``contentguard.policy.enforcement`` dotted attribute chain.
            dotted = _dotted_name(node)
            if dotted is not None and dotted == _ENFORCEMENT_MODULE:
                reasons.append(f"attribute {dotted}")
        elif isinstance(node, ast.Name):
            if node.id == _AUTHORITY_SYMBOL:
                reasons.append(f"name {_AUTHORITY_SYMBOL}")
        elif isinstance(node, ast.Call):
            func = node.func
            fname = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if fname in {"__import__", "import_module"}:
                for value in _string_constants(node):
                    if value == _ENFORCEMENT_MODULE or value.startswith(
                        _ENFORCEMENT_MODULE + "."
                    ):
                        reasons.append(f"{fname}({value!r})")
    return reasons


def _dotted_name(node: ast.AST) -> str | None:
    """Render an ``a.b.c`` Name/Attribute chain, or None if it is not one."""
    parts: list[str] = []
    cur: ast.AST | None = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def find_enforcement_violations(root: Path) -> list[str]:
    """AST-scan ``root`` for references to enforcement outside ``contentguard.policy``.

    Returns a sorted list of ``"<relpath>: <reason>"`` entries. Files under
    ``contentguard/policy/`` are the authority's own package and are skipped.
    """
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if _in_policy_package(rel):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for reason in sorted(set(_references_enforcement(tree, rel))):
            violations.append(f"{rel.as_posix()}: {reason}")
    return violations


def test_enforcement_only_from_policy() -> None:
    """Verifies REQ-INV-001: no module outside ``contentguard.policy`` references the
    enforcement authority by any import or attribute form."""
    violations = find_enforcement_violations(SRC)
    assert violations == [], violations


def test_forbidden_call_structural(tmp_path: Path) -> None:
    """Verifies REQ-INV-001 (negative): the deliberate fixture is detected by the same
    checker that passes on ``src/``, covering module imports, ``from ... import
    enforcement``, ``from ...enforcement import X``, attribute access, literal
    ``__import__``/``importlib.import_module`` strings and the
    ``from contentguard.policy import EnforcementAuthority`` re-export bypass.

    The fixture is stored as ``.py.txt`` (never collected); it is copied to a temporary
    ``.py`` file so the AST walk sees it."""
    fixture = FIXTURES / "rogue_module.py.txt"
    assert fixture.is_file()
    staging = tmp_path / "contentguard_rogue" / "evil.py"
    staging.parent.mkdir(parents=True)
    shutil.copyfile(fixture, staging)

    violations = find_enforcement_violations(tmp_path)
    assert violations, "the checker failed to flag the deliberate violation fixture"
    joined = "\n".join(violations)

    # Each of the seven fixture forms must be independently detected.
    required_forms = {
        "module import": f"import {_ENFORCEMENT_MODULE}",
        "aliased module / attribute access": f".{_AUTHORITY_SYMBOL}",
        "from policy import enforcement": f"from {_POLICY_MODULE} import enforcement",
        "from enforcement import X": f"from {_ENFORCEMENT_MODULE} import",
        "re-export EnforcementAuthority": (
            f"from {_POLICY_MODULE} import {_AUTHORITY_SYMBOL}"
        ),
        "literal __import__": f"__import__('{_ENFORCEMENT_MODULE}')",
        "literal import_module": f"import_module('{_ENFORCEMENT_MODULE}')",
    }
    missing = [name for name, marker in required_forms.items() if marker not in joined]
    assert not missing, f"checker missed fixture forms: {missing}\nviolations:\n{joined}"


def _imported_policy_modules(file_rel: Path, tree: ast.AST) -> set[str]:
    """Fully-qualified ``contentguard.*`` modules imported by a parsed file."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("contentguard"):
                    found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_relative(node.module, node.level, file_rel)
            if resolved and resolved.startswith("contentguard"):
                found.add(resolved)
                for alias in node.names:
                    found.add(f"{resolved}.{alias.name}")
    return found


def _dependency_direction_violations(root: Path) -> list[str]:
    """AST-scan ``root`` for dependency-direction violations (structural rule 5).

    Covers the named prohibitions: ``audit``/``escalation`` must not import ``policy``;
    ``policy`` must not import ``analysis``; ``analysis`` must not import ``policy`` (the
    advisory component never reaches the authoritative boundary); and the audit/escalation
    mutation repositories are imported only by ``policy`` or their own package.
    """
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = _imported_policy_modules(rel, tree)
        top = rel.parts[1] if len(rel.parts) >= 2 else ""

        if top in {"audit", "escalation"}:
            assert not any(m == "contentguard.policy" or m.startswith(
                "contentguard.policy."
            ) for m in imported), f"{rel.as_posix()} imports policy: {sorted(imported)}"

        if top == "policy":
            assert not any(m == "contentguard.analysis" or m.startswith(
                "contentguard.analysis."
            ) for m in imported), f"{rel.as_posix()} imports analysis: {sorted(imported)}"

        if top == "analysis":
            assert not any(m == "contentguard.policy" or m.startswith(
                "contentguard.policy."
            ) for m in imported), (
                f"{rel.as_posix()} (analysis) imports policy: {sorted(imported)} — the "
                "advisory component must not import the authoritative boundary"
            )

        if top not in {"audit", "escalation", "policy"}:
            for sensitive in ("contentguard.audit.", "contentguard.escalation."):
                offenders = {m for m in imported if m.startswith(sensitive)}
                assert not offenders, (
                    f"{rel.as_posix()} imports a mutation repository port: "
                    f"{sorted(offenders)}"
                )
    return []


def test_dependency_direction() -> None:
    """Verifies REQ-INV-001 / structural rule 5 (dependency direction): ``audit`` and
    ``escalation`` do not import ``policy``; ``policy`` does not import ``analysis``;
    ``analysis`` does not import ``policy``; and the audit/escalation mutation
    repositories are imported only by ``policy`` or their own package (never by an
    adapter/API) — a forward-looking guard for S2."""
    assert _dependency_direction_violations(SRC) == []


def test_analysis_must_not_import_policy(tmp_path: Path) -> None:
    """Verifies REQ-INV-001 (negative): an ``analysis`` module importing ``policy`` is
    flagged by the dependency-direction scan.

    The advisory component must never reach the authoritative boundary. A fixture tree
    ``contentguard/analysis/rogue.py`` importing ``contentguard.policy`` must fail.
    """
    analysis = tmp_path / "contentguard" / "analysis"
    analysis.mkdir(parents=True)
    (analysis / "__init__.py").write_text("", encoding="utf-8")
    (analysis / "rogue.py").write_text(
        "from contentguard.policy import engine\n", encoding="utf-8"
    )
    with pytest.raises(AssertionError) as excinfo:
        _dependency_direction_violations(tmp_path)
    assert "analysis" in str(excinfo.value)
    assert "policy" in str(excinfo.value)


def _valid_advisory_payload() -> dict[str, object]:
    return {
        "role": "initial_review",
        "verdict": Verdict.ALLOW.value,
        "severity": Severity.LOW.value,
        "rationale": "model rationale",
        "citations": ("clause-001",),
        "prompt_version": "prompt-v1",
        "model_id": "model-x",
        "model_version": "2026-11",
        "usage": {"input_tokens": 10, "output_tokens": 5, "usage_unknown": False},
    }


@pytest.mark.parametrize(
    "forbidden_key",
    ["action", "outcome", "enforcement", "actor", "privileges", "tools"],
)
def test_forged_advisory_action(forbidden_key: str) -> None:
    """Verifies REQ-INV-001 (forgery): ``AdvisoryResult.from_payload`` rejects a privileged
    action field; the model output is data, never an enforcement command."""
    payload = _valid_advisory_payload()
    payload[forbidden_key] = "grant-admin"
    with pytest.raises(ValueError):
        AdvisoryResult.from_payload(payload)


def test_forged_advisory_unknown_key_rejected() -> None:
    """Verifies REQ-INV-001 (forgery): an unknown advisory key is rejected, not ignored."""
    payload = _valid_advisory_payload()
    payload["surprise"] = True
    with pytest.raises(ValueError):
        AdvisoryResult.from_payload(payload)


@pytest.mark.parametrize("bad_role", ["moderator", "policy", "admin", "submitter"])
def test_advisory_role_is_llm_role_only(bad_role: str) -> None:
    """Verifies REQ-INV-001 (forgery): ``role`` is the LLM role, accepted only as
    ``initial_review``/``reconsideration`` — never an actor privilege."""
    payload = _valid_advisory_payload()
    payload["role"] = bad_role
    assert bad_role not in ADVISORY_ROLES
    with pytest.raises(ValueError):
        AdvisoryResult.from_payload(payload)


def test_audit_value_sets_match_policy() -> None:
    """Verifies REQ-INV-004: audit's local value sets equal the policy enums, so the
    no-import duplication (structural rule 5) cannot drift."""
    assert VALID_OUTCOMES == {o.value for o in Outcome}
    assert VALID_VERDICTS == {v.value for v in Verdict}
    assert VALID_FAILURE_CODES == {c.value for c in FailureCode}


@pytest.fixture()
def store(tmp_path: Path) -> SqliteStore:
    """A fresh file-backed SQLite store with schemas created (positive-control DB)."""
    sqlite_store = SqliteStore(str(tmp_path / "cases.db"))
    sqlite_store.initialize()
    return sqlite_store


def test_valid_engine_authorized_action_succeeds(store: SqliteStore) -> None:
    """Verifies REQ-INV-001 (positive control): a decision returned by the engine commits
    successfully, producing exactly one audit record.

    This proves the structural restriction (nothing outside ``policy`` may touch
    enforcement) still leaves a working authorized path."""
    advisory = AdvisoryResult.from_payload(_valid_advisory_payload())
    case = make_case(advisory=advisory)
    snapshot = make_snapshot()
    with store.transaction() as conn:
        store.activate_snapshot(conn, snapshot)
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO cases (case_id, revision, status, content_hash, "
            "policy_snapshot_id, policy_snapshot_digest, content_text, advisory_verdict, "
            "advisory_severity, advisory_model_id, advisory_model_version, "
            "analysis_failure_code, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                case.case_id, case.revision, case.status.value, case.content_hash,
                case.policy_snapshot_id, case.policy_snapshot_digest, "benign text",
                case.advisory_verdict.value if case.advisory_verdict else None,
                case.advisory_severity.value if case.advisory_severity else None,
                case.advisory_model_id, case.advisory_model_version, None,
                "2026-11-18T00:00:00+00:00",
            ),
        )
    engine = PolicyEngine(snapshot)
    result = engine.evaluate_and_commit(
        store=store,
        case=case,
        content_text="benign text",
        advisory=None,
        expected_revision=case.revision,
        replay_key=ReplayKey(actor_id="submitter-1", idempotency_key="idem-inv-pos"),
    )
    assert result.status is CommitStatus.COMMITTED
    assert result.audit_id is not None
    with store.read_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0]
    assert int(count) == 1
