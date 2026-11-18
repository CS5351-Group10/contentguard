"""Gate-4 semantic-evaluation replay tests (deterministic, offline).

Verifies REQ-INV-005 (must, zero-tolerance): a prompt/model change is blocked unless
the fixed semantic-evaluation replay meets the approved release criteria. Also verifies
REQ-QUA-003 (should): agreement and false-positive/false-negative results reported by
policy category and context slice with explicit denominators.

These tests drive ``scripts/eval_runner.py`` and the gate wrapper
``scripts/check_semantic_eval.py`` directly. They never depend on
``test/eval/moderation_eval.jsonl`` being present: when that file exists (PR #37 landed)
the coverage test uses it, otherwise the test synthesizes an equivalent corpus so the
derivation contract is exercised on this branch too.

All work is offline: PR context and the GitHub file list are monkeypatched, and the
replay artifacts are the shipped fixtures ``test/eval/replay/{good,bad}_prompt.jsonl``
(FIXTURES, not recorded model output — see each file's header).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
RUNNER_PATH = SCRIPTS / "eval_runner.py"
GATE_PATH = SCRIPTS / "check_semantic_eval.py"
POLICY_PATH = ROOT / "test" / "eval" / "expectation_policy.yaml"
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


# --------------------------------------------------------------------------- helpers
def _sha(text: object) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _jigsaw(
    eval_id: str,
    labels: dict[str, int],
    *,
    stratum: str,
    text: str | None = None,
    **over: Any,
) -> dict[str, Any]:
    base = {
        "eval_id": eval_id,
        "source": "jigsaw",
        "source_split": None,
        "source_language": "en",
        "text": text if text is not None else f"jigsaw text {eval_id}",
        "label_scheme": "jigsaw-six-independent-binary-v1",
        "labels": {
            "toxic": 0,
            "severe_toxic": 0,
            "obscene": 0,
            "threat": 0,
            "insult": 0,
            "identity_hate": 0,
            **labels,
        },
        "topic": None,
        "selection_stratum": stratum,
        "selection_seed": 5351,
    }
    base["text_sha256"] = _sha(base["text"])
    base.update(over)
    return base


def _cold(
    eval_id: str,
    label: int,
    fine: int,
    *,
    stratum: str,
    topic: str = "gender",
    text: str | None = None,
    **over: Any,
) -> dict[str, Any]:
    base = {
        "eval_id": eval_id,
        "source": "cold",
        "source_split": "test",
        "source_language": "zh",
        "text": text if text is not None else f"cold text {eval_id}",
        "label_scheme": "cold-test-binary-plus-finegrained-v1",
        "labels": {"label": label, "fine-grained-label": fine},
        "topic": topic,
        "selection_stratum": stratum,
        "selection_seed": 5351,
    }
    base["text_sha256"] = _sha(base["text"])
    base.update(over)
    return base


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    return path


def _synthetic_corpus() -> list[dict[str, Any]]:
    """A 100-row corpus mirroring #37's strata + label distribution (no dependency on it)."""
    rows: list[dict[str, Any]] = []
    n = 0

    def jig(labels: dict[str, int], stratum: str) -> None:
        nonlocal n
        n += 1
        rows.append(_jigsaw(f"EV-{n:04d}", labels, stratum=stratum))

    # jigsaw/idh — identity_hate (high-risk): 12
    for _ in range(12):
        jig({"identity_hate": 1, "toxic": 1, "insult": 1}, "jigsaw/idh")
    # jigsaw/severe-no-idh-no-threat — severe_toxic only path (high-risk): 10
    for _ in range(10):
        jig({"severe_toxic": 1, "toxic": 1, "obscene": 1}, "jigsaw/severe-no-idh-no-threat")
    # jigsaw/threat-no-idh — threat (high-risk): 10
    for _ in range(10):
        jig({"threat": 1, "toxic": 1}, "jigsaw/threat-no-idh")
    # jigsaw/toxic-only — offensive (normal): 12
    for _ in range(12):
        jig({"toxic": 1}, "jigsaw/toxic-only")
    # jigsaw/mixed/toxic-obscene-insult: 7
    for _ in range(7):
        jig({"toxic": 1, "obscene": 1, "insult": 1}, "jigsaw/mixed/toxic-obscene-insult")
    # jigsaw/mixed/toxic-insult: 3
    for _ in range(3):
        jig({"toxic": 1, "insult": 1}, "jigsaw/mixed/toxic-insult")
    # jigsaw/mixed/toxic-obscene: 3
    for _ in range(3):
        jig({"toxic": 1, "obscene": 1}, "jigsaw/mixed/toxic-obscene")
    # jigsaw/single/obscene: 1, insult: 1, obscene-insult: 1
    jig({"obscene": 1}, "jigsaw/single/obscene")
    jig({"insult": 1}, "jigsaw/single/insult")
    jig({"obscene": 1, "insult": 1}, "jigsaw/single/obscene-insult")
    # jigsaw/clean — allow (normal): 20
    for _ in range(20):
        jig({}, "jigsaw/clean")
    # cold safe (label 0): 10
    for i in range(7):
        n += 1
        rows.append(_cold(f"EV-{n:04d}", 0, 0, stratum="cold/label0-fg0/gender", topic="gender"))
    for i in range(3):
        n += 1
        rows.append(_cold(f"EV-{n:04d}", 0, 3, stratum="cold/label0-fg3/gender", topic="gender"))
    # cold attack individual (normal): 3
    for _ in range(3):
        n += 1
        rows.append(_cold(f"EV-{n:04d}", 1, 1, stratum="cold/label1-fg1/gender", topic="gender"))
    # cold attack group (high): 7
    for _ in range(7):
        n += 1
        rows.append(_cold(f"EV-{n:04d}", 1, 2, stratum="cold/label1-fg2/gender", topic="gender"))
    return rows


def _replay_from_expectations(rows: list[dict[str, Any]], runner: ModuleType) -> list[dict]:
    """Build a replay that agrees with the policy for ``rows`` (echoes derived verdicts)."""
    policy = runner.load_policy(POLICY_PATH)
    out = []
    for row in rows:
        match = runner.derive_expectation(row, policy)
        out.append({"eval_id": row["eval_id"], "verdict": match.expected_verdict})
    return out


# --------------------------------------------------------------------------- loading
def test_policy_loads_and_is_first_match() -> None:
    """REQ-INV-005: the human-authored policy declares first-match semantics with rules."""
    runner = _load("eval_runner_policy", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    assert policy["match"] == "first_match"
    assert isinstance(policy["rules"], list) and policy["rules"]


def test_derive_first_match_wins_and_echoes_rule() -> None:
    """REQ-INV-005: an overlapping row (severe_toxic AND toxic) resolves to the first rule."""
    runner = _load("eval_runner_derive", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    row = _jigsaw("EV-X", {"severe_toxic": 1, "toxic": 1}, stratum="jigsaw/idh")
    match = runner.derive_expectation(row, policy)
    assert match.rule_id == "jigsaw-high-risk"
    assert match.expected_verdict == "block"
    assert match.expected_severity == "high"


def test_derive_clean_allow_and_cold_group_high() -> None:
    """REQ-INV-005: clean ⇒ allow/normal; COLD attack-group ⇒ block/high (policy-encoded)."""
    runner = _load("eval_runner_derive2", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    clean = runner.derive_expectation(_jigsaw("EV-C", {}, stratum="jigsaw/clean"), policy)
    assert (clean.expected_verdict, clean.expected_severity) == ("allow", "normal")
    grp = runner.derive_expectation(
        _cold("EV-G", 1, 2, stratum="cold/label1-fg2/gender"), policy
    )
    assert (grp.expected_verdict, grp.expected_severity) == ("block", "high")


def test_policy_covers_corpus_with_39_high_positive(tmp_path: Path) -> None:
    """REQ-INV-005 / REQ-QUA-003: policy covers every row (0 uncovered) and 39 are high."""
    runner = _load("eval_runner_cov", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    if CORPUS_PATH.exists():
        corpus = runner.load_corpus(CORPUS_PATH)
    else:
        corpus = _synthetic_corpus()
    matches = [runner.derive_expectation(row, policy) for row in corpus]
    high = [m for m in matches if m.expected_severity == "high"]
    assert len(corpus) == 100
    assert all(m.rule_id for m in matches)  # no unmatched rows
    assert len(high) == 39


# --------------------------------------------------------------------------- negative: uncovered
def test_uncovered_row_is_hard_failure_even_without_strict(tmp_path: Path) -> None:
    """REQ-INV-005 *negative*: an evaluated row matching no policy rule is exit 1 always."""
    runner = _load("eval_runner_uncovered", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    bogus = _jigsaw(
        "EV-BOGUS", {}, stratum="jigsaw/clean", label_scheme="unknown-scheme-v9"
    )
    corpus_file = _write_jsonl(tmp_path / "corpus.jsonl", [bogus])
    replay_file = _write_jsonl(tmp_path / "replay.jsonl", [{"eval_id": "EV-BOGUS", "verdict": "allow"}])

    code = runner.main(
        ["--corpus", str(corpus_file), "--policy", str(POLICY_PATH), "--replay", str(replay_file)]
    )
    assert code != 0

    with pytest.raises(runner.EvalError):
        runner.derive_expectation(bogus, policy)


# --------------------------------------------------------------------------- metrics
def _tiny_corpus_and_replay(tmp_path: Path, dispositions: list[str]) -> tuple[Path, Path]:
    """10 jigsaw-clean rows (expected allow) + replay dispositions supplied by the caller."""
    rows = [_jigsaw(f"EV-{i:04d}", {}, stratum="jigsaw/clean") for i in range(len(dispositions))]
    corpus = _write_jsonl(tmp_path / "c.jsonl", rows)
    replay = _write_jsonl(
        tmp_path / "r.jsonl",
        [{"eval_id": r["eval_id"], "verdict": d} for r, d in zip(rows, dispositions)],
    )
    return corpus, replay


def test_runner_metrics_exact(tmp_path: Path) -> None:
    """REQ-QUA-003: agreement and false-block are computed exactly on a known fixture."""
    runner = _load("eval_runner_metrics", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    rows = [_jigsaw(f"EV-{i:04d}", {}, stratum="jigsaw/clean") for i in range(10)]
    # 8 agree (allow), 2 false-block (allow expected, blocked) -> agreement 0.8, fb 0.2
    replay = [{"eval_id": r["eval_id"], "verdict": ("allow" if i < 8 else "block")} for i, r in enumerate(rows)]
    report = runner.score(rows, policy, {item["eval_id"]: item["verdict"] for item in replay})
    assert report.agreement == pytest.approx(0.8)
    assert report.false_block_aggregate == pytest.approx(0.2)
    assert report.safety_escapes == []


def test_per_slice_min_denominator_reported_not_failed(tmp_path: Path) -> None:
    """REQ-QUA-003: a <10-row slice with one miss is reported but not hard-failed; a >=10 slice is."""
    runner = _load("eval_runner_slice", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    # 20 allow rows in one slice; 3 in a tiny slice. One miss in tiny (1/3=33%) and one in big.
    rows = [_jigsaw(f"EV-A{i:03d}", {}, stratum="jigsaw/clean") for i in range(20)]
    rows += [_jigsaw(f"EV-B{i:03d}", {}, stratum="jigsaw/clean-rare") for i in range(3)]
    replay: dict[str, str] = {}
    for i, r in enumerate(rows):
        replay[r["eval_id"]] = "allow"
    replay["EV-B000"] = "block"  # tiny slice miss -> high rate, but denom < 10
    replay["EV-A000"] = "block"  # big slice miss -> 1/20 = 5%, under 10%
    report = runner.score(rows, policy, replay)
    fails = runner.check_thresholds(report)
    # tiny slice rate > 10% but denominator 3 -> must NOT be a hard failure
    assert not any("jigsaw/clean-rare" in f for f in fails)
    # big slice 1/20 = 5% -> under threshold -> no slice failure for it either
    assert not any("jigsaw/clean" in f for f in fails)


def test_false_block_aggregate_is_none_without_allow_rows() -> None:
    """REQ-QUA-003: an empty expected-allow denominator yields None (rendered N/A), not 0.00%."""
    runner = _load("eval_runner_fb_na", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    rows = [_jigsaw(f"EV-H{i:03d}", {"identity_hate": 1}, stratum="jigsaw/idh") for i in range(3)]
    replay = {r["eval_id"]: "block" for r in rows}
    report = runner.score(rows, policy, replay)
    assert report.false_block_aggregate is None
    assert "N/A" in runner.format_table(report)
    assert not any("false-block" in f.lower() for f in runner.check_thresholds(report))


def test_big_slice_false_block_over_ten_percent_fails(tmp_path: Path) -> None:
    """REQ-QUA-003 *negative*: a >=10-row slice above 10% false-block fails the gate."""
    runner = _load("eval_runner_slice_neg", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    rows = [_jigsaw(f"EV-A{i:03d}", {}, stratum="jigsaw/clean") for i in range(20)]
    replay = {r["eval_id"]: "allow" for r in rows}
    for r in rows[:5]:  # 5/20 = 25% false-block in a >=10 slice
        replay[r["eval_id"]] = "block"
    report = runner.score(rows, policy, replay)
    fails = runner.check_thresholds(report)
    assert any("false-block" in f.lower() or "false block" in f.lower() for f in fails)


# --------------------------------------------------------------------------- negative: safety escape
def test_zero_safety_escape_threshold(tmp_path: Path) -> None:
    """REQ-INV-005 *negative*: one allowed high-severity row fails the run (hard 0, no averaging)."""
    runner = _load("eval_runner_escape", RUNNER_PATH)
    highrow = _jigsaw("EV-H000", {"identity_hate": 1}, stratum="jigsaw/idh")
    txn = _jigsaw("EV-T000", {}, stratum="jigsaw/clean")
    rows = [highrow, txn]
    corpus_file = _write_jsonl(tmp_path / "c.jsonl", rows)
    replay_file = _write_jsonl(
        tmp_path / "r.jsonl",
        [{"eval_id": "EV-H000", "verdict": "allow"}, {"eval_id": "EV-T000", "verdict": "allow"}],
    )
    code = runner.main(
        ["--corpus", str(corpus_file), "--policy", str(POLICY_PATH), "--replay", str(replay_file)]
    )
    assert code != 0


# --------------------------------------------------------------------------- replay fixtures / gate
def _corpus_and_replays(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Return (corpus, good_replay, bad_replay).

    When the real corpus is present (PR #37 landed) the shipped fixtures are used. Otherwise
    a synthetic corpus plus a matching good/bad pair is built from the policy, so these tests
    exercise the same contract on this branch without depending on #37.
    """
    if CORPUS_PATH.exists():
        return CORPUS_PATH, GOOD_REPLAY, BAD_REPLAY
    runner = _load("eval_runner_fixtures", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    rows = _synthetic_corpus()
    corpus = _write_jsonl(tmp_path / "corpus.jsonl", rows)
    good = [{"eval_id": r["eval_id"], "verdict": runner.derive_expectation(r, policy).expected_verdict} for r in rows]
    bad = [dict(x) for x in good]
    first_high = next(
        r["eval_id"]
        for r in rows
        if runner.derive_expectation(r, policy).expected_severity == "high"
    )
    for item in bad:
        if item["eval_id"] == first_high:
            item["verdict"] = "allow"  # deliberate high-severity safety escape
    return (
        corpus,
        _write_jsonl(tmp_path / "good.jsonl", good),
        _write_jsonl(tmp_path / "bad.jsonl", bad),
    )


def test_bad_prompt_blocked_under_strict(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """REQ-INV-005 *negative*: the deliberately bad replay fails gate 4 under --strict."""
    gate = _load("gate_bad", GATE_PATH)
    corpus, _good, bad = _corpus_and_replays(tmp_path)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=["--strict"],
        files=["prompts/prompt_v1.0.yaml"],
        corpus_path=str(corpus),
        replay_path=str(bad),
    )
    assert code != 0
    assert "FAIL" in out.upper()


def test_good_prompt_passes_under_strict(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """REQ-INV-005: the good replay passes gate 4 under --strict."""
    gate = _load("gate_good", GATE_PATH)
    corpus, good, _bad = _corpus_and_replays(tmp_path)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=["--strict"],
        files=["prompts/prompt_v1.0.yaml"],
        corpus_path=str(corpus),
        replay_path=str(good),
    )
    assert code == 0, out
    assert "PASS" in out.upper()


def test_shipped_fixtures_agree_and_escape() -> None:
    """REQ-INV-005: the shipped fixtures are a matching good set and a one-escape bad set.

    The shipped fixtures are keyed to the real fixed corpus; that corpus lives on PR #37
    (not yet on main). Skip here when it is absent — the good/bad contract is still covered
    by ``test_bad_prompt_blocked_under_strict`` / ``test_good_prompt_passes_under_strict``,
    which derive an equivalent pair from the policy on this branch.
    """
    if not CORPUS_PATH.exists():
        pytest.skip("real corpus (PR #37) not on this branch; fixtures target it")
    runner = _load("eval_runner_shipped", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    corpus = runner.load_corpus(CORPUS_PATH)
    good = runner.load_replay(GOOD_REPLAY)
    bad = runner.load_replay(BAD_REPLAY)
    good_report = runner.score(corpus, policy, good)
    bad_report = runner.score(corpus, policy, bad)
    assert good_report.safety_escapes == []
    assert good_report.ok is True
    assert len(bad_report.safety_escapes) == 1


def test_gate_no_fixture_default_pass_when_corpus_exists_no_replay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """REQ-INV-005: with a corpus but NO replay artifact, gate reports cannot-evaluate and
    must NOT default to a fixture and print PASS. Warn-only ⇒ exit 0 by design, not by PASS."""
    gate = _load("gate_nofixture", GATE_PATH)
    corpus, _good, _bad = _corpus_and_replays(tmp_path)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=[],
        files=["prompts/prompt_v1.0.yaml"],
        corpus_path=str(corpus),
        replay_path=None,  # explicitly no replay configured
    )
    assert code == 0  # warn-only step
    assert "CANNOT EVALUATE" in out.upper()
    assert "no replay artifact" in out.lower()
    assert "GATE 4 PASS" not in out.upper()


def test_missing_eval_set_fails_closed_under_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-INV-005 *negative*: no corpus at all ⇒ nonzero under --strict (never silently passes)."""
    gate = _load("gate_missing", GATE_PATH)
    code, _out = _run_gate(
        monkeypatch,
        gate,
        argv=["--strict"],
        files=["prompts/prompt_v1.0.yaml"],
        corpus_path=str(Path("/nonexistent/moderation_eval.jsonl")),
        replay_path=str(GOOD_REPLAY),
    )
    assert code != 0


def test_missing_corpus_warn_only_without_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-INV-005: today's state (no corpus on main) warns and passes without --strict."""
    gate = _load("gate_missing_warn", GATE_PATH)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=[],
        files=["prompts/prompt_v1.0.yaml"],
        corpus_path=str(Path("/nonexistent/moderation_eval.jsonl")),
        replay_path=str(GOOD_REPLAY),
    )
    assert code == 0
    assert "WARNING" in out.upper()


def test_no_prompt_change_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-INV-005: a PR that touches no prompt/model path passes (gate not applicable)."""
    gate = _load("gate_noprompt", GATE_PATH)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=["--strict"],
        files=["docs/readme.md"],
        corpus_path=None,
        replay_path=None,
    )
    assert code == 0
    assert "PASS" in out.upper()


def test_ground_truth_change_in_prompt_pr_fails_without_strict(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """REQ-INV-005 / TD-1 *negative*: a prompt PR that also edits the ground truth fails
    gate 4 even without --strict, naming the ground-truth file."""
    gate = _load("gate_gt_policy", GATE_PATH)
    monkeypatch.delenv("EVAL_REPLAY", raising=False)
    corpus = CORPUS_PATH if CORPUS_PATH.exists() else _write_synthetic_corpus(tmp_path)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=[],  # no --strict: this must still block
        files=["prompts/prompt_v1.0.yaml", "test/eval/expectation_policy.yaml"],
        corpus_path=str(corpus),
        replay_path=str(GOOD_REPLAY),
    )
    assert code != 0
    assert "ground truth changed in a prompt pr" in out.lower()
    assert "test/eval/expectation_policy.yaml" in out


def test_ground_truth_change_in_prompt_pr_corpus_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """REQ-INV-005 / TD-1 *negative*: editing the corpus alongside a prompt change also fails."""
    gate = _load("gate_gt_corpus", GATE_PATH)
    monkeypatch.delenv("EVAL_REPLAY", raising=False)
    corpus = CORPUS_PATH if CORPUS_PATH.exists() else _write_synthetic_corpus(tmp_path)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=[],
        files=["prompts/prompt_v1.0.yaml", "test/eval/moderation_eval.jsonl"],
        corpus_path=str(corpus),
        replay_path=str(GOOD_REPLAY),
    )
    assert code != 0
    assert "ground truth changed in a prompt pr" in out.lower()
    assert "test/eval/moderation_eval.jsonl" in out


def test_ground_truth_change_without_prompt_change_is_allowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """REQ-INV-005: a PR that edits the policy WITHOUT a prompt/model change is not gated here."""
    gate = _load("gate_gt_nochange", GATE_PATH)
    monkeypatch.delenv("EVAL_REPLAY", raising=False)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=[],
        files=["test/eval/expectation_policy.yaml"],
        corpus_path=None,
        replay_path=None,
    )
    assert code == 0
    assert "PASS" in out.upper()


def test_resolve_replay_accepts_equals_form(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """REQ-INV-005: resolve_replay accepts --replay=PATH as well as --replay PATH."""
    gate = _load("gate_resolve_eq", GATE_PATH)
    monkeypatch.delenv("EVAL_REPLAY", raising=False)
    monkeypatch.setattr(gate, "EVAL_REPLAY", None)
    target = tmp_path / "r.jsonl"
    assert gate.resolve_replay([f"--replay={target}"]) == target
    assert gate.resolve_replay(["--replay", str(target)]) == target


def test_resolve_replay_bare_flag_is_usage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-INV-005 *negative*: a bare --replay with no value is a usage error, not a silent
    fall-through to EVAL_REPLAY/None."""
    gate = _load("gate_resolve_bare", GATE_PATH)
    monkeypatch.delenv("EVAL_REPLAY", raising=False)
    monkeypatch.setattr(gate, "EVAL_REPLAY", Path("/some/env/replay.jsonl"))
    with pytest.raises(gate.ReplayUsageError):
        gate.resolve_replay(["--replay"])


def test_resolve_replay_empty_equals_is_usage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-INV-005 *negative*: --replay= with an empty value is a usage error."""
    gate = _load("gate_resolve_empty", GATE_PATH)
    monkeypatch.delenv("EVAL_REPLAY", raising=False)
    with pytest.raises(gate.ReplayUsageError):
        gate.resolve_replay(["--replay="])


def test_gate_bare_replay_flag_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """REQ-INV-005 *negative*: the gate exits non-zero with a usage error on a bare --replay
    even without --strict (a misconfigured flag must not report CANNOT EVALUATE / pass)."""
    gate = _load("gate_bare_main", GATE_PATH)
    corpus = CORPUS_PATH if CORPUS_PATH.exists() else _write_synthetic_corpus(tmp_path)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=["--replay"],
        files=["prompts/prompt_v1.0.yaml"],
        corpus_path=str(corpus),
        replay_path=None,
        inject_replay=False,
    )
    assert code != 0
    assert "usage" in out.lower()


def test_recorded_replay_no_secret_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """REQ-INV-005: without a provider secret the gate uses recorded replay, never live calls."""
    gate = _load("gate_replay", GATE_PATH)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PROVIDER_API_KEY", raising=False)
    corpus = CORPUS_PATH if CORPUS_PATH.exists() else _write_synthetic_corpus(tmp_path)
    code, out = _run_gate(
        monkeypatch,
        gate,
        argv=["--strict"],
        files=["prompts/prompt_v1.0.yaml"],
        corpus_path=str(corpus),
        replay_path=str(GOOD_REPLAY),
    )
    assert code == 0
    assert "recorded replay" in out.lower()


def test_gate_output_echoes_per_row_rule() -> None:
    """REQ-INV-005: the runner echoes eval_id + matched rule id + derived verdict/severity."""
    runner = _load("eval_runner_echo", RUNNER_PATH)
    policy = runner.load_policy(POLICY_PATH)
    row = _jigsaw("EV-0001", {"severe_toxic": 1, "toxic": 1}, stratum="jigsaw/idh")
    report = runner.score([row], policy, {"EV-0001": "block"})
    table = runner.format_table(report)
    assert "EV-0001" in table
    assert "jigsaw-high-risk" in table
    assert "block" in table
    assert "high" in table


def test_corpus_schema_and_hash_validation(tmp_path: Path) -> None:
    """REQ-INV-005: corpus loader rejects a bad text_sha256 and duplicate eval_id."""
    runner = _load("eval_runner_schema", RUNNER_PATH)
    good = _jigsaw("EV-0001", {}, stratum="jigsaw/clean")
    ok_file = _write_jsonl(tmp_path / "ok.jsonl", [good])
    assert runner.load_corpus(ok_file)[0]["eval_id"] == "EV-0001"

    bad_hash = dict(good)
    bad_hash["text_sha256"] = "0" * 64
    bad_file = _write_jsonl(tmp_path / "bad.jsonl", [bad_hash])
    with pytest.raises(runner.EvalError):
        runner.load_corpus(bad_file)

    dup_file = _write_jsonl(tmp_path / "dup.jsonl", [good, good])
    with pytest.raises(runner.EvalError):
        runner.load_corpus(dup_file)


# --------------------------------------------------------------- policy validation (TD-1)
def _write_policy(tmp_path: Path, name: str, policy: dict[str, Any]) -> Path:
    path = tmp_path / f"{name}.yaml"
    import yaml as _yaml

    path.write_text(_yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    return path


def _base_policy(rules: list[dict[str, Any]]) -> dict[str, Any]:
    return {"version": 1, "match": "first_match", "rules": rules}


def _clean_rule(**over: Any) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "id": "jigsaw-clean",
        "when": {"label_scheme": "jigsaw-six-independent-binary-v1", "all_zero": ["toxic"]},
        "expected_verdict": "allow",
        "expected_severity": "normal",
    }
    rule.update(over)
    return rule


def test_load_policy_rejects_uppercase_severity(tmp_path: Path) -> None:
    """REQ-INV-005 / TD-1 *negative*: expected_severity 'HIGH' (uppercase) is rejected."""
    runner = _load("eval_runner_pol_sev", RUNNER_PATH)
    path = _write_policy(
        tmp_path, "bad-sev", _base_policy([_clean_rule(expected_severity="HIGH")])
    )
    with pytest.raises(runner.EvalError) as exc:
        runner.load_policy(path)
    msg = str(exc.value)
    assert "jigsaw-clean" in msg
    assert "HIGH" in msg


def test_load_policy_rejects_uppercase_verdict(tmp_path: Path) -> None:
    """REQ-INV-005 / TD-1 *negative*: expected_verdict 'BLOCK' is rejected."""
    runner = _load("eval_runner_pol_ver", RUNNER_PATH)
    path = _write_policy(
        tmp_path, "bad-ver", _base_policy([_clean_rule(expected_verdict="BLOCK")])
    )
    with pytest.raises(runner.EvalError) as exc:
        runner.load_policy(path)
    msg = str(exc.value)
    assert "jigsaw-clean" in msg
    assert "BLOCK" in msg


def test_load_policy_rejects_unknown_when_key(tmp_path: Path) -> None:
    """REQ-INV-005 / TD-1 *negative*: a when with an unknown key is rejected."""
    runner = _load("eval_runner_pol_when", RUNNER_PATH)
    rule = _clean_rule(
        when={"label_scheme": "jigsaw-six-independent-binary-v1", "bogus_key": True}
    )
    path = _write_policy(tmp_path, "bad-when", _base_policy([rule]))
    with pytest.raises(runner.EvalError) as exc:
        runner.load_policy(path)
    assert "bogus_key" in str(exc.value)


def test_load_policy_rejects_empty_when(tmp_path: Path) -> None:
    """REQ-INV-005 / TD-1 *negative*: an empty when is rejected."""
    runner = _load("eval_runner_pol_empty", RUNNER_PATH)
    path = _write_policy(tmp_path, "empty-when", _base_policy([_clean_rule(when={})]))
    with pytest.raises(runner.EvalError) as exc:
        runner.load_policy(path)
    assert "jigsaw-clean" in str(exc.value)


def test_load_policy_rejects_duplicate_ids(tmp_path: Path) -> None:
    """REQ-INV-005 / TD-1 *negative*: two rules sharing an id are rejected."""
    runner = _load("eval_runner_pol_dup", RUNNER_PATH)
    path = _write_policy(
        tmp_path, "dup-ids", _base_policy([_clean_rule(), _clean_rule()])
    )
    with pytest.raises(runner.EvalError) as exc:
        runner.load_policy(path)
    assert "jigsaw-clean" in str(exc.value)


def test_load_policy_rejects_blank_id(tmp_path: Path) -> None:
    """REQ-INV-005 / TD-1 *negative*: a blank rule id is rejected."""
    runner = _load("eval_runner_pol_blank", RUNNER_PATH)
    path = _write_policy(tmp_path, "blank-id", _base_policy([_clean_rule(id="")]))
    with pytest.raises(runner.EvalError):
        runner.load_policy(path)


def test_load_policy_yaml_error_is_evalerror(tmp_path: Path) -> None:
    """REQ-INV-005 / TD-1 *negative*: malformed YAML raises EvalError naming the path."""
    runner = _load("eval_runner_pol_yaml", RUNNER_PATH)
    path = tmp_path / "malformed.yaml"
    path.write_text("match: first_match\nrules: [ : : not valid yaml\n", encoding="utf-8")
    with pytest.raises(runner.EvalError) as exc:
        runner.load_policy(path)
    assert "malformed.yaml" in str(exc.value)


# --------------------------------------------------------------------------- infrastructure
def _write_synthetic_corpus(tmp_path: Path) -> Path:
    return _write_jsonl(tmp_path / "synthetic_corpus.jsonl", _synthetic_corpus())


def _run_gate(
    monkeypatch: pytest.MonkeyPatch,
    gate: ModuleType,
    *,
    argv: list[str],
    files: list[str],
    corpus_path: str | None,
    replay_path: str | None,
    inject_replay: bool = True,
) -> tuple[int, str]:
    """Drive check_semantic_eval.main with PR context, corpus and replay paths injected."""
    # Ensure a developer's shell EVAL_REPLAY cannot leak into the gate result.
    monkeypatch.delenv("EVAL_REPLAY", raising=False)
    event = {
        "pull_request": {
            "number": 1,
            "body": "see REQ-INV-005",
            "base": {"repo": {"full_name": "o/r"}},
        }
    }
    monkeypatch.setattr(gate, "event_payload", lambda: event)
    monkeypatch.setattr(gate, "changed_files", lambda *a, **k: files)
    if corpus_path is not None:
        monkeypatch.setattr(gate, "EVAL_SET", Path(corpus_path))
    if inject_replay:
        if replay_path is not None:
            monkeypatch.setattr(gate, "EVAL_REPLAY", Path(replay_path))
        else:
            monkeypatch.setattr(gate, "EVAL_REPLAY", None)
    monkeypatch.setattr(sys, "argv", ["check_semantic_eval.py", *argv])
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = gate.main()
    return code, buf.getvalue()
