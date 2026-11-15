"""CI gate 1: no code change merges unless its tests were approved before implementation.

Current enforcement (basic; tightening tracked as TD-2 in docs/debt-register.md):
the PR description must cite the pre-approved test plan with the marker

    Test-Plan-Approved: #<issue-number>

The referenced issue records the approved test plan (strategy + test list) from
BEFORE implementation began (Prompt.md stage 1/2). W12 tightening: verify the issue
exists and was approved earlier than the first implementation commit.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pr_files import changed_code_files, changed_files, event_payload, pull_request

MARKER = re.compile(r"Test-Plan-Approved:\s*#(\d+)")


def main() -> int:
    event = event_payload()
    if event is None:
        print("GATE 1 SKIP: no event context (local run)")
        return 0
    pr = pull_request(event)
    if pr is None:
        print("GATE 1 PASS: push event — gate applies to pull requests")
        return 0

    repo = str(pr["base"]["repo"]["full_name"])
    number = int(pr["number"])
    token = os.environ.get("GITHUB_TOKEN", "")
    files = changed_files(repo, number, token)
    if not changed_code_files(files):
        print("GATE 1 PASS: no code/prompt changes in this PR (docs-only)")
        return 0

    body = pr.get("body") or ""
    match = MARKER.search(body)
    if match is None:
        print(
            "GATE 1 FAIL: PR changes code but the description has no "
            "'Test-Plan-Approved: #<issue>' marker citing the pre-approved test plan."
        )
        return 1
    print(f"GATE 1 PASS: test plan approved in issue #{match.group(1)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
