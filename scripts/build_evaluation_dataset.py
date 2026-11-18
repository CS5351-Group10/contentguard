"""Deterministic local builder for the fixed semantic evaluation set.

Implements the approved issue-#36 plan (REQ-INV-005): reads the local Jigsaw
and COLD extracts from outside the repository, verifies their pinned SHA-256
digests, checks the quota guarantees derived from the observed label pools,
selects records with a SHA-256 rank key, and writes
``test/eval/moderation_eval.jsonl``.

No network access. Source text is never logged: error messages name sources,
line numbers, strata and label fields only. Validation happens before any
output is written, so a failed run leaves no output file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

SEED = 5351
ROOT = Path(__file__).resolve().parents[1]
RANK_PREFIX = "contentguard-eval-v1"

JIGSAW_LABELS = (
    "toxic",
    "severe_toxic",
    "obscene",
    "threat",
    "insult",
    "identity_hate",
)
COLD_TOPICS = ("gender", "race", "region")
COLD_CELLS = ((0, 0), (0, 3), (1, 1), (1, 2))

JIGSAW_SCHEME = "jigsaw-six-independent-binary-v1"
COLD_SCHEME = "cold-test-binary-plus-finegrained-v1"

PINNED_SHA256 = {
    "jigsaw": "ae2968a0248be3b99b636a3924e2895034da12bc307ead40da22593b893761e3",
    "cold": "df4cf25b99152f6c93443371095f2e0e6e54506005cf82e6add9b13e89c82d53",
}

_IPV4_RE = re.compile(
    r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])"
)
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
_PERSONAL_IDENTIFIER_RE = re.compile(
    r"(?<![\w@])@[A-Za-z0-9_]{2,30}\b"
    r"|(?:/u/|/user/|(?<!\w)u/|\b(?:user|username):)[A-Za-z0-9_.-]{2,}",
    re.IGNORECASE,
)

# ADR-001 / REQ-INV-005: texts confirmed during manual review as containing
# direct personal names or account identifiers that the pattern detector missed.
# Stored as digests so reviewed text is not duplicated in the builder.
REVIEWED_PII_TEXT_SHA256 = frozenset(
    {
        "8f53115142a6e6ac76984a14f75382552712e3e0244b1296186a172d29ef692e",  # EV-0004
        "0256f3e92f619da2bdd73ad9f089146feeedc323c568fa559dfa2df3d4f6bf49",  # EV-0030
        "4c89fadf76717b3301dcc39bb37c1af2d049c1494a10b26cf9021b3d1d37eb94",  # EV-0032
        "9bc8212f74b37f9270e7e87a562220899c9316acbe480d789d66a40698b4d0dc",  # EV-0037
        "8c3c65fde3d14bbe51d20970efd5f0ba99470c95e63f0d8947f983ecc67b3764",  # EV-0043
        "65765ec832127f5046aaf4a66f991f7f5a8fe5e566ee1ae79491dc711a1caa43",  # EV-0051
        "c0fdca0c30452f7f1012726b2c626bb1d4ead40c71926271643d6f4b6e4a4450",  # EV-0054
        "6b517928e423f114fb14b51366ec3e4a2f4d48938e8436720d09f0b3b6ad1524",  # EV-0055
        "bf1a6e6df52f62f65cb16d5475c02317a386039e1f288ad1ce2637d574056f1f",  # EV-0043 replacement 1
        "72fa7d46ccec0074297bc0baecda4a56aff5748617b7d1f742c7caaf8a798988",  # EV-0051 replacement
        "33d85829ea42912a6f124a0b5491bf99e93e5af370c28cd2bc9cd9124104802f",  # EV-0043 replacement 2
        "4fac17b4119e0f8b1484913e9a772cfe4678da187ef47c57747abd5c7ce12b40",  # EV-0010 replacement
        "df4b0c9aaf6757c66d361319e6f30fd6e1d78e60f26a8714a892389fee045de7",  # EV-0038 replacement 1
        "25eaf18e23f4f63e43c9e84ab6f7c0afd2328cc8ba555424d4256f2d6252d996",  # EV-0039 replacement
        "4c50489ca6436721193dd5e9f7af83662718c4d0d89672593a9e4c30c2699b1e",  # EV-0043 replacement 3
        "730cf03bbe26ee5d83c8dd8bf4798ac61becab228dc56f5e8f176bd49d8c4eb4",  # EV-0038 replacement 2
        "26f93f865d88a1b70a543de77ea0f94003c0ce4766ec82843575edf37019208e",  # EV-0043 replacement 4
        "64e20b163765cee5363085c9dda09a03dd25a47138c1774aa11063be8ffa96f4",  # EV-0071
        "c0e0ff2cad1460f0b44864d54045ae138670839bf7041048dec7a5d1039c4eae",  # EV-0074
        "12f1f2890397c1df674f0202c4562d20092555137e2c2b7ae38c1178504045fe",  # EV-0076
    }
)

RECORD_KEYS = (
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

JsonRecord = dict[str, Any]
Predicate = Callable[[JsonRecord], bool]


def _label(row: JsonRecord, name: str) -> int:
    return int(row[name])


def jigsaw_strata() -> list[tuple[str, Predicate, int]]:
    """Approved Jigsaw strata in deterministic selection order."""
    return [
        ("jigsaw/idh", lambda r: _label(r, "identity_hate") == 1, 12),
        (
            "jigsaw/threat-no-idh",
            lambda r: _label(r, "identity_hate") == 0 and _label(r, "threat") == 1,
            10,
        ),
        (
            "jigsaw/severe-no-idh-no-threat",
            lambda r: (
                _label(r, "identity_hate") == 0
                and _label(r, "threat") == 0
                and _label(r, "severe_toxic") == 1
            ),
            10,
        ),
        (
            "jigsaw/toxic-only",
            lambda r: (
                _label(r, "toxic") == 1
                and _label(r, "severe_toxic") == 0
                and _label(r, "obscene") == 0
                and _label(r, "threat") == 0
                and _label(r, "insult") == 0
                and _label(r, "identity_hate") == 0
            ),
            12,
        ),
        (
            "jigsaw/mixed/toxic-obscene-insult",
            _toxic_mix(obscene=True, insult=True),
            7,
        ),
        ("jigsaw/mixed/toxic-insult", _toxic_mix(obscene=False, insult=True), 3),
        ("jigsaw/mixed/toxic-obscene", _toxic_mix(obscene=True, insult=False), 3),
        ("jigsaw/single/obscene", _single("obscene"), 1),
        ("jigsaw/single/insult", _single("insult"), 1),
        (
            "jigsaw/single/obscene-insult",
            lambda r: _no_rare(r)
            and _label(r, "toxic") == 0
            and _label(r, "obscene") == 1
            and _label(r, "insult") == 1,
            1,
        ),
        ("jigsaw/clean", lambda r: all(_label(r, name) == 0 for name in JIGSAW_LABELS), 20),
    ]


def _no_rare(row: JsonRecord) -> bool:
    return (
        _label(row, "severe_toxic") == 0
        and _label(row, "threat") == 0
        and _label(row, "identity_hate") == 0
    )


def _toxic_mix(*, obscene: bool, insult: bool) -> Predicate:
    return lambda r: (
        _no_rare(r)
        and _label(r, "toxic") == 1
        and _label(r, "obscene") == int(obscene)
        and _label(r, "insult") == int(insult)
    )


def _single(name: str) -> Predicate:
    other = "insult" if name == "obscene" else "obscene"
    return lambda r: (
        _no_rare(r)
        and _label(r, "toxic") == 0
        and _label(r, name) == 1
        and _label(r, other) == 0
    )


def cold_quotas() -> dict[tuple[int, int, str], int]:
    """Approved COLD cell x topic quotas."""
    return {
        (0, 0, "gender"): 3,
        (0, 0, "race"): 2,
        (0, 0, "region"): 2,
        (0, 3, "gender"): 1,
        (0, 3, "race"): 1,
        (0, 3, "region"): 1,
        (1, 1, "gender"): 1,
        (1, 1, "race"): 1,
        (1, 1, "region"): 1,
        (1, 2, "gender"): 3,
        (1, 2, "race"): 2,
        (1, 2, "region"): 2,
    }


JIGSAW_FLOORS = {
    "toxic": 54,
    "severe_toxic": 10,
    "obscene": 28,
    "threat": 10,
    "insult": 25,
    "identity_hate": 12,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_outside_repo(path: Path) -> None:
    """Refuse raw inputs located inside the repository (keep raw data out of Git)."""
    resolved = path.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError("raw input must live outside the repository")


def verify_file_digest(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(
            f"input digest mismatch: expected {expected}, got {actual}"
        )


def rank_key(seed: int, source: str, stratum: str, text: str) -> str:
    """Deterministic, PRNG-free selection key."""
    payload = f"{RANK_PREFIX}|{seed}|{source}|{stratum}|{text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[JsonRecord]:
    records: list[JsonRecord] = []
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at line {lineno}: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise TypeError(f"line {lineno} is not a JSON object")
        records.append(row)
    return records


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_jigsaw_rows(rows: list[JsonRecord]) -> None:
    seen: set[str] = set()
    for lineno, row in enumerate(rows, start=1):
        for name in JIGSAW_LABELS:
            if name not in row:
                raise ValueError(f"jigsaw row {lineno}: missing label {name}")
            if not _is_int(row[name]) or row[name] not in (0, 1):
                raise ValueError(f"jigsaw row {lineno}: {name} must be 0 or 1")
        text = row.get("comment_text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"jigsaw row {lineno}: missing comment_text")
        if text in seen:
            raise ValueError(f"jigsaw row {lineno}: duplicate comment_text")
        seen.add(text)


def validate_cold_rows(rows: list[JsonRecord]) -> None:
    seen: set[str] = set()
    for lineno, row in enumerate(rows, start=1):
        if row.get("split") != "test":
            raise ValueError(f"cold row {lineno}: split must be 'test'")
        label = row.get("label")
        fine = row.get("fine-grained-label")
        if not _is_int(label) or label not in (0, 1):
            raise ValueError(f"cold row {lineno}: label must be 0 or 1")
        if not _is_int(fine) or fine not in (0, 1, 2, 3):
            raise ValueError(f"cold row {lineno}: invalid fine-grained-label")
        if (label == 1) != (fine in (1, 2)):
            raise ValueError(f"cold row {lineno}: label/fine-grained inconsistent")
        if row.get("topic") not in COLD_TOPICS:
            raise ValueError(f"cold row {lineno}: invalid topic")
        text = row.get("TEXT")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"cold row {lineno}: missing TEXT")
        if text in seen:
            raise ValueError(f"cold row {lineno}: duplicate TEXT")
        seen.add(text)


def load_source(path: str | os.PathLike[str], source: str) -> list[JsonRecord]:
    resolved = Path(path).resolve()
    ensure_outside_repo(resolved)
    if not resolved.is_file():
        raise ValueError(f"{source} input file not found")
    verify_file_digest(resolved, PINNED_SHA256[source])
    rows = read_jsonl(resolved)
    if source == "jigsaw":
        validate_jigsaw_rows(rows)
    else:
        validate_cold_rows(rows)
    return rows


def _worst_case_min(pool: list[JsonRecord], take: int, label: str) -> int:
    without = sum(1 for row in pool if _label(row, label) == 0)
    return max(0, take - without)


def check_pool_guarantees(rows: list[JsonRecord]) -> None:
    """Verify quota feasibility and the worst-case label floors before selection."""
    strata = jigsaw_strata()
    pools = [
        (name, take, [row for row in rows if predicate(row)])
        for name, predicate, take in strata
    ]
    covered = sum(len(pool) for _, _, pool in pools)
    if covered != len(rows):
        raise ValueError(
            "jigsaw strata are not an exact partition: "
            f"{covered} covered vs {len(rows)} rows"
        )
    for name, take, pool in pools:
        if len(pool) < take:
            raise ValueError(f"jigsaw stratum {name}: pool {len(pool)} < take {take}")
    for label, floor in JIGSAW_FLOORS.items():
        guaranteed = sum(
            _worst_case_min(pool, take, label) for _, take, pool in pools
        )
        if guaranteed < floor:
            raise ValueError(
                f"jigsaw guarantee for {label}: {guaranteed} < approved floor {floor}"
            )


def check_cold_pools(rows: list[JsonRecord]) -> None:
    for (label, fine, topic), take in cold_quotas().items():
        pool = [
            row
            for row in rows
            if row["label"] == label
            and row["fine-grained-label"] == fine
            and row["topic"] == topic
        ]
        if len(pool) < take:
            raise ValueError(
                "cold cell "
                f"label{label}-fg{fine}/{topic}: pool {len(pool)} < take {take}"
            )


def has_pii(text: str) -> bool:
    """ADR-001 / REQ-INV-005: detect supported PII patterns or reviewed IDs."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest in REVIEWED_PII_TEXT_SHA256 or bool(
        _IPV4_RE.search(text)
        or _EMAIL_RE.search(text)
        or _PERSONAL_IDENTIFIER_RE.search(text)
    )


def _row_has_pii(row: JsonRecord, text_field: str) -> bool:
    text = row.get(text_field)
    return isinstance(text, str) and has_pii(text)


def exclude_pii_rows(
    rows: Sequence[JsonRecord], text_field: str
) -> list[JsonRecord]:
    """ADR-001 / REQ-INV-005: keep rows without supported PII patterns."""
    return [row for row in rows if not _row_has_pii(row, text_field)]


def select_jigsaw(
    rows: list[JsonRecord],
    seed: int = SEED,
    *,
    exclude_pii: bool = True,
) -> list[tuple[str, JsonRecord]]:
    selected: list[tuple[str, JsonRecord]] = []
    for name, predicate, take in jigsaw_strata():
        pool = [row for row in rows if predicate(row)]
        if exclude_pii:
            pool = [row for row in pool if not _row_has_pii(row, "comment_text")]
        ranked = sorted(
            pool, key=lambda row: rank_key(seed, "jigsaw", name, row["comment_text"])
        )
        if len(ranked) < take:
            raise ValueError(f"jigsaw stratum {name}: insufficient rows")
        selected.extend((name, row) for row in ranked[:take])
    return selected


def select_cold(
    rows: list[JsonRecord],
    seed: int = SEED,
    *,
    exclude_pii: bool = True,
) -> list[tuple[str, JsonRecord]]:
    selected: list[tuple[str, JsonRecord]] = []
    quotas = cold_quotas()
    for label, fine in COLD_CELLS:
        for topic in COLD_TOPICS:
            take = quotas[(label, fine, topic)]
            stratum = f"cold/label{label}-fg{fine}/{topic}"
            pool = [
                row
                for row in rows
                if row["label"] == label
                and row["fine-grained-label"] == fine
                and row["topic"] == topic
            ]
            if exclude_pii:
                pool = [row for row in pool if not _row_has_pii(row, "TEXT")]
            ranked = sorted(
                pool, key=lambda row: rank_key(seed, "cold", stratum, row["TEXT"])
            )
            if len(ranked) < take:
                raise ValueError(f"cold stratum {stratum}: insufficient rows")
            selected.extend((stratum, row) for row in ranked[:take])
    return selected


def _jigsaw_pool_for_stratum(
    stratum: str, rows: list[JsonRecord]
) -> list[JsonRecord]:
    for name, predicate, _ in jigsaw_strata():
        if name == stratum:
            return [row for row in rows if predicate(row)]
    raise ValueError(f"unknown jigsaw stratum: {stratum}")


def _cold_pool_for_stratum(
    stratum: str, rows: list[JsonRecord]
) -> list[JsonRecord]:
    for label, fine in COLD_CELLS:
        for topic in COLD_TOPICS:
            if f"cold/label{label}-fg{fine}/{topic}" == stratum:
                return [
                    row
                    for row in rows
                    if row["label"] == label
                    and row["fine-grained-label"] == fine
                    and row["topic"] == topic
                ]
    raise ValueError(f"unknown cold stratum: {stratum}")


def replace_pii_selected(
    selected: list[tuple[str, JsonRecord]],
    rows: list[JsonRecord],
    seed: int,
    source: str,
    text_field: str,
) -> list[tuple[str, JsonRecord]]:
    """ADR-001 / REQ-INV-005: replace selected PII rows in place."""
    selected_texts = {row[text_field] for _, row in selected}
    result: list[tuple[str, JsonRecord]] = []
    for stratum, row in selected:
        if not _row_has_pii(row, text_field):
            result.append((stratum, row))
            continue
        pool = (
            _jigsaw_pool_for_stratum(stratum, rows)
            if source == "jigsaw"
            else _cold_pool_for_stratum(stratum, rows)
        )
        candidates = [
            candidate
            for candidate in pool
            if not _row_has_pii(candidate, text_field)
            and candidate[text_field] not in selected_texts
        ]
        ranked = sorted(
            candidates,
            key=lambda candidate: rank_key(
                seed, source, stratum, candidate[text_field]
            ),
        )
        if not ranked:
            raise ValueError(
                f"{source} stratum {stratum}: no PII-free replacement available"
            )
        replacement = ranked[0]
        selected_texts.add(replacement[text_field])
        result.append((stratum, replacement))
    return result


def _check_selected_jigsaw(rows: list[JsonRecord]) -> None:
    counts = {name: sum(_label(row, name) for row in rows) for name in JIGSAW_LABELS}
    for name, floor in JIGSAW_FLOORS.items():
        if counts[name] < floor:
            raise ValueError(f"selected jigsaw data violates {name} floor {floor}")
    clean = sum(
        1 for row in rows if all(_label(row, name) == 0 for name in JIGSAW_LABELS)
    )
    if clean != 20:
        raise ValueError(f"selected clean controls: {clean} != 20")
    idh_negative = sum(1 for row in rows if _label(row, "identity_hate") == 0)
    if idh_negative != 68:
        raise ValueError(f"selected identity_hate-negative rows: {idh_negative} != 68")
    toxic_idh_negative = sum(
        1
        for row in rows
        if _label(row, "toxic") == 1 and _label(row, "identity_hate") == 0
    )
    if toxic_idh_negative < 44:
        raise ValueError(
            f"selected toxic identity_hate-negative rows: {toxic_idh_negative} < 44"
        )
    high_risk = sum(
        1
        for row in rows
        if any(_label(row, name) == 1 for name in ("severe_toxic", "threat", "identity_hate"))
    )
    if high_risk < 32:
        raise ValueError(f"selected high-risk slice: {high_risk} < 32")


def _jigsaw_record(row: JsonRecord, stratum: str, index: int) -> JsonRecord:
    text = row["comment_text"]
    return {
        "eval_id": f"EV-{index:04d}",
        "source": "jigsaw",
        "source_split": None,
        "source_language": "en",
        "text": text,
        "label_scheme": JIGSAW_SCHEME,
        "labels": {name: _label(row, name) for name in JIGSAW_LABELS},
        "topic": None,
        "selection_stratum": stratum,
        "selection_seed": SEED,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _cold_record(row: JsonRecord, stratum: str, index: int) -> JsonRecord:
    text = row["TEXT"]
    return {
        "eval_id": f"EV-{index:04d}",
        "source": "cold",
        "source_split": row["split"],
        "source_language": "zh",
        "text": text,
        "label_scheme": COLD_SCHEME,
        "labels": {
            "label": int(row["label"]),
            "fine-grained-label": int(row["fine-grained-label"]),
        },
        "topic": row["topic"],
        "selection_stratum": stratum,
        "selection_seed": SEED,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def build_records(
    jigsaw_rows: list[JsonRecord],
    cold_rows: list[JsonRecord],
    seed: int = SEED,
    *,
    allow_fallback_95: bool = False,
) -> list[JsonRecord]:
    """ADR-001 / REQ-INV-005: select the PII-free 80/20 set."""
    if seed != SEED:
        raise ValueError(f"seed must be the approved value {SEED}")
    validate_jigsaw_rows(jigsaw_rows)
    validate_cold_rows(cold_rows)

    fallback = False
    try:
        check_pool_guarantees(jigsaw_rows)
        check_cold_pools(cold_rows)
        jigsaw_base = select_jigsaw(jigsaw_rows, seed, exclude_pii=False)
        cold_base = select_cold(cold_rows, seed, exclude_pii=False)
        if len(jigsaw_base) != 80 or len(cold_base) != 20:
            raise ValueError("selection produced an unexpected record count")
        jigsaw_selected = replace_pii_selected(
            jigsaw_base, jigsaw_rows, seed, "jigsaw", "comment_text"
        )
        cold_selected = replace_pii_selected(
            cold_base, cold_rows, seed, "cold", "TEXT"
        )
        _check_selected_jigsaw([row for _, row in jigsaw_selected])
    except ValueError:
        if not allow_fallback_95:
            raise
        jigsaw_selected = [
            (stratum, row)
            for stratum, row in select_jigsaw(
                jigsaw_rows, seed, exclude_pii=False
            )
            if not _row_has_pii(row, "comment_text")
        ]
        cold_selected = [
            (stratum, row)
            for stratum, row in select_cold(
                cold_rows, seed, exclude_pii=False
            )
            if not _row_has_pii(row, "TEXT")
        ]
        fallback = True
        if len(jigsaw_selected) + len(cold_selected) != 95:
            raise ValueError(
                "approved 95 fallback expected exactly 95 records"
            )

    records: list[JsonRecord] = []
    for stratum, row in jigsaw_selected:
        records.append(_jigsaw_record(row, stratum, len(records) + 1))
    for stratum, row in cold_selected:
        records.append(_cold_record(row, stratum, len(records) + 1))

    for record in records:
        if set(record) != set(RECORD_KEYS):
            raise ValueError("constructed record does not match the approved schema")
        if has_pii(record["text"]):
            raise ValueError(
                f"detected PII in generated record {record['eval_id']}"
            )

    if not fallback:
        _check_selected_cold(records)
    return records


def _check_selected_cold(records: list[JsonRecord]) -> None:
    cold = [record for record in records if record["source"] == "cold"]
    if len(cold) != 20:
        raise ValueError(f"selected COLD records: {len(cold)} != 20")
    cells = Counter(
        (record["labels"]["label"], record["labels"]["fine-grained-label"])
        for record in cold
    )
    expected_cells = {(0, 0): 7, (0, 3): 3, (1, 1): 3, (1, 2): 7}
    if dict(cells) != expected_cells:
        raise ValueError("selected COLD cell counts do not match the approved quotas")
    topics = Counter(record["topic"] for record in cold)
    if dict(topics) != {"gender": 8, "race": 6, "region": 6}:
        raise ValueError("selected COLD topic counts do not match 8/6/6")


def write_records(records: Sequence[JsonRecord], out: Path) -> None:
    """Atomically write validated records as JSONL."""
    payload = "".join(
        json.dumps(record, ensure_ascii=False) + "\n" for record in records
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    try:
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, out)
    finally:
        if tmp.exists():
            tmp.unlink()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jigsaw", required=True)
    parser.add_argument("--cold", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--allow-fallback-95", action="store_true")
    args = parser.parse_args(argv)
    try:
        jigsaw_rows = load_source(args.jigsaw, "jigsaw")
        cold_rows = load_source(args.cold, "cold")
        records = build_records(
            jigsaw_rows,
            cold_rows,
            args.seed,
            allow_fallback_95=args.allow_fallback_95,
        )
        write_records(records, Path(args.out))
    except (ValueError, TypeError, OSError) as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1
    if len(records) == 95:
        print(f"FALLBACK 95: wrote {len(records)} records to {args.out}")
    else:
        print(f"WROTE {len(records)} records to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
