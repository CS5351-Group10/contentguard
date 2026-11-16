"""CI gate 7: no PR merges without a review memo posted by a non-author reviewer.

Per docs/review-memo.md (rule 1) every PR needs its RM memo before merge, but no
gate enforced it (2026-11-15 PR #2 review incident; issue #4). This closes the gap:
a memo is a review body or issue comment whose author is NOT the PR author and whose
body carries both an ``RM-\\d{3}`` number and a ``Verdict: APPROVE|CHANGES REQUIRED|
REJECT`` line (both case-insensitive). The PR body is excluded (author-owned).

Behavior (mirrors gates 1/4/6):
  - No event context (local run): skip.
  - Push event: pass (gate applies to pull requests).
  - PR event: pass if >=1 valid non-author memo exists, else fail with an actionable
    message. Any API failure fails closed with an actionable diagnosis.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pr_files import event_payload, issue_comments, pull_request, pull_reviews

MEMO_RM = re.compile(r"RM-\d{3}", re.IGNORECASE)
MEMO_VERDICT = re.compile(
    r"Verdict\s*:\s*(APPROVE|CHANGES REQUIRED|REJECT)", re.IGNORECASE
)


def find_memo(entries: list[tuple[str, str]], author_login: str) -> str | None:
    """Return the body of the first valid non-author review memo, or None.

    ``entries`` is a list of ``(author_login, body)`` candidates (review bodies then
    issue comments). Pure: no network, so the offline tests need no API access.
    A candidate counts when its author is not the PR author AND its body carries
    both an RM number and a Verdict line (docs/review-memo.md; issue #4).
    """
    for author, body in entries:
        if author == author_login:
            continue
        if MEMO_RM.search(body) and MEMO_VERDICT.search(body):
            return body
    return None


def collect_entries(reviews: list[dict], comments: list[dict]) -> list[tuple[str, str]]:
    """Map review + comment objects to ``(user.login, body)`` memo candidates."""
    entries: list[tuple[str, str]] = []
    for item in [*reviews, *comments]:
        user = item.get("user") or {}
        entries.append((str(user.get("login", "")), str(item.get("body") or "")))
    return entries


def main() -> int:
    event = event_payload()
    if event is None:
        print("GATE 7 SKIP: no event context (local run)")
        return 0
    pr = pull_request(event)
    if pr is None:
        print("GATE 7 PASS: push event — gate applies to pull requests")
        return 0

    repo = str(pr["base"]["repo"]["full_name"])
    number = int(pr["number"])
    author_login = str(pr["user"]["login"])
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        reviews = pull_reviews(repo, number, token)
        comments = issue_comments(repo, number, token)
    except RuntimeError as exc:
        print(f"GATE 7 FAIL: could not fetch reviews/comments — {exc}")
        return 1

    memo = find_memo(collect_entries(reviews, comments), author_login)
    if memo is None:
        print(
            f"GATE 7 FAIL: PR #{number} has no review memo posted by a non-author "
            "reviewer. Post the next RM-<next> memo (per docs/review-memo.md) as a "
            "review body or a comment — a non-author reviewer, with an RM number and "
            "a 'Verdict: APPROVE|CHANGES REQUIRED|REJECT' line — then re-run this job."
        )
        return 1
    print(f"GATE 7 PASS: non-author review memo found on PR #{number}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
