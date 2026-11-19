"""Convert a recorded live-run responses file into a gate-4 replay artifact (REQ-INV-005).

This is a PURE converter and validator: it reads a JSONL responses file, checks it, and
writes a replay artifact of the shape the runner consumes. It has NO provider SDK, reads
NO credential environment variables, and NEVER touches the network. There is deliberately
no ``--live`` mode — there is no pipeline in ``src/`` to record from yet, and inventing a
live/credential path now would open an unapproved credential surface.

Recording path (human-run; CI and the offline tier never do this):

  1. A human runs the (future) analysis pipeline against the fixed corpus
     ``test/eval/moderation_eval.jsonl`` and writes one response per corpus row to a
     responses file, e.g. ``responses_prompt_v1.1.jsonl``. That file is produced by
     whatever future pipeline exists — not by this script.
  2. The human converts and validates it here:

         python scripts/record_replay.py \
             --from responses_prompt_v1.1.jsonl \
             --out test/eval/replay/prompt_v1.1.jsonl

  3. The human reviews and commits the replay under ``test/eval/replay/<tag>.jsonl`` and
     passes it to gate 4 via ``--replay``. A prompt change with no committed replay does
     not merge (gate 4 blocks under ``--strict``).

Responses file format — one JSON object per line, comment lines (``#``) skipped::

    {"eval_id": "EV-0001", "verdict": "block"}   # verdict ∈ {allow, block, escalate}

Validation (fail closed, writes nothing on error):
  - every row has ``eval_id`` and ``verdict``; ``verdict`` ∈ {allow, block, escalate};
  - no duplicate ``eval_id``;
  - no ``eval_id`` that is absent from the corpus (typos / stale ids are rejected);
  - every corpus ``eval_id`` is covered — an incomplete replay is refused, because a
    partial replay would otherwise masquerade as evidence.

Output: a replay artifact with the same ``{"eval_id","verdict"}`` lines, plus a
provenance comment header, at ``--out``.

Implements REQ-INV-005; pays down TD-1 (gate 4 evidence production).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_runner

DEFAULT_CORPUS = eval_runner.DEFAULT_CORPUS
VALID_DISPOSITIONS = eval_runner.VALID_DISPOSITIONS


class ConversionError(Exception):
    """The responses file cannot be turned into a valid, complete replay artifact."""


def _iter_rows(path: Path) -> list[dict[str, object]]:
    """Load JSONL rows, skipping blank/comment lines; raise on malformed JSON."""
    if not path.exists():
        raise ConversionError(f"responses file not found: {path}")
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ConversionError(f"{path}:{lineno}: invalid JSON — {exc}") from exc
            if not isinstance(item, dict):
                raise ConversionError(f"{path}:{lineno}: each row must be a JSON object")
            rows.append(item)
    if not rows:
        raise ConversionError(f"responses file is empty: {path}")
    return rows


def convert(responses: Path, corpus: Path) -> dict[str, str]:
    """Validate ``responses`` against ``corpus`` and return the {eval_id: verdict} map.

    Raises ``ConversionError`` (with an actionable message) on any defect; writes nothing.
    """
    corpus_ids = {str(row["eval_id"]) for row in eval_runner.load_corpus(corpus)}
    replay: dict[str, str] = {}
    for index, item in enumerate(_iter_rows(responses), 1):
        eval_id = str(item.get("eval_id", "")).strip()
        verdict = str(item.get("verdict", "")).strip()
        if not eval_id:
            raise ConversionError(f"row #{index}: missing eval_id")
        if verdict not in VALID_DISPOSITIONS:
            raise ConversionError(
                f"row #{index} ({eval_id}): verdict must be one of "
                f"{sorted(VALID_DISPOSITIONS)}, got {item.get('verdict')!r}"
            )
        if eval_id in replay:
            raise ConversionError(f"row #{index}: duplicate eval_id {eval_id}")
        if eval_id not in corpus_ids:
            raise ConversionError(
                f"row #{index}: eval_id {eval_id} is not in the corpus {corpus} "
                "(stale or misspelled id)"
            )
        replay[eval_id] = verdict
    uncovered = sorted(corpus_ids - set(replay))
    if uncovered:
        raise ConversionError(
            f"{len(uncovered)} corpus eval_id(s) are uncovered by the responses file "
            f"(first: {uncovered[:10]}{' …' if len(uncovered) > 10 else ''}); a partial "
            "replay is not evidence — record a verdict for every corpus row"
        )
    return replay


def write_replay(replay: dict[str, str], out: Path, *, source: Path, corpus: Path) -> None:
    """Write the replay artifact, preserving corpus order, with a provenance header."""
    corpus_ids = [str(row["eval_id"]) for row in eval_runner.load_corpus(corpus)]
    lines = [
        f"# Replay artifact converted from {source.name} by scripts/record_replay.py.",
        f"# Corpus: {corpus}. {len(replay)} rows, every corpus eval_id covered.",
        "# Converted offline from a human-recorded live run; no provider call at convert time.",
        "# Format: one JSON object per line, {\"eval_id\":..., \"verdict\": allow|block|escalate}.",
    ]
    lines.extend(
        json.dumps({"eval_id": eval_id, "verdict": replay[eval_id]}) for eval_id in corpus_ids
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a human-recorded live-run responses file into a gate-4 replay artifact. "
            "Pure offline transform: no provider SDK, no credentials, no network. The "
            "responses file is produced by the (future) analysis pipeline; this script only "
            "validates and reshapes it, and the human commits the result under "
            "test/eval/replay/<tag>.jsonl."
        ),
        epilog=(
            "Example:\n"
            "  python scripts/record_replay.py \\\n"
            "      --from responses_prompt_v1.1.jsonl \\\n"
            "      --out test/eval/replay/prompt_v1.1.jsonl"
        ),
    )
    parser.add_argument(
        "--from",
        dest="source",
        required=True,
        type=Path,
        help="JSONL responses file from a live run (one {\"eval_id\",\"verdict\"} per line).",
    )
    parser.add_argument(
        "--out",
        dest="out",
        required=True,
        type=Path,
        help="Replay artifact to write, e.g. test/eval/replay/<tag>.jsonl.",
    )
    parser.add_argument(
        "--corpus",
        dest="corpus",
        type=Path,
        default=DEFAULT_CORPUS,
        help=f"Fixed evaluation corpus (default: {DEFAULT_CORPUS}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on a written artifact, nonzero on any validation error."""
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        replay = convert(args.source, args.corpus)
    except (ConversionError, eval_runner.EvalError) as exc:
        print(f"RECORD FAIL: {exc}")
        return 1
    write_replay(replay, args.out, source=args.source, corpus=args.corpus)
    print(
        f"RECORD OK: wrote {len(replay)} rows to {args.out}. "
        "Review and commit it under test/eval/replay/ before a prompt PR can pass gate 4."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
