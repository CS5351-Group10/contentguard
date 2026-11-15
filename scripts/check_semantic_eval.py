"""CI gate 4: semantic evaluation for prompt/model changes (INV-5 / REQ-INV-005).

Behavior:
  - No PR context (local run / push): pass.
  - PR touches no prompt/model path: pass (not applicable).
  - PR touches prompt/model paths: replay the fixed evaluation set
    (test/eval/moderation_eval.jsonl) against quality thresholds.
    Until the harness lands (evaluation debt TD-1 in docs/debt-register.md),
    this warns and passes by default; `--strict` (used once the harness is
    implemented in W12) turns the missing/failed replay into a blocking failure.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pr_files import changed_files, event_payload, pull_request

EVAL_SET = Path(__file__).resolve().parent.parent / "test" / "eval" / "moderation_eval.jsonl"
PROMPT_PREFIX = "prompts/"


def prompt_or_model_files(files: list[str]) -> list[str]:
    """PR paths that constitute a prompt or model configuration change."""
    hits = [f for f in files if f.startswith(PROMPT_PREFIX)]
    hits += [f for f in files if f.startswith("src/") and "model" in Path(f).name.lower()]
    return hits


def main() -> int:
    strict = "--strict" in sys.argv
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
    files = changed_files(repo, number, os.environ.get("GITHUB_TOKEN", ""))
    hits = prompt_or_model_files(files)
    if not hits:
        print("GATE 4 PASS: no prompt/model change in this PR")
        return 0

    if not EVAL_SET.exists():
        print(
            "GATE 4 WARNING: prompt/model change detected "
            f"({', '.join(hits)}) but the fixed evaluation set is not yet "
            f"implemented ({EVAL_SET}). Recorded as evaluation debt TD-1; "
            "the replay harness is built in W12."
        )
        if strict:
            print("GATE 4 FAIL (--strict): evaluation replay missing")
            return 1
        return 0

    # TODO(W12): replay the evaluation set here and compare against thresholds;
    # any metric below threshold must fail the gate (REQ-INV-005 fit criterion).
    print("GATE 4 WARNING: evaluation harness not wired yet (TD-1)")
    if strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
