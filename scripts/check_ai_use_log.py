"""CI gate 6: a PR that changes code or prompts without updating the AI-use log is blocked.

Code/prompt paths: src/, test/, prompts/, scripts/ (see pr_files.CODE_PREFIXES).
The log file: docs/ai-use-log.yaml (D1).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pr_files import changed_code_files, changed_files, event_payload, pull_request

LOG_PATH = "docs/ai-use-log.yaml"


def main() -> int:
    event = event_payload()
    if event is None:
        print("GATE 6 SKIP: no event context (local run)")
        return 0
    pr = pull_request(event)
    if pr is None:
        print("GATE 6 PASS: push event — gate applies to pull requests")
        return 0

    repo = str(pr["base"]["repo"]["full_name"])
    number = int(pr["number"])
    try:
        files = changed_files(repo, number, os.environ.get("GITHUB_TOKEN", ""))
    except RuntimeError as exc:
        print(f"GATE 6 FAIL: could not list PR files — {exc}")
        return 1
    code_changed = changed_code_files(files)
    log_updated = LOG_PATH in files

    if code_changed and not log_updated:
        print(
            f"GATE 6 FAIL: PR #{number} changes {len(code_changed)} code/prompt file(s) "
            f"but does not update {LOG_PATH}. Record the agent session in the log "
            "(same PR) before merging."
        )
        return 1
    print(
        f"GATE 6 PASS: {len(code_changed)} code/prompt file(s); "
        f"ai-use log {'updated' if log_updated else 'not required (no code/prompt changes)'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
