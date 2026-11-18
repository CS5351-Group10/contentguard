"""CI gate 4: semantic evaluation for prompt/model changes (INV-5 / REQ-INV-005).

Behavior:
  - No PR context (local run / push): pass.
  - PR touches no prompt/model path: pass (not applicable).
  - PR touches a prompt/model path: replay the fixed evaluation set
    (test/eval/moderation_eval.jsonl) against the approved thresholds using
    scripts/eval_runner.py.

Fail-closed / honest-reporting contract (issue #26):
  - The replay artifact is resolved **explicitly** — ``--replay`` CLI arg, else the
    ``EVAL_REPLAY`` env var, else ``None``. It is NEVER defaulted to a shipped fixture:
    a fixture that always agrees is exactly the "check that cannot fail" this gate removes.
  - Corpus absent → today's state (PR #37 not on main); warns, or fails under ``--strict``.
  - Corpus present but no replay artifact for this prompt version → report
    "cannot evaluate: no replay artifact" and pass ONLY because the step is warn-only.
  - A high-severity safety escape or an unevaluable row is fatal regardless of ``--strict``.

``--strict`` is warn-only-compatible by design while the corpus is off main; flipping the
CI step to ``--strict`` is a follow-up once #37 lands (recorded as TD-1).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_runner
from pr_files import changed_files, event_payload, pull_request

EVAL_SET = eval_runner.DEFAULT_CORPUS
POLICY = eval_runner.DEFAULT_POLICY
EVAL_REPLAY: Path | None = None
PROMPT_PREFIX = "prompts/"

# The fixed evaluation baseline. A prompt/model change may NOT edit these in the same PR,
# or a PR could weaken the ground truth it is being scored against (REQ-INV-005, TD-1).
GROUND_TRUTH_FILES = (
    "test/eval/expectation_policy.yaml",
    "test/eval/moderation_eval.jsonl",
)


class ReplayUsageError(Exception):
    """A malformed --replay flag; must fail rather than fall back to env/None."""


def prompt_or_model_files(files: list[str]) -> list[str]:
    """PR paths that constitute a prompt or model configuration change."""
    hits = [f for f in files if f.startswith(PROMPT_PREFIX)]
    hits += [f for f in files if f.startswith("src/") and "model" in Path(f).name.lower()]
    return hits


def ground_truth_files_changed(files: list[str]) -> list[str]:
    """Changed files that are part of the fixed evaluation baseline."""
    return [f for f in files if f in GROUND_TRUTH_FILES]


def resolve_replay(argv: list[str]) -> Path | None:
    """Resolve the replay artifact explicitly: ``--replay PATH`` / ``--replay=PATH``,
    then the ``EVAL_REPLAY`` env var, else ``EVAL_REPLAY`` module default (None).

    A bare ``--replay`` (no value) or ``--replay=`` (empty value) is a usage error: a
    configured-but-broken flag must not silently fall through to env/None and report
    "cannot evaluate" as if nothing were configured.
    """
    for index, arg in enumerate(argv):
        if arg == "--replay":
            if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
                raise ReplayUsageError("--replay requires a path value")
            return Path(argv[index + 1])
        if arg.startswith("--replay="):
            value = arg.split("=", 1)[1]
            if not value:
                raise ReplayUsageError("--replay= requires a non-empty path value")
            return Path(value)
    env = os.environ.get("EVAL_REPLAY")
    if env:
        return Path(env)
    return EVAL_REPLAY


def main() -> int:
    argv = sys.argv[1:]
    strict = "--strict" in argv
    # A malformed --replay is a usage error regardless of PR context: a broken flag must
    # not be masked by "no event context" or by silently falling back to env/None.
    try:
        replay = resolve_replay(argv)
    except ReplayUsageError as exc:
        print(f"GATE 4 FAIL: usage error — {exc}")
        return 2
    event = event_payload()
    if event is None:
        print("GATE 4 SKIP: no event context (local run)")
        return 0
    pr = pull_request(event)
    if pr is None:
        print("GATE 4 PASS: push event — gate applies to pull requests")
        return 0

    repo = str(pr["base"]["repo"]["full_name"])
    number = int(pr["number"])
    try:
        files = changed_files(repo, number, os.environ.get("GITHUB_TOKEN", ""))
    except RuntimeError as exc:
        print(f"GATE 4 FAIL: could not list PR files — {exc}")
        return 1
    hits = prompt_or_model_files(files)
    if not hits:
        print("GATE 4 PASS: no prompt/model change in this PR")
        return 0

    gt_hits = ground_truth_files_changed(files)
    if gt_hits:
        for gt_file in gt_hits:
            print(
                f"GATE 4 FAIL: ground truth changed in a prompt PR - {gt_file} is part of the "
                "fixed evaluation baseline; a prompt/model change may not also edit the labelled "
                "data or the expectation policy. Split the change and get separate approval."
            )
        return 1  # fails even without --strict: the scoring baseline must not move with the PR.

    if not EVAL_SET.exists():
        print(
            "GATE 4 WARNING: prompt/model change detected "
            f"({', '.join(hits)}) but the fixed evaluation set is not yet on main "
            f"({EVAL_SET}). Recorded as evaluation debt TD-1; the replay harness exists "
            "but has no corpus to replay."
        )
        if strict:
            print("GATE 4 FAIL (--strict): evaluation replay missing")
            return 1
        return 0

    if replay is None:
        # Honest reporting: do NOT default to a fixture and print PASS.
        print(
            "GATE 4 CANNOT EVALUATE: no replay artifact for this prompt version (TD-1). "
            "Configure one explicitly via --replay <path> or EVAL_REPLAY=<path>; "
            "the gate never defaults to a shipped fixture."
        )
        if strict:
            print("GATE 4 FAIL (--strict): no replay artifact for this prompt version")
            return 1
        print("GATE 4 WARNING: passing only because this step is warn-only (TD-1).")
        return 0

    try:
        rows = eval_runner.load_corpus(EVAL_SET)
        policy = eval_runner.load_policy(POLICY)
        dispositions = eval_runner.load_replay(replay)
        report = eval_runner.score(rows, policy, dispositions)
    except eval_runner.EvalError as exc:
        print(f"GATE 4 FAIL: {exc}")
        return 1

    print("GATE 4: recorded replay (no provider secret used).")
    print(eval_runner.format_table(report))
    fails = eval_runner.check_thresholds(report)
    if fails:
        for fail in fails:
            print(fail)
        hard = bool(report.safety_escapes) or bool(report.uncovered)
        if strict or hard:
            print("GATE 4 FAIL: replay does not meet the approved thresholds")
            return 1
        print("GATE 4 WARNING: quality thresholds not met (warn-only; --strict to block)")
        return 0
    print("GATE 4 PASS: recorded replay meets the approved thresholds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
