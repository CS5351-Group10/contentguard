# Fixed moderation evaluation set (REQ-INV-005)

`moderation_eval.jsonl` is the approved, fixed evaluation corpus intended for
replay by the semantic evaluation gate (CI gate 4) whenever a prompt or model
configuration changes (REQ-INV-005, INV-5). It contains **100 records: 80 Jigsaw (English) +
20 COLD (Chinese)**, selected with the approved deterministic procedure and seed
`5351`.

The file path is fixed: `scripts/check_semantic_eval.py` looks only for
`test/eval/moderation_eval.jsonl`. Today that gate checks existence only and its
replay harness is still debt item TD-1, so this file does **not** yet cause gate 4
to compute metrics. It is the fixed corpus the harness will consume; the offline
validator in `test/offline/test_evaluation_dataset.py` is the schema authority.

## Source approval, provenance and attribution

The project owner confirmed (2026-11-17) that **both sources are approved for this
project**, including committing this derived 100-record evaluation file to this
repository. This is a project-level approval recorded by the owner; **no license
identifier is asserted here**, because no specific license text was verified for
the local extracts during this session. The raw extracts contain no
embedded license metadata. The owner reviews this section before the PR is
submitted; removing IDs or selecting fewer rows is not, by itself, license evidence.

Sources and attribution:

- **Jigsaw** — Jigsaw Toxic Comment Classification Challenge, Google/Jigsaw via
  Kaggle (2018):
  <https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge>.
  Local labeled extract: 5,000 rows, 2,643,655 bytes; only the six native label
  columns and the comment text are consumed.
- **COLD** — official COLDataset repository, THU CoAI, *COLD: A Benchmark for
  Chinese Offensive Language Detection* (EMNLP 2022):
  <https://github.com/thu-coai/COLDataset>. Local extract: 1,000 rows,
  236,229 bytes, all from the native `test` split.

Pinned input evidence (the builder refuses any other input):

| Source | Bytes | SHA-256 |
|---|---:|---|
| Jigsaw extract | 2,643,655 | `ae2968a0248be3b99b636a3924e2895034da12bc307ead40da22593b893761e3` |
| COLD extract | 236,229 | `df4cf25b99152f6c93443371095f2e0e6e54506005cf82e6add9b13e89c82d53` |

The raw extracts are **not** in Git and must stay outside the repository; the
builder rejects inputs whose resolved path is inside the repository. Only this
derived subset is committed. Raw record identifiers are not included; records carry
a SHA-256 of the text instead.

## Label semantics (native labels preserved)

The two label schemes are recorded separately and are **not** mapped onto each
other. There is no unified `is_hate`/`is_toxic` ground truth in this file, and no
model-generated label is used as ground truth.

**Jigsaw** — six independent binary labels, each `0`/`1`: `toxic`,
`severe_toxic`, `obscene`, `threat`, `insult`, `identity_hate`. They are kept as
six independent multi-label values; no aggregate label is stored. The
high-risk coverage slice used below (`severe_toxic` OR `threat` OR
`identity_hate`) is a reporting slice only, not a stored label.

**COLD** — native labels, with the definitions documented by the official
COLDataset README:

- Binary `label` (train/dev definition): `0` = safe, `1` = offensive.
- Test `fine-grained-label`: `0` = safe (other-Non-offen), `1` = attack
  individual, `2` = attack group, `3` = safe (anti-bias).

This extract is entirely the COLD `test` split, so both the binary `label` and the
test fine-grained label are preserved exactly as stored. In this extract they are
consistent with the codebook: `label = 1` iff `fine-grained-label` is `1` or `2`.
No COLD value is renamed or mapped to a Jigsaw label.

## Selection method

- Seed: **5351** (stored as `selection_seed` in every record).
- No PRNG. Each candidate is ranked by
  `sha256("contentguard-eval-v1|5351|<source>|<stratum>|<text>")` (UTF-8, lowercase
  hex, ascending); the lowest `k` per sub-stratum are selected. The key uses the
  text only, never a source row identifier.
- Jigsaw strata are disjoint label-pattern predicates, applied in the order below.
- COLD is stratified by native `(label, fine-grained-label, topic)` with fixed
  cell × topic quotas.
- `eval_id` values `EV-0001`–`EV-0100` are assigned deterministically: Jigsaw in
  stratum order then rank order, followed by COLD cell/topic order then rank order.

### Jigsaw quotas and guaranteed minima

Worst-case guarantees are computed from the observed pools before selection as
`max(0, k - (n - p))` per stratum (n = pool size, p = rows carrying the label),
summed over strata; the builder aborts if a floor is not guaranteed, and again if
the selected output misses it.

| Stratum | Take |
|---|---:|
| `identity_hate == 1` | 12 |
| `threat == 1`, `identity_hate == 0` | 10 |
| `severe_toxic == 1`, `identity_hate == 0`, `threat == 0` | 10 |
| `toxic` only | 12 |
| `toxic+obscene+insult` (no rare labels) | 7 |
| `toxic+insult` (no rare labels) | 3 |
| `toxic+obscene` (no rare labels) | 3 |
| `obscene` only | 1 |
| `insult` only | 1 |
| `obscene+insult` only | 1 |
| all six labels `0` (clean controls) | 20 |
| **Total** | **80** |

| Label / slice | Guaranteed floor | Final count |
|---|---:|---:|
| `toxic` | ≥ 54 | 55 |
| `severe_toxic` | ≥ 10 | 13 |
| `obscene` | ≥ 28 | 36 |
| `threat` | ≥ 10 | 11 |
| `insult` | ≥ 25 | 34 |
| `identity_hate` | 12 | 12 |
| `identity_hate`-negative controls | 68 | 68 |
| toxic & `identity_hate`-negative | ≥ 44 | 44 |
| clean controls (all six `0`) | 20 | 20 |
| high-risk slice (`severe_toxic` OR `threat` OR `identity_hate`) | ≥ 32 | 32 |

### COLD quotas

| `label` | `fine-grained-label` | Meaning | gender | race | region | total |
|---:|---:|---|---:|---:|---:|---:|
| 0 | 0 | safe (other-Non-offen) | 3 | 2 | 2 | 7 |
| 0 | 3 | safe (anti-bias) | 1 | 1 | 1 | 3 |
| 1 | 1 | attack individual | 1 | 1 | 1 | 3 |
| 1 | 2 | attack group | 3 | 2 | 2 | 7 |
| | | **Totals** | **8** | **6** | **6** | **20** |

Final COLD counts: label 0 = 10, label 1 = 10; cells 7/3/3/7; topics 8/6/6.

## Record schema

One JSON object per line; uniform keys with explicit nulls. `text` is the verbatim
source text; `text_sha256` is the SHA-256 of its UTF-8 bytes.

| Field | Type | Values |
|---|---|---|
| `eval_id` | string | `EV-0001`…`EV-0100`, unique and sequential |
| `source` | string | `jigsaw` or `cold` |
| `source_split` | string or null | `test` for COLD; **null** for Jigsaw (the local extract encodes no split; nothing is inferred from the file name) |
| `source_language` | string | `en` (Jigsaw) or `zh` (COLD); declared per source, not detected per row |
| `text` | string | verbatim source text |
| `label_scheme` | string | `jigsaw-six-independent-binary-v1` or `cold-test-binary-plus-finegrained-v1` |
| `labels` | object | Jigsaw: the six native `0`/`1` labels. COLD: `{"label": 0|1, "fine-grained-label": 0|1|2|3}` |
| `topic` | string or null | COLD: `gender`, `race`, `region`; Jigsaw: null |
| `selection_stratum` | string | approved stratum identifier (closed set) |
| `selection_seed` | int | `5351` |
| `text_sha256` | string | lowercase hex SHA-256 of `text` |

No source row IDs, no derived/unified labels, and no model-generated fields are
stored.

## Limitations

- This is a **coverage/diagnostic** set, **not a prevalence benchmark**. Rare
  classes are deliberately oversampled relative to their rate in the raw extracts,
  so aggregate rates here must not be read as population estimates. Use per-slice
  metrics only.
- Jigsaw's source split is unknown from the extract and is recorded as null.
- Language is a source-level declaration, not per-record detection.
- COLD contributes only the native `test` split; train/dev-only binary semantics
  are cited for context but no train/dev rows are included.
- The dataset does not define model expectations or thresholds, and it does not
  wire gate 4 (TD-1). A future harness must document how native labels map to
  advisory expectations.
- Changing the file content, seed, quotas or schema invalidates prior semantic
  baselines and requires owner review.

## Regeneration (local only)

The raw extracts must exist outside the repository; they are not distributed here.
The builder is stdlib-only, performs no network access, verifies the pinned input
digests and quota guarantees, never logs source text, and writes nothing if any
check fails.

```bash
python scripts/build_evaluation_dataset.py \
  --jigsaw /tmp/raw_jigsaw.jsonl \
  --cold /tmp/raw_cold.jsonl \
  --out test/eval/moderation_eval.jsonl \
  --seed 5351
```

Reproducibility check:

```bash
python scripts/build_evaluation_dataset.py \
  --jigsaw /tmp/raw_jigsaw.jsonl \
  --cold /tmp/raw_cold.jsonl \
  --out /tmp/rebuild.jsonl \
  --seed 5351
shasum -a 256 test/eval/moderation_eval.jsonl /tmp/rebuild.jsonl
```

Validation:

```bash
pytest test/offline/test_evaluation_dataset.py -v
pytest test/offline -v
ruff check src scripts test
mypy scripts test
python scripts/validate_requirements.py
```
