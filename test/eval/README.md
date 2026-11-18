# Fixed moderation evaluation set (REQ-INV-005)

> **Content warning:** this corpus contains real offensive, hateful and abusive
> text from public moderation datasets. It is for offline evaluation only, not for
> display, training or redistribution as raw source data. Handle it according to
> the course data-handling rules.

`moderation_eval.jsonl` is the fixed evaluation corpus intended for
replay by the semantic evaluation gate (CI gate 4) whenever a prompt or model
configuration changes (REQ-INV-005, INV-5). It contains **100 records: 80 Jigsaw (English) +
20 COLD (Chinese)**, selected with the documented deterministic procedure and seed
`5351`.

This revision removes the five previously flagged PII-bearing records and replaces
them with PII-free records from the same strata. A local name/handle review also
confirmed additional direct personal names and account identifiers that the
pattern detector missed; those records were replaced from the same strata.
Selected records whose text matches a supported PII pattern or a reviewed digest
are replaced in place, and those texts are not eligible as replacements. Generic
URLs are not treated as PII unless they contain a personal identifier. See
[NOTICE.md](NOTICE.md) for licensing, attribution and the required changes
statement.

The corpus path is fixed at `test/eval/moderation_eval.jsonl`. For prompt/model
changes, `scripts/check_semantic_eval.py` uses this corpus, the human-authored
`test/eval/expectation_policy.yaml`, and an explicitly configured recorded replay
artifact. The replay runner is implemented in PR #47. Gate 4 currently warns
instead of blocking when a replay is missing or quality thresholds are missed,
unless `--strict` is enabled; an evaluated high-severity safety escape or
uncovered row remains a hard failure. Strict activation remains tracked as TD-1.
A warn-only pass without a replay is not evidence that semantic metrics passed.
The offline validator in `test/offline/test_evaluation_dataset.py` checks corpus
structure, not model quality.

## Licensing, attribution and provenance

Licensing and attribution are recorded in [NOTICE.md](NOTICE.md): the Jigsaw
dataset is **CC0 1.0** and its underlying Wikipedia text is **CC BY-SA 3.0**;
COLD is **Apache-2.0**. This documentation records the source terms and changes;
it does not assert a separate project-owner authorization to publish the derived
corpus. The applicable upstream license terms govern; see `NOTICE.md` for
attribution and the changes statement.

Sources and attribution:

- **Jigsaw** — Jigsaw Toxic Comment Classification Challenge, Google/Jigsaw via
  Kaggle (2018):
  <https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge>.
  Local labeled extract: 5,000 rows, 2,643,655 bytes; only the six native label
  columns and the comment text are consumed. Retrieved **2026-11-16**; the
  pinned extract hash below identifies the local input. No separate immutable
  upstream revision identifier was recorded.
- **COLD** — official COLDataset repository, THU CoAI, *COLD: A Benchmark for
  Chinese Offensive Language Detection* (EMNLP 2022):
  <https://github.com/thu-coai/COLDataset>. Local extract: 1,000 rows,
  236,229 bytes, all from the native `test` split. Source commit:
  [`a0c55a945497ab58e94aef491180e1cf88ffb864`](https://github.com/thu-coai/COLDataset/commit/a0c55a945497ab58e94aef491180e1cf88ffb864)
  (2023-03-20); retrieved **2026-11-16**.

Pinned input evidence (the builder refuses any other input):

| Source | Bytes | SHA-256 |
|---|---:|---|
| Jigsaw extract | 2,643,655 | `ae2968a0248be3b99b636a3924e2895034da12bc307ead40da22593b893761e3` |
| COLD extract | 236,229 | `df4cf25b99152f6c93443371095f2e0e6e54506005cf82e6add9b13e89c82d53` |

The raw extracts are **not** in Git and must stay outside the repository; the
builder rejects inputs whose resolved path is inside the repository. Only this
derived subset is committed. Source row identifiers are omitted. `text_sha256` is
a content-integrity digest of the verbatim text, not a source row ID or a direct
mapping to an upstream record.

## Generated corpus counts and hash

These values are calculated from the committed generated output, not hand-entered:

| Item | Value |
|---|---|
| Total records | 100 |
| Jigsaw / COLD | 80 / 20 |
| Corpus bytes | 75,817 |
| Corpus SHA-256 | `37a1135ec2e563f39709d1d01fefb8229023c490469545039db80b0729128ed1` |

Jigsaw label totals: `toxic` 56, `severe_toxic` 14, `obscene` 35, `threat` 12,
`insult` 35, `identity_hate` 12; clean controls 20. COLD retains label 0/1 = 10/10,
fine-grained cells 7/3/3/7, and topic balance 8/6/6.

## PII remediation and manual review

The five previously flagged PII-bearing records were replaced from the same
strata. A local review of the generated records and their replacements confirmed
additional direct personal names and account identifiers that the pattern detector
missed; those texts were also replaced from the same strata. The builder detects
valid IPv4 addresses, email addresses, and personal user identifiers/signatures
(`@handle`, `/u/`, `/user/`, `u/`, and `user:` forms), plus the reviewed text
digests. Generic URLs alone are not PII. A record that still matches a supported
PII pattern or a reviewed digest is rejected before any output is written.

### Manual review status

**Operator manual PII review: complete.** Reviewer: **DA Buna**. Date:
**2026-11-19**. All 100 final records passed the manual PII review. Confirmed
cases were replaced from the same strata. This records the PII-review result; it
is not a manual validation of label semantics or model behavior.

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
| `toxic` | ≥ 54 | 56 |
| `severe_toxic` | ≥ 10 | 14 |
| `obscene` | ≥ 28 | 35 |
| `threat` | ≥ 10 | 12 |
| `insult` | ≥ 25 | 35 |
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
- Both local extracts were retrieved on 2026-11-16. The Jigsaw extract is pinned
  by its hash above; the COLD source commit is recorded above.
- Language is a source-level declaration, not per-record detection.
- COLD contributes only the native `test` split; train/dev-only binary semantics
  are cited for context but no train/dev rows are included.
- The dataset does not define model expectations or thresholds; those are kept in
  `expectation_policy.yaml`. Gate 4 requires an explicit recorded replay artifact,
  and strict activation remains tracked as TD-1.
- Changing the file content, seed, quotas or schema invalidates prior semantic
  baselines and requires owner review.

## Regeneration (local only)

The raw extracts must exist outside the repository; they are not distributed here.
The builder is stdlib-only, performs no network access, verifies the pinned input
digests and quota guarantees, excludes detected PII before selection, never logs
source text, and writes nothing if any check fails. The approved 95-record fallback
is available only with the explicit `--allow-fallback-95` flag; the primary target
is 100 records with same-stratum replacement.

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
