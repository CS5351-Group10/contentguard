# Third-Party Data Notice

This file records attribution, licensing and the changes made for the derived
evaluation corpus at `test/eval/moderation_eval.jsonl`. It applies to the derived
subset only; the raw source extracts are not distributed in this repository.

## Jigsaw

- **Source:** Jigsaw Toxic Comment Classification Challenge, Google/Jigsaw via
  Kaggle (2018).
- **URL:** <https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge>
- **Dataset license:** CC0 1.0.
- **Underlying text license:** the comments derive from Wikipedia text, which is
  licensed CC BY-SA 3.0.
- **Source version:** the upstream release was not separately versioned; the local
  extract is pinned by its SHA-256 in [README.md](README.md).
- **Retrieval date:** 2026-11-16.

## COLD

- **Source:** COLDataset, THU CoAI, *COLD: A Benchmark for Chinese Offensive
  Language Detection* (EMNLP 2022).
- **URL:** <https://github.com/thu-coai/COLDataset>
- **License:** Apache-2.0.
- **Source commit:** [`a0c55a945497ab58e94aef491180e1cf88ffb864`](https://github.com/thu-coai/COLDataset/commit/a0c55a945497ab58e94aef491180e1cf88ffb864)
  (2023-03-20).
- **Retrieval date:** 2026-11-16.

## Changes made

The following changes were made to produce the derived corpus:

- Selected a deterministic subset of 100 records (80 Jigsaw and 20 COLD) using the
  approved SHA-256 ranking procedure with seed `5351`.
- Excluded records whose text matches the builder's supported PII patterns: valid
  IPv4 addresses, email addresses, and personal user identifiers/signatures.
  Five previously flagged PII-bearing records were replaced from the same strata.
  Additional records confirmed during manual name/handle review were also
  replaced from the same strata, including replacement texts found to contain
  further identifiers.
- Preserved the native Jigsaw and COLD labels without mapping them onto each other.
- Omitted source row identifiers. Each `text_sha256` is a content-integrity digest
  of the verbatim text, not a source row ID or a direct mapping to an upstream record.
- Committed only the derived subset; no raw source extracts are redistributed.

The Jigsaw upstream release was not separately versioned; its local extract is
identified by the pinned hash in the README. This derived corpus is not endorsed
by the original authors or dataset providers. The upstream license terms continue to
govern the source data.
