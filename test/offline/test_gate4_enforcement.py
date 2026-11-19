"""Gate-4 enforcement tests: strict blocking + the replay converter (offline, no network).

Verifies REQ-INV-005: a prompt/model change is blocked from merging unless the fixed
semantic-evaluation replay meets the approved release criteria — "missing, incomplete,
stale … replay … block merge". Pays down TD-1 (gate 4 flipped from warn-only to blocking).

These tests drive the real ``scripts/check_semantic_eval.py`` gate and the real
``scripts/record_replay.py`` converter. PR context is injected exactly as the existing
``test_eval_runner.py`` does (synthetic event + monkeypatched ``changed_files``); the
replay artifacts are the shipped fixtures ``test/eval/replay/{good,bad}_prompt.jsonl``.

Nothing here opens a network connection or reads a provider credential, and neither does
the converter under test — that is asserted explicitly.
"""

from __future__ import annotations

import importlib.util
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
GATE_PATH = SCRIPTS / "check_semantic_eval.py"
RECORD_PATH = SCRIPTS / "record_replay.py"
CORPUS_PATH = ROOT / "test" / "eval" / "moderation_eval.jsonl"
REPLAY_DIR = ROOT / "test" / "eval" / "replay"
GOOD_REPLAY = REPLAY_DIR / "good_prompt.jsonl"
BAD_REPLAY = REPLAY_DIR / "bad_prompt.jsonl"

sys.path.insert(0, str(SCRIPTS))


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run_gate(
    monkeypatch: pytest.MonkeyPatch,
    gate: ModuleType,
    *,
    argv: list[str],
    files: list[str],
    replay_path: str | None,
) -> tuple[int, str]:
    """Drive check_semantic_eval.main with PR context and an explicit (or absent) replay."""
    # A developer's shell EVAL_REPLAY must never leak into a gate result.
    monkeypatch.delenv("EVAL_REPLAY", raising=False)
    event = {
        "pull_request": {
            "number": 1,
            "body": "Test-Plan-Approved: #26",
            "base": {"repo": {"full_name": "o/r"}},
        }
    }
    monkeypatch.setattr(gate, "event_payload", lambda: event)
    monkeypatch.setattr(gate, "changed_files", lambda *a, **k: files)
    monkeypatch.setattr(gate, "EVAL_SET", CORPUS_PATH)
    monkeypatch.setattr(gate, "EVAL_REPLAY", Path(replay_path) if replay_path else None)
    monkeypatch.setattr(sys, "argv", ["check_semantic_eval.py", *argv])
    buf = StringIO()
    with redirect_stdout(buf):
        code = gate.main()
    return code, buf.getvalue()


# --------------------------------------------------------------- strict: missing replay
def test_strict_no_replay_fails_naming_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-INV-005 / TD-1 *negative*: under --strict a prompt change with NO replay
    artifact must FAIL and the message must name the fix — a replay committed under
    ``test/eval/replay/<tag>.jsonl`` — not just "configure --replay". A prompt change
    with no evidence does not merge, and the gate never defaults to a shipped fixture."""
    gate = _load("gate_g4_no_replay", GATE_PATH)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=["--strict"],
        files=["prompts/prompt_v1.1.yaml"],
        replay_path=None,
    )
    assert code != 0, out
    assert "GATE 4 FAIL" in out
    assert "test/eval/replay/" in out
    assert "<tag>.jsonl" in out
    # Must NOT have silently used a fixture and reported success.
    assert "GATE 4 PASS" not in out


# --------------------------------------------------------- strict: bad replay (regression)
def test_strict_bad_replay_fails_naming_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-INV-005 / TD-1 *negative* (regression guard — already passes at head): the
    deliberately-bad replay fails gate 4 under --strict, the output names the failed
    threshold (a high-severity safety escape), and the step does not pass."""
    gate = _load("gate_g4_bad_replay", GATE_PATH)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=["--strict"],
        files=["prompts/prompt_v1.1.yaml"],
        replay_path=str(BAD_REPLAY),
    )
    assert code != 0, out
    assert "GATE 4 FAIL" in out
    assert "threshold" in out.lower()
    assert "safety escape" in out.lower()


# ------------------------------------------------------------- strict: good replay passes
def test_strict_good_replay_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-INV-005: the shipped good replay clears the approved thresholds under --strict
    (agreement >= 0.80 with zero safety escapes), so gate 4 PASSes and prints the table."""
    gate = _load("gate_g4_good_replay", GATE_PATH)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=["--strict"],
        files=["prompts/prompt_v1.1.yaml"],
        replay_path=str(GOOD_REPLAY),
    )
    assert code == 0, out
    assert "GATE 4 PASS" in out
    assert "recorded replay" in out.lower()
    assert "agreement" in out.lower()


# --------------------------------------------------------------- non-strict: warn (guard)
def test_non_strict_keeps_warn_behaviour(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-INV-005 / TD-1 (regression guard): without --strict, a prompt change with no
    replay still reports CANNOT EVALUATE and exits 0 as a warning — it must never claim
    PASS. This protects the documented warn-only fallback semantics."""
    gate = _load("gate_g4_warn", GATE_PATH)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=[],
        files=["prompts/prompt_v1.1.yaml"],
        replay_path=None,
    )
    assert code == 0, out
    assert "CANNOT EVALUATE" in out.upper()
    assert "WARNING" in out.upper()
    assert "GATE 4 PASS" not in out


# ------------------------------------------------------------- docs-only PR unaffected
def test_strict_docs_only_pr_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-INV-005: under --strict a PR that changes no prompt/model path passes gate 4
    (the gate is not applicable to docs-only changes); no replay is required."""
    gate = _load("gate_g4_docs_only", GATE_PATH)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=["--strict"],
        files=["docs/code-governance/verification-constraints.md"],
        replay_path=None,
    )
    assert code == 0, out
    assert "no prompt/model change" in out.lower()


# ---------------------------------------------------------- converter: offline by design
def _responses(tmp_path: Path, rows: list[dict[str, Any]]) -> Path:
    import json

    path = tmp_path / "responses.jsonl"
    path.write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    return path


def test_converter_rejects_bad_rows_and_duplicates(tmp_path: Path) -> None:
    """REQ-INV-005 / TD-1 *negative*: the converter rejects a row missing eval_id/verdict,
    rejects a duplicate eval_id, and rejects an id not present in the corpus."""
    converter = _load("converter_neg", RECORD_PATH)

    bad = _responses(tmp_path, [{"eval_id": "EV-0001"}])  # no verdict
    out = tmp_path / "out.jsonl"
    code = converter.main(["--from", str(bad), "--out", str(out)])
    assert code != 0

    dup = _responses(
        tmp_path,
        [{"eval_id": "EV-0001", "verdict": "block"}, {"eval_id": "EV-0001", "verdict": "allow"}],
    )
    code = converter.main(["--from", str(dup), "--out", str(out)])
    assert code != 0

    unknown = _responses(tmp_path, [{"eval_id": "EV-9999", "verdict": "block"}])
    code = converter.main(["--from", str(unknown), "--out", str(out)])
    assert code != 0
    # A failed conversion must not write a partial artifact.
    assert not out.exists()


def test_converter_reports_uncovered_corpus_ids(tmp_path: Path) -> None:
    """REQ-INV-005 / TD-1 *negative*: a responses file that covers only part of the corpus
    is refused, naming how many corpus eval_ids are uncovered (an incomplete replay would
    otherwise look like evidence)."""
    converter = _load("converter_uncovered", RECORD_PATH)
    partial = _responses(tmp_path, [{"eval_id": "EV-0001", "verdict": "block"}])
    out = tmp_path / "out.jsonl"
    buf = StringIO()
    with redirect_stdout(buf):
        code = converter.main(["--from", str(partial), "--out", str(out)])
    assert code != 0
    assert "uncovered" in buf.getvalue().lower()
    assert not out.exists()


def test_converter_happy_path_writes_replay(tmp_path: Path) -> None:
    """REQ-INV-005: a complete, valid responses file converts to a replay artifact that the
    runner can load — every corpus eval_id covered once with a valid verdict."""
    converter = _load("converter_ok", RECORD_PATH)
    runner = _load("converter_runner", SCRIPTS / "eval_runner.py")
    replay_map = runner.load_replay(GOOD_REPLAY)
    rows = [{"eval_id": k, "verdict": v} for k, v in replay_map.items()]
    src = _responses(tmp_path, rows)
    out = tmp_path / "replay_out.jsonl"
    code = converter.main(["--from", str(src), "--out", str(out)])
    assert code == 0
    assert out.exists()
    assert runner.load_replay(out) == replay_map


def test_converter_never_touches_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """REQ-INV-005 / TD-1 *negative*: the converter is a pure file transform — it must not
    open a network connection at all, even when invoked under CI env vars. Any attempt to
    create a socket fails the test, proving there is no credential/network surface."""
    import socket

    def _boom(*a: Any, **k: Any) -> Any:  # pragma: no cover - only runs on violation
        raise AssertionError("record_replay must never open a network connection")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    converter = _load("converter_nonnetwork", RECORD_PATH)
    runner = _load("converter_nonnetwork_runner", SCRIPTS / "eval_runner.py")
    replay_map = runner.load_replay(GOOD_REPLAY)
    src = _responses(
        tmp_path, [{"eval_id": k, "verdict": v} for k, v in replay_map.items()]
    )
    out = tmp_path / "out.jsonl"
    assert converter.main(["--from", str(src), "--out", str(out)]) == 0


# --------------------------------------------------- threshold/registry drift guard
def test_threshold_matches_registry() -> None:
    """REQ-QUA-003: the machine agreement threshold must equal the registry's REQ-QUA-003
    "overall agreement >= N%" release target. A hard-coded duplicate is exactly how a gate
    ends up enforcing yesterday's number (it read 0.80 while the registry said 85%)."""
    import re

    registry = (ROOT / "docs" / "req" / "requirements.yaml").read_text(encoding="utf-8")
    match = re.search(r"overall agreement >=?\s*(\d+)%", registry)
    assert match is not None, "REQ-QUA-003 agreement target not found in the registry"
    registry_pct = int(match.group(1))

    runner = _load("eval_runner_drift", SCRIPTS / "eval_runner.py")
    assert round(runner.AGREEMENT_MIN * 100) == registry_pct, (
        f"eval_runner.AGREEMENT_MIN ({runner.AGREEMENT_MIN:.2f}) != REQ-QUA-003 "
        f"registry target ({registry_pct}%); update the machine copy to match the registry"
    )
