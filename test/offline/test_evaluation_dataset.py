"""Validation of the fixed semantic evaluation set (REQ-INV-005, issue #36).

Checks the committed 100-record set at ``test/eval/moderation_eval.jsonl``:
80 Jigsaw + 20 COLD, seed 5351, the approved deterministic strata/quotas,
native labels preserved, Jigsaw split ``null``, and documented provenance.
Negative tests prove the validator rejects schema, label and coverage
violations; builder tests prove input pinning and deterministic ranking.

Deterministic and offline: no network, no raw inputs, and no source text in
failure messages.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
EVAL_PATH = ROOT / "test" / "eval" / "moderation_eval.jsonl"
README_PATH = ROOT / "test" / "eval" / "README.md"
NOTICE_PATH = ROOT / "test" / "eval" / "NOTICE.md"
BUILDER_PATH = ROOT / "scripts" / "build_evaluation_dataset.py"


def _load_builder() -> ModuleType:
    """Load ``scripts/build_evaluation_dataset.py`` without a path-mutating import."""
    spec = importlib.util.spec_from_file_location("build_evaluation_dataset", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {BUILDER_PATH.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder: ModuleType = _load_builder()

SEED = 5351
JIGSAW_LABELS = (
    "toxic",
    "severe_toxic",
    "obscene",
    "threat",
    "insult",
    "identity_hate",
)
COLD_TOPICS = ("gender", "race", "region")
COLD_LABEL_KEYS = ("label", "fine-grained-label")

JIGSAW_SCHEME = "jigsaw-six-independent-binary-v1"
COLD_SCHEME = "cold-test-binary-plus-finegrained-v1"

REQUIRED_KEYS = (
    "eval_id",
    "source",
    "source_split",
    "source_language",
    "text",
    "label_scheme",
    "labels",
    "topic",
    "selection_stratum",
    "selection_seed",
    "text_sha256",
)

JIGSAW_QUOTAS = {
    "jigsaw/idh": 12,
    "jigsaw/threat-no-idh": 10,
    "jigsaw/severe-no-idh-no-threat": 10,
    "jigsaw/toxic-only": 12,
    "jigsaw/mixed/toxic-obscene-insult": 7,
    "jigsaw/mixed/toxic-insult": 3,
    "jigsaw/mixed/toxic-obscene": 3,
    "jigsaw/single/obscene": 1,
    "jigsaw/single/insult": 1,
    "jigsaw/single/obscene-insult": 1,
    "jigsaw/clean": 20,
}

COLD_QUOTAS = {
    "cold/label0-fg0/gender": 3,
    "cold/label0-fg0/race": 2,
    "cold/label0-fg0/region": 2,
    "cold/label0-fg3/gender": 1,
    "cold/label0-fg3/race": 1,
    "cold/label0-fg3/region": 1,
    "cold/label1-fg1/gender": 1,
    "cold/label1-fg1/race": 1,
    "cold/label1-fg1/region": 1,
    "cold/label1-fg2/gender": 3,
    "cold/label1-fg2/race": 2,
    "cold/label1-fg2/region": 2,
}

JIGSAW_FLOORS = {
    "toxic": 54,
    "severe_toxic": 10,
    "obscene": 28,
    "threat": 10,
    "insult": 25,
    "identity_hate": 12,
}

JIGSAW_INPUT_SHA256 = (
    "ae2968a0248be3b99b636a3924e2895034da12bc307ead40da22593b893761e3"
)
COLD_INPUT_SHA256 = (
    "df4cf25b99152f6c93443371095f2e0e6e54506005cf82e6add9b13e89c82d53"
)
JIGSAW_URL = "https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge"
COLD_URL = "https://github.com/thu-coai/COLDataset"
RETRIEVAL_DATE = "2026-11-16"
COLD_COMMIT_SHA = "a0c55a945497ab58e94aef491180e1cf88ffb864"

HEX64 = re.compile(r"^[0-9a-f]{64}$")
EVAL_ID = re.compile(r"^EV-\d{4}$")


def _read_records(path: Path) -> list[dict[str, Any]]:
    """Parse JSONL; errors carry line numbers only, never record text."""
    records: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at line {lineno}: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise TypeError(f"line {lineno} is not a JSON object")
        records.append(record)
    return records


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _jigsaw_stratum(labels: dict[str, int]) -> str:
    if labels["identity_hate"] == 1:
        return "jigsaw/idh"
    if labels["threat"] == 1:
        return "jigsaw/threat-no-idh"
    if labels["severe_toxic"] == 1:
        return "jigsaw/severe-no-idh-no-threat"
    toxic = labels["toxic"] == 1
    obscene = labels["obscene"] == 1
    insult = labels["insult"] == 1
    if toxic and not obscene and not insult:
        return "jigsaw/toxic-only"
    if toxic and obscene and insult:
        return "jigsaw/mixed/toxic-obscene-insult"
    if toxic and insult:
        return "jigsaw/mixed/toxic-insult"
    if toxic and obscene:
        return "jigsaw/mixed/toxic-obscene"
    if obscene and insult:
        return "jigsaw/single/obscene-insult"
    if obscene:
        return "jigsaw/single/obscene"
    if insult:
        return "jigsaw/single/insult"
    return "jigsaw/clean"


def validate_dataset(
    records: list[dict[str, Any]], readme_text: str | None = None
) -> None:
    """Validate the full approved dataset contract; raise AssertionError."""
    assert len(records) == 100, f"expected 100 records, got {len(records)}"

    for index, record in enumerate(records):
        assert set(record) == set(REQUIRED_KEYS), (
            f"record {index + 1}: unexpected key set"
        )
        assert record["eval_id"] == f"EV-{index + 1:04d}", (
            f"record {index + 1}: non-sequential eval_id"
        )
        assert EVAL_ID.match(str(record["eval_id"]))
        assert record["selection_seed"] == SEED

        source = record["source"]
        assert source in ("jigsaw", "cold"), f"record {index + 1}: unknown source"

        text = record["text"]
        assert isinstance(text, str) and text.strip(), (
            f"record {index + 1}: empty text"
        )
        assert HEX64.match(str(record["text_sha256"]))
        assert record["text_sha256"] == hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest(), f"record {index + 1}: text digest mismatch"

        if source == "jigsaw":
            assert record["source_split"] is None, (
                f"record {index + 1}: Jigsaw split must stay null"
            )
            assert record["source_language"] == "en"
            assert record["label_scheme"] == JIGSAW_SCHEME
            assert record["topic"] is None
            labels = record["labels"]
            assert isinstance(labels, dict)
            assert set(labels) == set(JIGSAW_LABELS), (
                f"record {index + 1}: Jigsaw labels must be the six native keys"
            )
            for name in JIGSAW_LABELS:
                assert _is_int(labels[name]), (
                    f"record {index + 1}: {name} must be an int"
                )
                assert labels[name] in (0, 1), (
                    f"record {index + 1}: {name} must be 0 or 1"
                )
            expected_stratum = _jigsaw_stratum(labels)
        else:
            assert record["source_split"] == "test", (
                f"record {index + 1}: COLD split must be the native test split"
            )
            assert record["source_language"] == "zh"
            assert record["label_scheme"] == COLD_SCHEME
            assert record["topic"] in COLD_TOPICS, (
                f"record {index + 1}: invalid COLD topic"
            )
            labels = record["labels"]
            assert isinstance(labels, dict)
            assert set(labels) == set(COLD_LABEL_KEYS), (
                f"record {index + 1}: COLD labels must keep native keys"
            )
            assert _is_int(labels["label"]) and labels["label"] in (0, 1)
            fine = labels["fine-grained-label"]
            assert _is_int(fine) and fine in (0, 1, 2, 3)
            assert (labels["label"] == 1) == (fine in (1, 2)), (
                f"record {index + 1}: COLD label/fine-grained inconsistency"
            )
            expected_stratum = (
                f"cold/label{labels['label']}-fg{fine}/{record['topic']}"
            )

        assert record["selection_stratum"] == expected_stratum, (
            f"record {index + 1}: stratum does not match record content"
        )

    eval_ids = [record["eval_id"] for record in records]
    assert len(set(eval_ids)) == len(eval_ids), "duplicate eval_id"
    texts = [record["text"] for record in records]
    assert len(set(texts)) == len(texts), "duplicate evaluation text"
    digests = [record["text_sha256"] for record in records]
    assert len(set(digests)) == len(digests), "duplicate text_sha256"

    jigsaw = [record for record in records if record["source"] == "jigsaw"]
    cold = [record for record in records if record["source"] == "cold"]
    assert (len(jigsaw), len(cold)) == (80, 20), "source allocation must be 80/20"

    _validate_jigsaw(jigsaw)
    _validate_cold(cold)

    if readme_text is not None:
        _validate_readme(readme_text)


def _validate_jigsaw(records: list[dict[str, Any]]) -> None:
    counts = {
        name: sum(int(record["labels"][name]) for record in records)
        for name in JIGSAW_LABELS
    }
    for name, floor in JIGSAW_FLOORS.items():
        assert counts[name] >= floor, f"{name} below guaranteed floor {floor}"

    clean = sum(
        1
        for record in records
        if all(record["labels"][name] == 0 for name in JIGSAW_LABELS)
    )
    assert clean == 20, "expected exactly 20 clean Jigsaw controls"
    idh_negative = sum(
        1 for record in records if record["labels"]["identity_hate"] == 0
    )
    assert idh_negative == 68, "expected exactly 68 identity_hate-negative rows"
    toxic_idh_negative = sum(
        1
        for record in records
        if record["labels"]["toxic"] == 1
        and record["labels"]["identity_hate"] == 0
    )
    assert toxic_idh_negative >= 44, "too few toxic non-IDH controls"
    high_risk = sum(
        1
        for record in records
        if any(
            record["labels"][name] == 1
            for name in ("severe_toxic", "threat", "identity_hate")
        )
    )
    assert high_risk >= 32, "high-risk coverage slice below 32"

    strata = Counter(record["selection_stratum"] for record in records)
    assert dict(strata) == JIGSAW_QUOTAS, "Jigsaw stratum quotas do not match"


def _validate_cold(records: list[dict[str, Any]]) -> None:
    strata = Counter(record["selection_stratum"] for record in records)
    assert dict(strata) == COLD_QUOTAS, "COLD quotas do not match"

    labels = Counter(record["labels"]["label"] for record in records)
    assert labels == {0: 10, 1: 10}, "COLD binary labels must be 10/10"

    cells = Counter(
        (record["labels"]["label"], record["labels"]["fine-grained-label"])
        for record in records
    )
    assert cells == {(0, 0): 7, (0, 3): 3, (1, 1): 3, (1, 2): 7}, (
        "COLD fine-grained cells must be 7/3/3/7"
    )

    topics = Counter(record["topic"] for record in records)
    assert topics == {"gender": 8, "race": 6, "region": 6}, (
        "COLD topic balance must be 8/6/6"
    )


def _validate_readme(text: str) -> None:
    required = (
        "REQ-INV-005",
        str(SEED),
        JIGSAW_INPUT_SHA256,
        COLD_INPUT_SHA256,
        JIGSAW_URL,
        COLD_URL,
        "other-Non-offen",
        "attack individual",
        "attack group",
        "anti-bias",
        "not a prevalence benchmark",
        "Content warning",
        "CC0 1.0",
        "CC BY-SA 3.0",
        "Apache-2.0",
        "NOTICE.md",
        RETRIEVAL_DATE,
        COLD_COMMIT_SHA,
    )
    missing = [item for item in required if item not in text]
    assert not missing, f"README missing required provenance items: {missing}"


def _valid_records() -> list[dict[str, Any]]:
    return _read_records(EVAL_PATH)


def _mutated(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return copy.deepcopy(records)


def test_committed_dataset_validates_against_contract() -> None:
    """REQ-INV-005: committed set matches the approved schema and quotas."""
    readme = README_PATH.read_text(encoding="utf-8")
    validate_dataset(_valid_records(), readme)
    assert RETRIEVAL_DATE in readme
    assert COLD_COMMIT_SHA in readme


def test_builder_rank_key_is_deterministic_and_seed_sensitive() -> None:
    """REQ-INV-005: selection basis is reproducible and seed-bound."""
    first = builder.rank_key(SEED, "jigsaw", "jigsaw/idh", "example")
    second = builder.rank_key(SEED, "jigsaw", "jigsaw/idh", "example")
    assert first == second
    assert first != builder.rank_key(SEED + 1, "jigsaw", "jigsaw/idh", "example")
    assert first != builder.rank_key(SEED, "cold", "jigsaw/idh", "example")


def test_builder_rejects_inputs_inside_repository() -> None:
    """REQ-INV-005: raw inputs must stay outside Git (negative test)."""
    with pytest.raises(ValueError):
        builder.ensure_outside_repo(ROOT / "test" / "eval" / "moderation_eval.jsonl")


def test_builder_rejects_input_digest_mismatch(tmp_path: Path) -> None:
    """REQ-INV-005: pinned input hashes are enforced (negative test)."""
    path = tmp_path / "raw.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        builder.verify_file_digest(path, "0" * 64)


def test_builder_worst_case_guarantee_arithmetic() -> None:
    """REQ-INV-005: floor guarantees follow the pool arithmetic."""
    rows: list[dict[str, Any]] = [{"obscene": 0}, {"obscene": 1}]
    assert builder._worst_case_min(rows, 1, "obscene") == 0
    assert builder._worst_case_min(rows, 2, "obscene") == 1


def test_builder_rejects_cold_pool_shortage() -> None:
    """REQ-INV-005: COLD quota feasibility is enforced (negative test)."""
    with pytest.raises(ValueError):
        builder.check_cold_pools([])


def test_builder_fails_without_writing_on_bad_inputs(tmp_path: Path) -> None:
    """REQ-INV-005: a failed build leaves no output file (negative test)."""
    jigsaw = tmp_path / "jigsaw.jsonl"
    cold = tmp_path / "cold.jsonl"
    out = tmp_path / "out" / "moderation_eval.jsonl"
    jigsaw.write_text("{}\n", encoding="utf-8")
    cold.write_text("{}\n", encoding="utf-8")
    code = builder.main(
        ["--jigsaw", str(jigsaw), "--cold", str(cold), "--out", str(out)]
    )
    assert code != 0
    assert not out.exists()


def test_validator_rejects_non_binary_label() -> None:
    """REQ-INV-005: invalid label value is rejected (negative test)."""
    records = _mutated(_valid_records())
    records[0]["labels"]["toxic"] = 2
    with pytest.raises(AssertionError):
        validate_dataset(records)


def test_validator_rejects_missing_identity_hate_label() -> None:
    """REQ-INV-005: collapsing the six labels is rejected (negative test)."""
    records = _mutated(_valid_records())
    del records[0]["labels"]["identity_hate"]
    with pytest.raises(AssertionError):
        validate_dataset(records)


def test_validator_rejects_cold_jigsaw_mapping() -> None:
    """REQ-INV-005: COLD must not be silently mapped to Jigsaw labels."""
    records = _mutated(_valid_records())
    cold = next(record for record in records if record["source"] == "cold")
    cold["labels"] = {name: 0 for name in JIGSAW_LABELS}
    with pytest.raises(AssertionError):
        validate_dataset(records)


def test_validator_rejects_fabricated_jigsaw_split() -> None:
    """REQ-INV-005: Jigsaw source_split must stay null (negative test)."""
    records = _mutated(_valid_records())
    records[0]["source_split"] = "train"
    with pytest.raises(AssertionError):
        validate_dataset(records)


def test_validator_rejects_model_generated_field() -> None:
    """REQ-INV-005: model-generated ground truth is rejected."""
    records = _mutated(_valid_records())
    records[0]["predicted_toxic"] = 1
    with pytest.raises(AssertionError):
        validate_dataset(records)


def test_validator_rejects_duplicate_eval_id() -> None:
    """REQ-INV-005: eval IDs must be unique and sequential (negative test)."""
    records = _mutated(_valid_records())
    records[1]["eval_id"] = records[0]["eval_id"]
    with pytest.raises(AssertionError):
        validate_dataset(records)


def test_validator_rejects_identity_hate_coverage_gap() -> None:
    """REQ-INV-005: identity_hate coverage floor is enforced (negative test)."""
    records = _mutated(_valid_records())
    for record in records:
        if record["source"] == "jigsaw":
            record["labels"]["identity_hate"] = 0
    with pytest.raises(AssertionError):
        validate_dataset(records)


def test_validator_rejects_unknown_source() -> None:
    """REQ-INV-005: only the two approved sources are accepted."""
    records = _mutated(_valid_records())
    records[0]["source"] = "other"
    with pytest.raises(AssertionError):
        validate_dataset(records)


def test_validator_rejects_cold_label_finegrained_mismatch() -> None:
    """REQ-INV-005: COLD codebook consistency is enforced (negative test)."""
    records = _mutated(_valid_records())
    cold = next(record for record in records if record["source"] == "cold")
    cold["labels"] = {"label": 1, "fine-grained-label": 0}
    cold["selection_stratum"] = "cold/label1-fg0/gender"
    with pytest.raises(AssertionError):
        validate_dataset(records)


def test_loader_rejects_malformed_json_line(tmp_path: Path) -> None:
    """REQ-INV-005: malformed JSONL is rejected without echoing text."""
    path = tmp_path / "bad.jsonl"
    path.write_text('{"eval_id": "EV-0001"}\nnot-json\n', encoding="utf-8")
    with pytest.raises(ValueError):
        _read_records(path)


def test_loader_ignores_blank_lines_only_at_edges(tmp_path: Path) -> None:
    """REQ-INV-005: blank lines are skipped, not treated as records."""
    path = tmp_path / "blank.jsonl"
    path.write_text('\n{"eval_id": "EV-0001"}\n\n', encoding="utf-8")
    assert _read_records(path) == [{"eval_id": "EV-0001"}]


def test_has_pii_detects_supported_patterns() -> None:
    """REQ-INV-005: supported PII classes are detected deterministically."""
    assert builder.has_pii("contact user@example.com")
    assert builder.has_pii("host 192.0.2.10 replied")
    assert builder.has_pii("see /u/example_user")
    assert builder.has_pii("signed user:example_user")


def test_has_pii_ignores_generic_urls_and_clean_text() -> None:
    """REQ-INV-005: generic URLs and clean text are not PII."""
    assert not builder.has_pii("see https://example.com/article?id=123")
    assert not builder.has_pii("a normal comment with no identifiers")


def test_has_pii_detects_reviewed_text_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-INV-005: manual-review digests are treated as PII markers."""
    text = "reviewed identifier candidate"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    monkeypatch.setattr(
        builder, "REVIEWED_PII_TEXT_SHA256", frozenset({digest})
    )
    assert builder.has_pii(text)


def test_exclude_pii_rows_is_deterministic() -> None:
    """REQ-INV-005: PII row exclusion preserves order and is repeatable."""
    rows = [
        {"comment_text": "clean text"},
        {"comment_text": "host 192.0.2.10"},
        {"comment_text": "signed user:example_user"},
        {"comment_text": "https://example.com/article"},
    ]
    first = builder.exclude_pii_rows(rows, "comment_text")
    second = builder.exclude_pii_rows(rows, "comment_text")
    assert first == second
    assert [row["comment_text"] for row in first] == [
        "clean text",
        "https://example.com/article",
    ]


def test_select_jigsaw_backfills_same_stratum_after_pii_exclusion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-INV-005: a PII-bearing top-ranked row is replaced by a clean row."""
    monkeypatch.setattr(
        builder,
        "jigsaw_strata",
        lambda: [("synthetic/all", lambda row: True, 1)],
    )
    monkeypatch.setattr(
        builder,
        "rank_key",
        lambda seed, source, stratum, text: text,
    )
    rows = [
        {"comment_text": "0 host 192.0.2.10"},
        {"comment_text": "1 clean replacement"},
    ]
    selected = builder.select_jigsaw(rows)
    assert [row["comment_text"] for _, row in selected] == [
        "1 clean replacement"
    ]


def test_replace_pii_selected_keeps_non_pii_positions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-INV-005: in-place replacement preserves non-PII record order."""
    monkeypatch.setattr(
        builder,
        "jigsaw_strata",
        lambda: [("synthetic/all", lambda row: True, 2)],
    )
    monkeypatch.setattr(
        builder,
        "rank_key",
        lambda seed, source, stratum, text: text,
    )
    rows = [
        {"comment_text": "0 host 192.0.2.10"},
        {"comment_text": "1 clean"},
        {"comment_text": "2 replacement"},
    ]
    baseline = builder.select_jigsaw(rows, exclude_pii=False)
    replaced = builder.replace_pii_selected(
        baseline, rows, SEED, "jigsaw", "comment_text"
    )
    assert [row["comment_text"] for _, row in replaced] == [
        "2 replacement",
        "1 clean",
    ]


def _synthetic_fallback_inputs() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]]
]:
    labels = {name: 0 for name in JIGSAW_LABELS}
    jigsaw_rows = [
        {
            "comment_text": (
                "0 host 192.0.2.10"
                if index == 0
                else f"synthetic comment {index}"
            ),
            **labels,
        }
        for index in range(95)
    ]
    cold_rows = [
        {
            "TEXT": "synthetic cold comment",
            "label": 0,
            "fine-grained-label": 0,
            "topic": "gender",
            "split": "test",
        }
    ]
    return jigsaw_rows, cold_rows


def test_build_records_aborts_when_pii_cannot_be_replaced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-INV-005: a PII shortfall aborts without the fallback flag."""
    monkeypatch.setattr(
        builder,
        "jigsaw_strata",
        lambda: [("synthetic/all", lambda row: True, 95)],
    )
    monkeypatch.setattr(builder, "COLD_CELLS", ((0, 0),))
    monkeypatch.setattr(builder, "COLD_TOPICS", ("gender",))
    monkeypatch.setattr(builder, "cold_quotas", lambda: {(0, 0, "gender"): 1})
    jigsaw_rows, cold_rows = _synthetic_fallback_inputs()
    with pytest.raises(ValueError):
        builder.build_records(jigsaw_rows, cold_rows)


def test_build_records_uses_95_fallback_only_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-INV-005: the approved 95 fallback is explicit and PII-free."""
    monkeypatch.setattr(
        builder,
        "jigsaw_strata",
        lambda: [("synthetic/all", lambda row: True, 95)],
    )
    monkeypatch.setattr(builder, "COLD_CELLS", ((0, 0),))
    monkeypatch.setattr(builder, "COLD_TOPICS", ("gender",))
    monkeypatch.setattr(builder, "cold_quotas", lambda: {(0, 0, "gender"): 1})
    jigsaw_rows, cold_rows = _synthetic_fallback_inputs()
    records = builder.build_records(
        jigsaw_rows, cold_rows, allow_fallback_95=True
    )
    assert len(records) == 95
    assert all(not builder.has_pii(record["text"]) for record in records)


def test_committed_corpus_contains_no_detected_pii() -> None:
    """REQ-INV-005: the committed corpus has no supported PII patterns."""
    records = _read_records(EVAL_PATH)
    offenders = [
        record["eval_id"]
        for record in records
        if builder.has_pii(record["text"])
    ]
    assert not offenders, f"PII detected in records: {offenders}"


def test_readme_corpus_hash_matches_file() -> None:
    """REQ-INV-005: README records the actual generated corpus digest."""
    digest = hashlib.sha256(EVAL_PATH.read_bytes()).hexdigest()
    assert digest in README_PATH.read_text(encoding="utf-8")


def test_readme_records_confirmed_retrieval_dates_and_commit() -> None:
    """REQ-INV-005: confirmed retrieval date and COLD commit are recorded."""
    text = README_PATH.read_text(encoding="utf-8")
    assert RETRIEVAL_DATE in text
    assert COLD_COMMIT_SHA in text
    assert "Retrieval dates are unknown" not in text


def test_notice_has_attribution_licenses_and_changes_statement() -> None:
    """REQ-INV-005: NOTICE carries verified attribution, licenses and changes."""
    text = NOTICE_PATH.read_text(encoding="utf-8")
    required = (
        JIGSAW_URL,
        COLD_URL,
        "CC0 1.0",
        "CC BY-SA 3.0",
        "Apache-2.0",
        "Changes made",
        "PII",
        "not endorsed",
        RETRIEVAL_DATE,
        COLD_COMMIT_SHA,
    )
    missing = [item for item in required if item not in text]
    assert not missing, f"NOTICE missing required items: {missing}"
